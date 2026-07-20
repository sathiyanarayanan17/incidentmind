"""Resolution Agent — Suggests fixes based on past successful resolutions.

The Resolution Agent:
1. Takes a diagnosed incident
2. Searches for past resolutions of similar issues
3. Ranks resolution strategies by relevance and success rate
4. Proposes a resolution plan
"""

import json
import structlog

from src.agents.base import BaseAgent

logger = structlog.get_logger(__name__)


class ResolutionAgent(BaseAgent):
    """Suggests resolutions based on past successful fixes."""

    agent_type = "resolution"

    SYSTEM_PROMPT = """You are an expert DevOps resolution agent. Your job is to:
1. Review the diagnosis of the current incident
2. Analyze past resolutions for similar issues
3. Propose a concrete resolution plan
4. Prioritize safe, reversible actions

Always prefer well-tested solutions over novel approaches.
Be specific about commands, configurations, or code changes needed."""

    def process(self, incident_id: str) -> dict:
        """Propose a resolution for a diagnosed incident."""
        self.state_manager.set_working({"incident_id": incident_id, "step": "resolution"})

        incident = self.memory.get_incident(incident_id)
        if not incident:
            return {"error": "Incident not found"}

        self.state_manager.store_reasoning(
            incident_id, "observation", {"action": "started_resolution", "root_cause": incident.get("root_cause")}
        )

        # Search for similar past resolutions
        similar_resolutions = self._find_similar_resolutions(incident)

        # Generate resolution plan
        resolution = self._generate_resolution(incident, similar_resolutions)

        self.state_manager.store_reasoning(
            incident_id, "action", {"proposed_resolution": resolution}
        )

        # Store resolution embedding for future reference
        if resolution.get("resolution_summary"):
            self.embeddings.store_incident_embedding(
                incident_id, "resolution", resolution["resolution_summary"]
            )

        # Update incident
        if resolution.get("resolution_summary"):
            self.memory.update_incident(
                incident_id, resolution=resolution["resolution_summary"]
            )

        self.state_manager.set_idle()
        logger.info("resolution_proposed", incident_id=incident_id)
        return {
            "status": "resolution_proposed",
            "resolution": resolution,
            "based_on_past_incidents": len(similar_resolutions),
        }

    def resolve_incident(self, incident_id: str, resolution_text: str):
        """Mark an incident as resolved (called after human approval)."""
        from datetime import datetime, timezone

        self.memory.update_incident(
            incident_id,
            status="resolved",
            resolution=resolution_text,
            resolved_by=self.state_manager.agent_id,
            resolved_at=datetime.now(timezone.utc),
        )

        # Store resolution embedding for future learning
        self.embeddings.store_incident_embedding(
            incident_id, "resolution", resolution_text
        )

        logger.info("incident_resolved", incident_id=incident_id)

    def _find_similar_resolutions(self, incident: dict) -> list:
        """Search for past resolutions using the root cause as query."""
        search_text = incident.get("root_cause", incident["title"])
        results = self.embeddings.search_similar(
            query_text=search_text,
            content_type="resolution",
            limit=5,
            min_similarity=0.6,
        )
        return results

    def _generate_resolution(self, incident: dict, similar_resolutions: list) -> dict:
        """Use LLM to generate a resolution plan."""
        # Build context from past resolutions
        context_parts = []
        for i, res in enumerate(similar_resolutions[:3], 1):
            context_parts.append(
                f"Past Resolution #{i} (similarity: {res['similarity']:.2f}):\n"
                f"  Incident: {res.get('incident_title', 'N/A')}\n"
                f"  Resolution: {res.get('content_text', 'N/A')}"
            )

        context = "\n\n".join(context_parts) if context_parts else "No similar past resolutions found."

        prompt = f"""Propose a resolution for this incident.

CURRENT INCIDENT:
Title: {incident['title']}
Severity: {incident['severity']}
Root Cause: {incident.get('root_cause', 'Not yet determined')}
Symptoms: {json.dumps(incident.get('symptoms', {}), indent=2)}

SIMILAR PAST RESOLUTIONS:
{context}

Provide a resolution plan as JSON with:
- resolution_summary: one-line description of the fix
- steps: array of concrete steps to resolve
- rollback_plan: how to undo if the fix causes problems
- estimated_time: estimated time to resolve (e.g., "15 minutes")
- risk_level: low|medium|high
- requires_approval: true/false (true for high-risk changes)
"""
        return self.invoke_llm_json(prompt, self.SYSTEM_PROMPT)
