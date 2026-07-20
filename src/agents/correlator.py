"""Correlator Agent — Identifies recurring patterns across incidents.

The Correlator Agent:
1. Periodically scans resolved incidents
2. Identifies recurring failure patterns
3. Stores patterns for the Triage Agent to use
4. Learns and improves confidence scores over time
"""

import json
import structlog

from src.agents.base import BaseAgent

logger = structlog.get_logger(__name__)


class CorrelatorAgent(BaseAgent):
    """Identifies recurring patterns across incidents and builds institutional knowledge."""

    agent_type = "correlator"

    SYSTEM_PROMPT = """You are an expert at identifying recurring patterns in production incidents.
Your job is to:
1. Analyze a batch of resolved incidents
2. Identify common root causes, symptoms, and resolutions
3. Extract reusable patterns that could speed up future triage

Focus on actionable patterns with clear trigger conditions."""

    def process(self, incident_id: str = None) -> dict:
        """Analyze recent incidents for recurring patterns.
        
        Unlike other agents, the Correlator works on batches, not single incidents.
        """
        self.state_manager.set_working({"step": "correlation_analysis"})

        # Get recent resolved incidents
        recent_incidents = self.memory.get_recent_incidents(limit=50)
        resolved = [i for i in recent_incidents if i["status"] == "resolved"]

        if len(resolved) < 2:
            self.state_manager.set_idle()
            return {"status": "insufficient_data", "resolved_count": len(resolved)}

        # Use LLM to identify patterns
        new_patterns = self._identify_patterns(resolved)

        # Store new patterns
        stored_count = 0
        for pattern in new_patterns:
            if pattern.get("pattern_name") and pattern.get("conditions"):
                self.memory.store_pattern(
                    pattern_name=pattern["pattern_name"],
                    conditions=pattern["conditions"],
                    suggested_action=pattern.get("suggested_action", "Investigate further"),
                    confidence=pattern.get("confidence", 0.5),
                )
                stored_count += 1

        self.state_manager.set_idle()
        logger.info(
            "correlation_completed",
            incidents_analyzed=len(resolved),
            patterns_found=stored_count,
        )
        return {
            "status": "completed",
            "incidents_analyzed": len(resolved),
            "patterns_stored": stored_count,
            "patterns": new_patterns,
        }

    def _identify_patterns(self, resolved_incidents: list) -> list:
        """Use LLM to identify recurring patterns in resolved incidents."""
        # Build summary of incidents
        incident_summaries = []
        for inc in resolved_incidents[:20]:  # Limit to avoid token overflow
            incident_summaries.append(
                f"- Title: {inc['title']}\n"
                f"  Severity: {inc['severity']}\n"
                f"  Root Cause: {inc.get('root_cause', 'Unknown')}\n"
                f"  Resolution: {inc.get('resolution', 'Unknown')}\n"
                f"  Symptoms: {json.dumps(inc.get('symptoms', {}))}"
            )

        summaries_text = "\n\n".join(incident_summaries)

        prompt = f"""Analyze these resolved incidents and identify recurring patterns.

RESOLVED INCIDENTS:
{summaries_text}

Identify patterns where the same type of issue keeps recurring. For each pattern, provide:
- pattern_name: short descriptive name
- conditions: object with "keywords" array (trigger words that identify this pattern)
- suggested_action: what to do when this pattern is detected
- confidence: 0.0-1.0 based on how often this pattern appears

Return a JSON array of patterns. Only include patterns you're fairly confident about (seen at least twice).
"""
        result = self.invoke_llm_json(prompt, self.SYSTEM_PROMPT)

        # Handle both list and dict responses
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "patterns" in result:
            return result["patterns"]
        elif isinstance(result, dict) and "error" not in result:
            return [result]
        return []
