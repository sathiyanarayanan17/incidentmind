"""Triage Agent — Classifies incidents and matches known patterns.

The Triage Agent is the first responder:
1. Receives a new incident alert
2. Classifies severity based on symptoms
3. Checks correlation patterns for known issues
4. Routes to Diagnosis Agent if unknown
"""

import json
import structlog

from src.agents.base import BaseAgent

logger = structlog.get_logger(__name__)


class TriageAgent(BaseAgent):
    """Classifies incoming incidents and matches known patterns."""

    agent_type = "triage"

    SYSTEM_PROMPT = """You are an expert DevOps incident triage agent. Your job is to:
1. Analyze incoming incident symptoms
2. Classify severity (1=critical, 2=high, 3=medium, 4=low, 5=info)
3. Identify the likely category (infrastructure, application, network, database, security)
4. Determine if this matches any known patterns

Be concise and precise. Base your analysis on the symptoms provided."""

    def process(self, incident_id: str) -> dict:
        """Triage an incident: classify and check patterns."""
        # Persist task state for crash recovery
        self.state_manager.set_working({"incident_id": incident_id, "step": "triage"})

        # Get incident details
        incident = self.memory.get_incident(incident_id)
        if not incident:
            logger.error("incident_not_found", incident_id=incident_id)
            return {"error": "Incident not found"}

        # Store observation
        self.state_manager.store_reasoning(
            incident_id, "observation", {"action": "started_triage", "incident": incident["title"]}
        )

        # Check known patterns first
        patterns = self.memory.get_patterns(min_confidence=0.6)
        pattern_match = self._match_patterns(incident, patterns)

        if pattern_match:
            # Known issue — fast path
            self.state_manager.store_reasoning(
                incident_id,
                "action",
                {"action": "pattern_matched", "pattern": pattern_match["pattern_name"]},
            )
            self.memory.update_incident(
                incident_id,
                status="investigating",
                root_cause=f"Matched pattern: {pattern_match['pattern_name']}",
            )
            self.memory.increment_pattern(pattern_match["pattern_id"])
            result = {
                "status": "pattern_matched",
                "pattern": pattern_match["pattern_name"],
                "suggested_action": pattern_match["suggested_action"],
                "confidence": pattern_match["confidence"],
            }
        else:
            # Unknown issue — classify with LLM
            classification = self._classify_incident(incident)
            self.state_manager.store_reasoning(
                incident_id, "result", {"action": "classified", "classification": classification}
            )

            # Update incident with classification
            self.memory.update_incident(
                incident_id,
                severity=classification.get("severity", incident["severity"]),
                status="investigating",
            )

            # Store symptom embedding for future similarity search
            symptom_text = self._build_symptom_text(incident, classification)
            self.embeddings.store_incident_embedding(
                incident_id, "symptom", symptom_text
            )

            result = {
                "status": "classified",
                "classification": classification,
                "needs_diagnosis": True,
            }

        self.state_manager.set_idle()
        logger.info("triage_completed", incident_id=incident_id, result_status=result["status"])
        return result

    def _classify_incident(self, incident: dict) -> dict:
        """Use LLM to classify the incident."""
        prompt = f"""Analyze this incident and classify it:

Title: {incident['title']}
Current Severity: {incident['severity']}
Symptoms: {json.dumps(incident.get('symptoms', {}), indent=2)}
Source: {incident.get('source', 'unknown')}

Classify with:
- severity: 1-5 (1=critical, 5=info)
- category: infrastructure|application|network|database|security
- summary: one-line description of the likely issue
- urgency: immediate|soon|can_wait
"""
        return self.invoke_llm_json(prompt, self.SYSTEM_PROMPT)

    def _match_patterns(self, incident: dict, patterns: list) -> dict | None:
        """Check if incident matches any known correlation pattern."""
        if not patterns:
            return None

        symptoms = incident.get("symptoms", {})
        title_lower = incident.get("title", "").lower()

        for pattern in patterns:
            conditions = pattern.get("conditions", {})
            keywords = conditions.get("keywords", [])
            # Simple keyword matching — could be enhanced with LLM
            if any(kw.lower() in title_lower for kw in keywords):
                return pattern
            if any(kw.lower() in json.dumps(symptoms).lower() for kw in keywords):
                return pattern

        return None

    def _build_symptom_text(self, incident: dict, classification: dict) -> str:
        """Build a rich text representation for embedding."""
        parts = [
            f"Incident: {incident['title']}",
            f"Severity: {classification.get('severity', incident['severity'])}",
            f"Category: {classification.get('category', 'unknown')}",
            f"Summary: {classification.get('summary', '')}",
        ]
        symptoms = incident.get("symptoms", {})
        if symptoms:
            parts.append(f"Symptoms: {json.dumps(symptoms)}")
        return "\n".join(parts)
