"""Streamlit demo UI for IncidentMind.

Run with: streamlit run demo/app.py
"""

import sys
import os
import json
from datetime import datetime, timezone

import streamlit as st

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.memory.cockroach import CockroachMemory
from src.memory.embeddings import EmbeddingManager
from src.orchestrator.main import Orchestrator


def init_session_state():
    """Initialize Streamlit session state."""
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = None
    if "initialized" not in st.session_state:
        st.session_state.initialized = False


def connect_to_db():
    """Initialize connection to CockroachDB."""
    try:
        orchestrator = Orchestrator()
        orchestrator.initialize()
        st.session_state.orchestrator = orchestrator
        st.session_state.initialized = True
        return True
    except Exception as e:
        st.error(f"Failed to connect: {e}")
        return False


def main():
    st.set_page_config(
        page_title="IncidentMind 🧠⚡",
        page_icon="🧠",
        layout="wide",
    )

    st.title("🧠⚡ IncidentMind")
    st.caption("Multi-Agent DevOps Incident Responder with Persistent Agentic Memory")

    init_session_state()

    # Sidebar: Connection
    with st.sidebar:
        st.header("🔌 Connection")
        if st.session_state.initialized:
            st.success("✅ Connected to CockroachDB")
        else:
            if st.button("Connect to CockroachDB"):
                with st.spinner("Connecting..."):
                    connect_to_db()

        st.divider()
        st.header("📊 Quick Stats")
        if st.session_state.initialized:
            memory = st.session_state.orchestrator.memory
            open_incidents = memory.get_open_incidents()
            recent = memory.get_recent_incidents(limit=100)
            resolved = [i for i in recent if i["status"] == "resolved"]
            st.metric("Open Incidents", len(open_incidents))
            st.metric("Resolved (recent)", len(resolved))
            patterns = memory.get_patterns()
            st.metric("Known Patterns", len(patterns))

    if not st.session_state.initialized:
        st.info("👈 Connect to CockroachDB to get started")
        st.markdown("""
        ### Setup Instructions
        1. Copy `.env.example` to `.env`
        2. Set your `COCKROACHDB_URL` and AWS credentials
        3. Click **Connect to CockroachDB** in the sidebar
        """)
        return

    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🚨 New Incident",
        "📋 Active Incidents",
        "🔍 Semantic Search",
        "🧬 Patterns",
        "🧠 Agent Memory",
    ])

    orchestrator = st.session_state.orchestrator

    # Tab 1: Create New Incident
    with tab1:
        st.header("Report New Incident")
        col1, col2 = st.columns(2)

        with col1:
            title = st.text_input("Incident Title", placeholder="e.g., High CPU usage on prod-web-01")
            severity = st.selectbox("Severity", [1, 2, 3, 4, 5], index=2, format_func=lambda x: {
                1: "1 - Critical",
                2: "2 - High",
                3: "3 - Medium",
                4: "4 - Low",
                5: "5 - Info",
            }[x])
            source = st.selectbox("Source", ["manual", "cloudwatch", "pagerduty", "datadog", "grafana"])

        with col2:
            st.markdown("**Symptoms (JSON)**")
            symptoms_text = st.text_area(
                "Symptoms",
                value='{\n  "error_message": "",\n  "affected_service": "",\n  "metrics": {}\n}',
                height=150,
                label_visibility="collapsed",
            )

        if st.button("🚀 Create & Process Incident", type="primary"):
            if not title:
                st.error("Please enter an incident title")
            else:
                try:
                    symptoms = json.loads(symptoms_text)
                except json.JSONDecodeError:
                    symptoms = {"raw": symptoms_text}

                with st.spinner("🤖 Agents processing incident..."):
                    result = orchestrator.create_and_process_incident(
                        title=title,
                        severity=severity,
                        source=source,
                        symptoms=symptoms,
                    )

                st.success(f"✅ Incident processed: {result['incident_id']}")

                # Show pipeline results
                for stage, data in result.get("stages", {}).items():
                    with st.expander(f"Stage: {stage.title()}", expanded=True):
                        st.json(data)

    # Tab 2: Active Incidents
    with tab2:
        st.header("Active Incidents")
        if st.button("🔄 Refresh"):
            st.rerun()

        incidents = orchestrator.memory.get_open_incidents()
        if not incidents:
            st.info("No active incidents")
        else:
            for inc in incidents:
                severity_emoji = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🔵", 5: "⚪"}.get(inc["severity"], "⚪")
                with st.expander(f"{severity_emoji} [{inc['status']}] {inc['title']}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Severity", inc["severity"])
                    col2.metric("Status", inc["status"])
                    col3.metric("Source", inc.get("source", "N/A"))
                    if inc.get("root_cause"):
                        st.markdown(f"**Root Cause:** {inc['root_cause']}")
                    if inc.get("resolution"):
                        st.markdown(f"**Resolution:** {inc['resolution']}")
                    if inc.get("symptoms"):
                        st.json(inc["symptoms"])

    # Tab 3: Semantic Search
    with tab3:
        st.header("🔍 Search Past Incidents (Vector Similarity)")
        st.caption("Uses CockroachDB Distributed Vector Indexing for semantic search")

        search_query = st.text_input("Describe the issue", placeholder="e.g., database connection timeout in payment service")
        col1, col2 = st.columns(2)
        content_type = col1.selectbox("Content Type", ["all", "symptom", "root_cause", "resolution"])
        min_similarity = col2.slider("Min Similarity", 0.0, 1.0, 0.6)

        if st.button("🔎 Search") and search_query:
            with st.spinner("Searching vector index..."):
                embeddings = EmbeddingManager()
                results = embeddings.search_similar(
                    query_text=search_query,
                    content_type=content_type if content_type != "all" else None,
                    min_similarity=min_similarity,
                    limit=10,
                )
                embeddings.close()

            if results:
                st.success(f"Found {len(results)} similar records")
                for r in results:
                    with st.expander(f"[{r['similarity']:.2f}] {r.get('incident_title', 'N/A')} ({r['content_type']})"):
                        st.markdown(f"**Content:** {r['content_text']}")
                        if r.get("root_cause"):
                            st.markdown(f"**Root Cause:** {r['root_cause']}")
                        if r.get("resolution"):
                            st.markdown(f"**Resolution:** {r['resolution']}")
            else:
                st.warning("No similar incidents found")

    # Tab 4: Correlation Patterns
    with tab4:
        st.header("🧬 Learned Correlation Patterns")
        st.caption("Patterns discovered by the Correlator Agent over time")

        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Run Correlator Now"):
                with st.spinner("Analyzing patterns..."):
                    result = orchestrator.run_correlator()
                st.json(result)

        patterns = orchestrator.memory.get_patterns()
        if not patterns:
            st.info("No patterns discovered yet. Process more incidents to build patterns.")
        else:
            for p in patterns:
                confidence_bar = "🟩" * int(p["confidence"] * 10) + "⬜" * (10 - int(p["confidence"] * 10))
                with st.expander(f"{p['pattern_name']} ({confidence_bar} {p['confidence']:.0%})"):
                    st.markdown(f"**Suggested Action:** {p.get('suggested_action', 'N/A')}")
                    st.markdown(f"**Times Seen:** {p.get('times_seen', 0)}")
                    st.json(p.get("conditions", {}))

    # Tab 5: Agent Memory
    with tab5:
        st.header("🧠 Agent Reasoning Traces")
        st.caption("View what agents were thinking during incident processing")

        recent = orchestrator.memory.get_recent_incidents(limit=10)
        if recent:
            selected = st.selectbox(
                "Select Incident",
                recent,
                format_func=lambda x: f"[{x['severity']}] {x['title']}",
            )
            if selected:
                with orchestrator.memory.conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT am.*, ag.agent_type
                        FROM agent_memory am
                        JOIN agent_state ag ON ag.agent_id = am.agent_id
                        WHERE am.incident_id = %s
                        ORDER BY am.created_at ASC
                        """,
                        (str(selected["incident_id"]),),
                    )
                    import psycopg2.extras
                    cur = orchestrator.memory.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cur.execute(
                        """
                        SELECT am.memory_type, am.content, am.created_at, ag.agent_type
                        FROM agent_memory am
                        JOIN agent_state ag ON ag.agent_id = am.agent_id
                        WHERE am.incident_id = %s
                        ORDER BY am.created_at ASC
                        """,
                        (str(selected["incident_id"]),),
                    )
                    memories = cur.fetchall()

                if memories:
                    for mem in memories:
                        emoji = {"observation": "👁️", "hypothesis": "💡", "action": "⚡", "result": "✅"}.get(mem["memory_type"], "📝")
                        st.markdown(f"{emoji} **[{mem['agent_type']}]** {mem['memory_type']}")
                        st.json(mem["content"])
                        st.caption(str(mem["created_at"]))
                        st.divider()
                else:
                    st.info("No reasoning traces for this incident")
        else:
            st.info("No incidents yet")


if __name__ == "__main__":
    main()
