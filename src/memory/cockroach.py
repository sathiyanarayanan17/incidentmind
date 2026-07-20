"""CockroachDB connection and query layer for IncidentMind.

This module manages the connection to CockroachDB Cloud and provides
the core CRUD operations for incidents, agent state, and memory.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import structlog

load_dotenv()

logger = structlog.get_logger(__name__)

# Register UUID adapter
psycopg2.extras.register_uuid()


class CockroachMemory:
    """Core CockroachDB memory layer for IncidentMind agents."""

    def __init__(self, connection_url: Optional[str] = None):
        self.connection_url = connection_url or os.getenv("COCKROACHDB_URL")
        if not self.connection_url:
            raise ValueError("COCKROACHDB_URL environment variable is required")
        self._conn = None

    @property
    def conn(self):
        """Lazy connection with auto-reconnect."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.connection_url)
            self._conn.autocommit = False
        return self._conn

    def close(self):
        """Close the database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()

    # ─── Schema Management ────────────────────────────────────────────

    def initialize_schema(self):
        """Create all tables if they don't exist."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS agent_state (
            agent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_type STRING NOT NULL,
            status STRING NOT NULL DEFAULT 'idle',
            current_task JSONB,
            last_heartbeat TIMESTAMPTZ DEFAULT now(),
            created_at TIMESTAMPTZ DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS incidents (
            incident_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title STRING NOT NULL,
            severity INT NOT NULL,
            status STRING NOT NULL DEFAULT 'open',
            source STRING,
            symptoms JSONB,
            root_cause STRING,
            resolution STRING,
            resolved_by UUID,
            created_at TIMESTAMPTZ DEFAULT now(),
            resolved_at TIMESTAMPTZ
        );

        CREATE TABLE IF NOT EXISTS incident_embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            incident_id UUID REFERENCES incidents(incident_id) ON DELETE CASCADE,
            content_type STRING NOT NULL,
            content_text STRING NOT NULL,
            embedding VECTOR(1536),
            created_at TIMESTAMPTZ DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS agent_memory (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id UUID REFERENCES agent_state(agent_id) ON DELETE CASCADE,
            incident_id UUID REFERENCES incidents(incident_id) ON DELETE CASCADE,
            memory_type STRING NOT NULL,
            content JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS correlation_patterns (
            pattern_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pattern_name STRING NOT NULL,
            conditions JSONB NOT NULL,
            suggested_action STRING,
            confidence FLOAT DEFAULT 0.5,
            times_seen INT DEFAULT 1,
            last_seen TIMESTAMPTZ DEFAULT now()
        );
        """
        with self.conn.cursor() as cur:
            cur.execute(schema_sql)
        self.conn.commit()
        logger.info("schema_initialized")

    def create_vector_index(self):
        """Create vector index for similarity search."""
        index_sql = """
        CREATE INDEX IF NOT EXISTS idx_incident_embeddings_vec
            ON incident_embeddings
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """
        with self.conn.cursor() as cur:
            cur.execute(index_sql)
        self.conn.commit()
        logger.info("vector_index_created")

    # ─── Incident Operations ──────────────────────────────────────────

    def create_incident(
        self,
        title: str,
        severity: int,
        source: str = "manual",
        symptoms: Optional[dict] = None,
    ) -> str:
        """Create a new incident and return its ID."""
        incident_id = str(uuid.uuid4())
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO incidents (incident_id, title, severity, status, source, symptoms)
                VALUES (%s, %s, %s, 'open', %s, %s)
                RETURNING incident_id
                """,
                (incident_id, title, severity, source, psycopg2.extras.Json(symptoms or {})),
            )
            result = cur.fetchone()
        self.conn.commit()
        logger.info("incident_created", incident_id=incident_id, title=title, severity=severity)
        return str(result[0])

    def update_incident(self, incident_id: str, **kwargs):
        """Update incident fields."""
        allowed_fields = {"title", "severity", "status", "root_cause", "resolution", "resolved_by", "resolved_at"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return

        set_clause = ", ".join(f"{k} = %s" for k in updates.keys())
        values = list(updates.values())
        values.append(incident_id)

        with self.conn.cursor() as cur:
            cur.execute(
                f"UPDATE incidents SET {set_clause} WHERE incident_id = %s",
                values,
            )
        self.conn.commit()
        logger.info("incident_updated", incident_id=incident_id, fields=list(updates.keys()))

    def get_incident(self, incident_id: str) -> Optional[dict]:
        """Get a single incident by ID."""
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM incidents WHERE incident_id = %s", (incident_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    def get_open_incidents(self) -> list:
        """Get all open incidents."""
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM incidents WHERE status != 'resolved' ORDER BY severity ASC, created_at DESC"
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def get_recent_incidents(self, limit: int = 20) -> list:
        """Get recent incidents."""
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM incidents ORDER BY created_at DESC LIMIT %s", (limit,)
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    # ─── Agent State Operations ───────────────────────────────────────

    def register_agent(self, agent_type: str) -> str:
        """Register a new agent and return its ID."""
        agent_id = str(uuid.uuid4())
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_state (agent_id, agent_type, status)
                VALUES (%s, %s, 'idle')
                RETURNING agent_id
                """,
                (agent_id, agent_type),
            )
            result = cur.fetchone()
        self.conn.commit()
        logger.info("agent_registered", agent_id=agent_id, agent_type=agent_type)
        return str(result[0])

    def update_agent_state(self, agent_id: str, status: str, current_task: Optional[dict] = None):
        """Update agent's state and heartbeat."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE agent_state
                SET status = %s, current_task = %s, last_heartbeat = now()
                WHERE agent_id = %s
                """,
                (status, psycopg2.extras.Json(current_task), agent_id),
            )
        self.conn.commit()

    def get_agent_state(self, agent_id: str) -> Optional[dict]:
        """Get current state of an agent."""
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM agent_state WHERE agent_id = %s", (agent_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    def heartbeat(self, agent_id: str):
        """Update agent heartbeat timestamp."""
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE agent_state SET last_heartbeat = now() WHERE agent_id = %s",
                (agent_id,),
            )
        self.conn.commit()

    # ─── Agent Memory (Reasoning Traces) ─────────────────────────────

    def store_memory(
        self,
        agent_id: str,
        incident_id: str,
        memory_type: str,
        content: dict,
    ) -> str:
        """Store an agent's reasoning trace or observation."""
        memory_id = str(uuid.uuid4())
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_memory (id, agent_id, incident_id, memory_type, content)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (memory_id, agent_id, incident_id, memory_type, psycopg2.extras.Json(content)),
            )
        self.conn.commit()
        return memory_id

    def get_agent_memories(self, agent_id: str, incident_id: Optional[str] = None) -> list:
        """Get reasoning traces for an agent, optionally filtered by incident."""
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if incident_id:
                cur.execute(
                    """
                    SELECT * FROM agent_memory
                    WHERE agent_id = %s AND incident_id = %s
                    ORDER BY created_at ASC
                    """,
                    (agent_id, incident_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM agent_memory WHERE agent_id = %s ORDER BY created_at DESC LIMIT 50",
                    (agent_id,),
                )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    # ─── Correlation Patterns ─────────────────────────────────────────

    def store_pattern(self, pattern_name: str, conditions: dict, suggested_action: str, confidence: float = 0.5):
        """Store a new correlation pattern."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO correlation_patterns (pattern_name, conditions, suggested_action, confidence)
                VALUES (%s, %s, %s, %s)
                """,
                (pattern_name, psycopg2.extras.Json(conditions), suggested_action, confidence),
            )
        self.conn.commit()
        logger.info("pattern_stored", pattern_name=pattern_name, confidence=confidence)

    def get_patterns(self, min_confidence: float = 0.0) -> list:
        """Get correlation patterns above a confidence threshold."""
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM correlation_patterns
                WHERE confidence >= %s
                ORDER BY confidence DESC, times_seen DESC
                """,
                (min_confidence,),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def increment_pattern(self, pattern_id: str):
        """Increment times_seen for a pattern."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE correlation_patterns
                SET times_seen = times_seen + 1, last_seen = now()
                WHERE pattern_id = %s
                """,
                (pattern_id,),
            )
        self.conn.commit()
