"""Agent state management with crash recovery.

This module handles persisting agent state to CockroachDB so that
if an agent crashes mid-task, it can resume from where it left off.
"""

import os
import time
import threading
from typing import Optional
from enum import Enum

from dotenv import load_dotenv
import structlog

from src.memory.cockroach import CockroachMemory

load_dotenv()

logger = structlog.get_logger(__name__)


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStateManager:
    """Manages agent lifecycle and state persistence in CockroachDB.
    
    Key capability: crash recovery. If an agent dies mid-task, its state
    in CockroachDB allows another instance to pick up where it left off.
    """

    def __init__(self, agent_type: str, memory: Optional[CockroachMemory] = None):
        self.agent_type = agent_type
        self.memory = memory or CockroachMemory()
        self.agent_id: Optional[str] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_running = False
        self._heartbeat_interval = int(os.getenv("AGENT_HEARTBEAT_INTERVAL", "30"))

    def register(self) -> str:
        """Register this agent and start heartbeat."""
        self.agent_id = self.memory.register_agent(self.agent_type)
        self._start_heartbeat()
        logger.info("agent_state_manager_registered", agent_id=self.agent_id, agent_type=self.agent_type)
        return self.agent_id

    def recover_or_register(self) -> str:
        """Check for a crashed agent of the same type and recover its state, or register new.
        
        This is the key crash-recovery mechanism:
        1. Look for agents of this type that stopped heartbeating
        2. If found, take over their state and resume their task
        3. If not found, register as a new agent
        """
        # Find stale agents (no heartbeat in 3x the interval)
        stale_threshold = self._heartbeat_interval * 3

        with self.memory.conn.cursor() as cur:
            cur.execute(
                """
                SELECT agent_id, current_task, status
                FROM agent_state
                WHERE agent_type = %s
                    AND status IN ('working', 'blocked')
                    AND last_heartbeat < now() - interval '%s seconds'
                ORDER BY last_heartbeat DESC
                LIMIT 1
                """,
                (self.agent_type, stale_threshold),
            )
            row = cur.fetchone()

        if row:
            # Recover stale agent
            self.agent_id = str(row[0])
            current_task = row[1]
            logger.info(
                "agent_recovered",
                agent_id=self.agent_id,
                previous_task=current_task,
            )
            # Update heartbeat to claim this agent
            self.memory.update_agent_state(self.agent_id, AgentStatus.WORKING, current_task)
            self._start_heartbeat()
            return self.agent_id
        else:
            return self.register()

    def set_working(self, task: dict):
        """Mark agent as working on a task."""
        if not self.agent_id:
            raise RuntimeError("Agent not registered")
        self.memory.update_agent_state(self.agent_id, AgentStatus.WORKING, task)
        logger.info("agent_working", agent_id=self.agent_id, task=task)

    def set_idle(self):
        """Mark agent as idle (task completed)."""
        if not self.agent_id:
            raise RuntimeError("Agent not registered")
        self.memory.update_agent_state(self.agent_id, AgentStatus.IDLE, None)

    def set_completed(self):
        """Mark agent as completed."""
        if not self.agent_id:
            raise RuntimeError("Agent not registered")
        self.memory.update_agent_state(self.agent_id, AgentStatus.COMPLETED, None)

    def set_failed(self, error: str):
        """Mark agent as failed with error info."""
        if not self.agent_id:
            raise RuntimeError("Agent not registered")
        self.memory.update_agent_state(
            self.agent_id, AgentStatus.FAILED, {"error": error}
        )
        logger.error("agent_failed", agent_id=self.agent_id, error=error)

    def get_current_task(self) -> Optional[dict]:
        """Get the current task (useful for recovery)."""
        if not self.agent_id:
            return None
        state = self.memory.get_agent_state(self.agent_id)
        return state.get("current_task") if state else None

    def store_reasoning(self, incident_id: str, memory_type: str, content: dict):
        """Store a reasoning trace for audit and recovery."""
        if not self.agent_id:
            raise RuntimeError("Agent not registered")
        self.memory.store_memory(self.agent_id, incident_id, memory_type, content)

    def shutdown(self):
        """Gracefully shutdown: stop heartbeat and mark as idle."""
        self._heartbeat_running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        if self.agent_id:
            self.set_idle()
        self.memory.close()
        logger.info("agent_shutdown", agent_id=self.agent_id)

    # ─── Private ──────────────────────────────────────────────────────

    def _start_heartbeat(self):
        """Start background heartbeat thread."""
        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True
        )
        self._heartbeat_thread.start()

    def _heartbeat_loop(self):
        """Continuously send heartbeats to CockroachDB."""
        while self._heartbeat_running:
            try:
                if self.agent_id:
                    self.memory.heartbeat(self.agent_id)
            except Exception as e:
                logger.warning("heartbeat_failed", error=str(e))
            time.sleep(self._heartbeat_interval)
