"""Main orchestrator for IncidentMind agents.

This is the entry point that:
1. Initializes all agents
2. Listens for new incidents
3. Routes incidents through the agent pipeline:
   Triage → Diagnosis → Resolution
4. Runs the Correlator periodically
"""

import time
import threading
import structlog

from src.memory.cockroach import CockroachMemory
from src.agents.triage import TriageAgent
from src.agents.diagnosis import DiagnosisAgent
from src.agents.correlator import CorrelatorAgent
from src.agents.resolution import ResolutionAgent

logger = structlog.get_logger(__name__)


class Orchestrator:
    """Orchestrates the multi-agent incident response pipeline."""

    def __init__(self):
        self.memory = CockroachMemory()
        self.triage_agent = TriageAgent()
        self.diagnosis_agent = DiagnosisAgent()
        self.correlator_agent = CorrelatorAgent()
        self.resolution_agent = ResolutionAgent()
        self._running = False

    def initialize(self):
        """Initialize schema and start all agents."""
        logger.info("orchestrator_initializing")
        self.memory.initialize_schema()
        self.memory.create_vector_index()

        # Start agents with crash recovery
        self.triage_agent.start()
        self.diagnosis_agent.start()
        self.correlator_agent.start()
        self.resolution_agent.start()

        logger.info("orchestrator_ready")

    def process_incident(self, incident_id: str) -> dict:
        """Run full incident response pipeline.
        
        Pipeline: Triage → Diagnosis → Resolution
        Each step persists state so recovery is possible at any point.
        """
        logger.info("pipeline_started", incident_id=incident_id)
        results = {"incident_id": incident_id, "stages": {}}

        # Stage 1: Triage
        triage_result = self.triage_agent.process(incident_id)
        results["stages"]["triage"] = triage_result

        if triage_result.get("status") == "pattern_matched":
            # Known issue — skip diagnosis, go to resolution
            resolution_result = self.resolution_agent.process(incident_id)
            results["stages"]["resolution"] = resolution_result
            logger.info("pipeline_fast_path", incident_id=incident_id)
            return results

        # Stage 2: Diagnosis
        if triage_result.get("needs_diagnosis"):
            diagnosis_result = self.diagnosis_agent.process(incident_id)
            results["stages"]["diagnosis"] = diagnosis_result

        # Stage 3: Resolution
        resolution_result = self.resolution_agent.process(incident_id)
        results["stages"]["resolution"] = resolution_result

        logger.info("pipeline_completed", incident_id=incident_id)
        return results

    def run_correlator(self):
        """Run the Correlator Agent to find patterns."""
        return self.correlator_agent.process()

    def create_and_process_incident(
        self, title: str, severity: int, source: str = "manual", symptoms: dict = None
    ) -> dict:
        """Convenience method: create an incident and process it through the pipeline."""
        incident_id = self.memory.create_incident(
            title=title, severity=severity, source=source, symptoms=symptoms
        )
        return self.process_incident(incident_id)

    def run(self, poll_interval: int = 10):
        """Main loop: poll for new incidents and process them.
        
        In production this would be event-driven via Lambda/SQS.
        This polling loop is for local development and demo.
        """
        self._running = True
        logger.info("orchestrator_running", poll_interval=poll_interval)

        # Run correlator in background every 5 minutes
        correlator_thread = threading.Thread(
            target=self._correlator_loop, daemon=True
        )
        correlator_thread.start()

        try:
            while self._running:
                # Check for unprocessed open incidents
                open_incidents = self.memory.get_open_incidents()
                for incident in open_incidents:
                    if incident["status"] == "open":
                        try:
                            self.process_incident(str(incident["incident_id"]))
                        except Exception as e:
                            logger.error(
                                "pipeline_error",
                                incident_id=str(incident["incident_id"]),
                                error=str(e),
                            )
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("orchestrator_stopping")
        finally:
            self.shutdown()

    def shutdown(self):
        """Gracefully shutdown all agents."""
        self._running = False
        self.triage_agent.shutdown()
        self.diagnosis_agent.shutdown()
        self.correlator_agent.shutdown()
        self.resolution_agent.shutdown()
        self.memory.close()
        logger.info("orchestrator_shutdown")

    def _correlator_loop(self):
        """Periodically run the correlator."""
        while self._running:
            time.sleep(300)  # Every 5 minutes
            try:
                self.run_correlator()
            except Exception as e:
                logger.error("correlator_error", error=str(e))


def main():
    """Entry point for the orchestrator."""
    orchestrator = Orchestrator()
    orchestrator.initialize()
    orchestrator.run()


if __name__ == "__main__":
    main()
