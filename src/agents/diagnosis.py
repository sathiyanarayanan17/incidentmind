"""Diagnosis Agent — Searches past incidents for similar issues.

The Diagnosis Agent:
1. Takes a triaged incident
2. Performs semantic search over past incidents via vector embeddings
3. Analyzes similar incidents for root cause patterns
4. Proposes a diagnosis with supporting evidence
"""

import json
import structlog

from src.agents.base import BaseAgent

logger = structlog.get_logger(__name__)


class DiagnosisAgent(BaseAgent):
    """Diagnoses incidents using semantic search over past incident memory."""

    agent_type = "diagnosis"

    SYSTEM_PROMPT = """You are an expert DevOps diagnosis agent. Your job is to:
1. Analyze current incident symptoms
2. Compare with similar past incidents
3. Identify the most likely root cause
4. Provide confidence in your diagnosis

Use evidence from past incidents to support your analysis.
Be specific about what's likely failing and why."""

    def process(self, incident_id: str) -> dict:
        """Diagnose an incident using RAG over past incidents."""
        self.state_manager.set_working({"incident_id": incident_id, "step": "diagnosis"})

        incident = self.memory.get_incident(incident_id)
        if not incident:
            return {"error": "Incident not found"}

        self.state_manager.store_reasoning(
            incident_id, "observation", {"action": "started_diagnosis", "incident": incident["title"]}
        )

        # Step 1: Search for similar past incidents using vector similarity
        similar_incidents = self._search_similar_incidents(incident)

        self.state_manager.store_reasoning(
            incident_id,
            "observation",
            {"action": "similarity_search", "results_found": len(similar_incidents)},
        )

        # Step 2: Analyze with LLM using similar incidents as context
        diagnosis = self._diagnose_with_context(incident, similar_incidents)

        self.state_manager.store_reasoning(
            incident_id, "hypothesis", {"diagnosis": diagnosis}
        )

        # Step 3: Store diagnosis embedding for future reference
        if diagnosis.get("root_cause"):
            self.embeddings.store_incident_embedding(
                incident_id, "root_cause", diagnosis["root_cause"]
            )

        # Step 4: Update incident with diagnosis
        if diagnosis.get("root_cause"):
            self.memory.update_incident(
                incident_id, root_cause=diagnosis["root_cause"]
            )

        self.state_manager.set_idle()
        logger.info("diagnosis_completed", incident_id=incident_id, confidence=diagnosis.get("confidence"))
        return {
            "status": "diagnosed",
            "diagnosis": diagnosis,
            "similar_incidents": [
                {"title": s["incident_title"], "similarity": s["similarity"]}
                for s in similar_incidents[:3]
            ],
        }

    def _search_similar_incidents(self, incident: dict) -> list:
        """Search for similar past incidents using vector similarity."""
        # Build search query from incident details
        search_text = f"{incident['title']}"
        symptoms = incident.get("symptoms", {})
        if symptoms:
            search_text += f" {json.dumps(symptoms)}"

        # Search CockroachDB vector index
        results = self.embeddings.search_similar(
            query_text=search_text,
            content_type="symptom",
            limit=5,
            min_similarity=0.6,
        )

        # Filter out the current incident
        results = [r for r in results if str(r["incident_id"]) != str(incident["incident_id"])]
        return results

    def _diagnose_with_context(self, incident: dict, similar_incidents: list) -> dict:
        """Use LLM to diagnose based on current incident + similar past incidents."""
        # Build context from similar incidents
        context_parts = []
        for i, sim in enumerate(similar_incidents[:3], 1):
            context_parts.append(
                f"Similar Incident #{i} (similarity: {sim['similarity']:.2f}):\n"
                f"  Title: {sim.get('incident_title', 'N/A')}\n"
                f"  Root Cause: {sim.get('root_cause', 'Unknown')}\n"
                f"  Resolution: {sim.get('resolution', 'Unknown')}\n"
                f"  Symptoms: {sim.get('content_text', 'N/A')}"
            )

        context = "\n\n".join(context_parts) if context_parts else "No similar past incidents found."

        prompt = f"""Diagnose this incident based on its symptoms and similar past incidents.

CURRENT INCIDENT:
Title: {incident['title']}
Severity: {incident['severity']}
Symptoms: {json.dumps(incident.get('symptoms', {}), indent=2)}

SIMILAR PAST INCIDENTS:
{context}

Provide your diagnosis as JSON with:
- root_cause: your best assessment of the root cause
- confidence: 0.0-1.0 how confident you are
- evidence: list of supporting evidence from past incidents
- recommended_action: what should be done to resolve this
- category: infrastructure|application|network|database|security
"""
        return self.invoke_llm_json(prompt, self.SYSTEM_PROMPT)
