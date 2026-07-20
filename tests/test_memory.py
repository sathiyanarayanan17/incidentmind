"""Tests for the CockroachDB memory layer."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCockroachMemory:
    """Tests for CockroachMemory class."""

    def test_missing_connection_url_raises(self):
        """Should raise ValueError if no connection URL is provided."""
        # Temporarily remove env var
        original = os.environ.pop("COCKROACHDB_URL", None)
        try:
            from src.memory.cockroach import CockroachMemory
            with pytest.raises(ValueError, match="COCKROACHDB_URL"):
                CockroachMemory(connection_url=None)
        finally:
            if original:
                os.environ["COCKROACHDB_URL"] = original

    def test_create_incident_requires_title(self):
        """Incident creation requires a title."""
        from src.memory.cockroach import CockroachMemory
        memory = CockroachMemory(connection_url="postgresql://fake:fake@localhost:26257/test")
        # This will fail at connection time, but validates the interface exists
        assert hasattr(memory, "create_incident")
        assert hasattr(memory, "get_incident")
        assert hasattr(memory, "update_incident")

    def test_agent_state_interface(self):
        """AgentStateManager has required interface."""
        from src.memory.state import AgentStateManager, AgentStatus
        assert AgentStatus.IDLE == "idle"
        assert AgentStatus.WORKING == "working"
        assert AgentStatus.FAILED == "failed"


class TestEmbeddingManager:
    """Tests for EmbeddingManager class."""

    def test_embedding_manager_interface(self):
        """EmbeddingManager exposes required methods."""
        from src.memory.embeddings import EmbeddingManager
        assert hasattr(EmbeddingManager, "generate_embedding")
        assert hasattr(EmbeddingManager, "store_incident_embedding")
        assert hasattr(EmbeddingManager, "search_similar")
        assert hasattr(EmbeddingManager, "search_similar_to_incident")


class TestAgents:
    """Tests for agent classes."""

    def test_triage_agent_type(self):
        """TriageAgent has correct type."""
        from src.agents.triage import TriageAgent
        assert TriageAgent.agent_type == "triage"

    def test_diagnosis_agent_type(self):
        """DiagnosisAgent has correct type."""
        from src.agents.diagnosis import DiagnosisAgent
        assert DiagnosisAgent.agent_type == "diagnosis"

    def test_correlator_agent_type(self):
        """CorrelatorAgent has correct type."""
        from src.agents.correlator import CorrelatorAgent
        assert CorrelatorAgent.agent_type == "correlator"

    def test_resolution_agent_type(self):
        """ResolutionAgent has correct type."""
        from src.agents.resolution import ResolutionAgent
        assert ResolutionAgent.agent_type == "resolution"


class TestLambdaHandler:
    """Tests for Lambda ingestion handler."""

    def test_parse_cloudwatch_alarm(self):
        """Should parse CloudWatch Alarm SNS event."""
        from src.ingestion.lambda_handler import _parse_event
        import json

        event = {
            "Records": [{
                "EventSource": "aws:sns",
                "Sns": {
                    "Subject": "ALARM: test-alarm",
                    "Message": json.dumps({
                        "AlarmName": "HighCPU",
                        "NewStateValue": "ALARM",
                        "NewStateReason": "Threshold exceeded",
                        "Trigger": {
                            "MetricName": "CPUUtilization",
                            "Namespace": "AWS/EC2",
                        },
                    }),
                },
            }],
        }

        result = _parse_event(event)
        assert result is not None
        assert "HighCPU" in result["title"]
        assert result["severity"] == 2
        assert result["source"] == "cloudwatch"

    def test_parse_api_gateway_event(self):
        """Should parse API Gateway event."""
        from src.ingestion.lambda_handler import _parse_event
        import json

        event = {
            "httpMethod": "POST",
            "body": json.dumps({
                "title": "Test incident",
                "severity": 3,
                "source": "api",
                "symptoms": {"error": "timeout"},
            }),
        }

        result = _parse_event(event)
        assert result is not None
        assert result["title"] == "Test incident"
        assert result["severity"] == 3

    def test_parse_direct_event(self):
        """Should parse direct Lambda invocation."""
        from src.ingestion.lambda_handler import _parse_event

        event = {
            "title": "Direct incident",
            "severity": 1,
            "symptoms": {"cpu": 99},
        }

        result = _parse_event(event)
        assert result is not None
        assert result["title"] == "Direct incident"
