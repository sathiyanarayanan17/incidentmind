"""Embedding operations using CockroachDB Distributed Vector Indexing.

This module handles:
- Generating embeddings via Amazon Bedrock Titan Embeddings v2
- Storing embeddings in CockroachDB alongside incident data
- Semantic similarity search over past incidents
"""

import os
import json
from typing import Optional

import boto3
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
import structlog

load_dotenv()

logger = structlog.get_logger(__name__)


class EmbeddingManager:
    """Manages vector embeddings in CockroachDB with Bedrock Titan."""

    def __init__(self, connection_url: Optional[str] = None):
        self.connection_url = connection_url or os.getenv("COCKROACHDB_URL")
        self.bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )
        self.embedding_model_id = os.getenv(
            "BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"
        )
        self._conn = None

    @property
    def conn(self):
        """Lazy connection with auto-reconnect."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self.connection_url, autocommit=False)
        return self._conn

    def close(self):
        """Close the database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector using Amazon Bedrock Titan Embeddings v2.
        
        Returns a 1536-dimensional vector.
        """
        body = json.dumps({
            "inputText": text,
            "dimensions": 1536,
            "normalize": True,
        })

        response = self.bedrock_client.invoke_model(
            modelId=self.embedding_model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        embedding = response_body["embedding"]
        logger.debug("embedding_generated", text_length=len(text), dimensions=len(embedding))
        return embedding

    def store_incident_embedding(
        self,
        incident_id: str,
        content_type: str,
        content_text: str,
        embedding: Optional[list[float]] = None,
    ) -> str:
        """Store an embedding for incident content.
        
        Args:
            incident_id: UUID of the incident
            content_type: Type of content ('symptom', 'root_cause', 'resolution', 'log_snippet')
            content_text: The text that was embedded
            embedding: Pre-computed embedding vector (if None, will generate)
            
        Returns:
            UUID of the stored embedding
        """
        if embedding is None:
            embedding = self.generate_embedding(content_text)

        embedding_str = f"[{','.join(str(x) for x in embedding)}]"

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO incident_embeddings (incident_id, content_type, content_text, embedding)
                VALUES (%s, %s, %s, %s::vector)
                RETURNING id
                """,
                (incident_id, content_type, content_text, embedding_str),
            )
            result = cur.fetchone()
        self.conn.commit()
        logger.info(
            "embedding_stored",
            incident_id=incident_id,
            content_type=content_type,
        )
        return str(result[0])

    def search_similar(
        self,
        query_text: str,
        content_type: Optional[str] = None,
        limit: int = 5,
        min_similarity: float = 0.7,
    ) -> list[dict]:
        """Search for similar incidents using cosine similarity.
        
        This is the core RAG retrieval function. It:
        1. Generates an embedding for the query text
        2. Searches CockroachDB's vector index for similar past incidents
        3. Returns ranked results with similarity scores
        
        Args:
            query_text: The text to search for (e.g., error message, symptom description)
            content_type: Filter by content type (optional)
            limit: Maximum results to return
            min_similarity: Minimum cosine similarity threshold
            
        Returns:
            List of matching records with similarity scores
        """
        query_embedding = self.generate_embedding(query_text)
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

        # CockroachDB vector cosine distance: 1 - cosine_similarity
        # So we filter where distance < (1 - min_similarity)
        max_distance = 1.0 - min_similarity

        if content_type:
            query = """
                SELECT
                    ie.id,
                    ie.incident_id,
                    ie.content_type,
                    ie.content_text,
                    ie.created_at,
                    i.title AS incident_title,
                    i.severity,
                    i.status AS incident_status,
                    i.root_cause,
                    i.resolution,
                    (ie.embedding <=> %s::vector) AS distance
                FROM incident_embeddings ie
                JOIN incidents i ON i.incident_id = ie.incident_id
                WHERE ie.content_type = %s
                    AND (ie.embedding <=> %s::vector) < %s
                ORDER BY distance ASC
                LIMIT %s
            """
            params = (embedding_str, content_type, embedding_str, max_distance, limit)
        else:
            query = """
                SELECT
                    ie.id,
                    ie.incident_id,
                    ie.content_type,
                    ie.content_text,
                    ie.created_at,
                    i.title AS incident_title,
                    i.severity,
                    i.status AS incident_status,
                    i.root_cause,
                    i.resolution,
                    (ie.embedding <=> %s::vector) AS distance
                FROM incident_embeddings ie
                JOIN incidents i ON i.incident_id = ie.incident_id
                WHERE (ie.embedding <=> %s::vector) < %s
                ORDER BY distance ASC
                LIMIT %s
            """
            params = (embedding_str, embedding_str, max_distance, limit)

        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        results = []
        for row in rows:
            record = dict(row)
            record["similarity"] = 1.0 - float(record.pop("distance"))
            results.append(record)

        logger.info(
            "similarity_search_completed",
            query_length=len(query_text),
            results_found=len(results),
        )
        return results

    def search_similar_to_incident(
        self,
        incident_id: str,
        limit: int = 5,
    ) -> list[dict]:
        """Find incidents similar to a given incident.
        
        Looks up the incident's symptom embeddings and searches for
        similar past incidents (excluding itself).
        """
        # Get the incident's symptom embeddings
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT content_text FROM incident_embeddings
                WHERE incident_id = %s AND content_type = 'symptom'
                LIMIT 1
                """,
                (incident_id,),
            )
            row = cur.fetchone()

        if not row:
            return []

        # Search for similar, excluding this incident
        results = self.search_similar(row["content_text"], limit=limit + 1)
        return [r for r in results if str(r["incident_id"]) != incident_id][:limit]
