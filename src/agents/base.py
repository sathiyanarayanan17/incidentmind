"""Base agent class for IncidentMind.

All agents inherit from this base class which provides:
- State management with crash recovery
- LLM access via Amazon Bedrock
- Memory read/write operations
- Structured logging
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Optional

import boto3
from dotenv import load_dotenv
import structlog

from src.memory.cockroach import CockroachMemory
from src.memory.embeddings import EmbeddingManager
from src.memory.state import AgentStateManager

load_dotenv()

logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    """Base class for all IncidentMind agents."""

    agent_type: str = "base"

    def __init__(self):
        self.memory = CockroachMemory()
        self.embeddings = EmbeddingManager()
        self.state_manager = AgentStateManager(self.agent_type, self.memory)
        self.bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )
        self.model_id = os.getenv(
            "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )

    def start(self) -> str:
        """Start the agent with crash recovery."""
        agent_id = self.state_manager.recover_or_register()
        logger.info("agent_started", agent_type=self.agent_type, agent_id=agent_id)

        # Check if we're recovering a previous task
        current_task = self.state_manager.get_current_task()
        if current_task:
            logger.info("resuming_task", task=current_task)
            self.resume(current_task)

        return agent_id

    def shutdown(self):
        """Gracefully shutdown the agent."""
        self.state_manager.shutdown()
        self.embeddings.close()
        logger.info("agent_stopped", agent_type=self.agent_type)

    def invoke_llm(self, prompt: str, system: str = "", max_tokens: int = 2048) -> str:
        """Invoke Amazon Bedrock Claude for reasoning."""
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            body["system"] = system

        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        output_text = response_body["content"][0]["text"]
        logger.debug("llm_invoked", prompt_length=len(prompt), response_length=len(output_text))
        return output_text

    def invoke_llm_json(self, prompt: str, system: str = "") -> dict:
        """Invoke LLM and parse JSON response."""
        full_prompt = f"{prompt}\n\nRespond ONLY with valid JSON, no other text."
        response = self.invoke_llm(full_prompt, system)

        # Try to extract JSON from response
        try:
            # Handle case where LLM wraps in markdown code block
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.warning("json_parse_failed", error=str(e), response=response[:200])
            return {"error": "Failed to parse LLM response", "raw": response}

    @abstractmethod
    def process(self, incident_id: str) -> dict:
        """Process an incident. Must be implemented by subclasses."""
        pass

    def resume(self, task: dict):
        """Resume a previously interrupted task. Override for custom recovery."""
        incident_id = task.get("incident_id")
        if incident_id:
            logger.info("resuming_incident_processing", incident_id=incident_id)
            self.process(incident_id)
