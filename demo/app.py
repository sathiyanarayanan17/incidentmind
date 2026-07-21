"""IncidentMind — Premium Demo UI.

A polished, modern interface for the IncidentMind multi-agent
incident response system.

Run with: streamlit run demo/app.py
"""

import sys
import os
import json
from datetime import datetime, timezone

import streamlit as st
import psycopg.rows

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.memory.cockroach import CockroachMemory
from src.memory.embeddings import EmbeddingManager
from src.orchestrator.main import Orchestrator


# ─── Page Config ──────────────────────────────────────────────────

st.set_page_config(
    page_title="IncidentMind — AI Incident Response",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ───────────────────────────────────────────────────

st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global Styles */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Hero Section */
    .hero-container {
        text-align: center;
        padding: 80px 20px 60px 20px;
        position: relative;
        overflow: hidden;
    }

    .hero-container::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 60%;
        height: 100%;
        background: repeating-linear-gradient(
            -45deg,
            transparent,
            transparent 10px,
            rgba(16, 185, 129, 0.05) 10px,
            rgba(16, 185, 129, 0.05) 11px
        );
        pointer-events: none;
    }

    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 100px;
        padding: 8px 16px;
        font-size: 14px;
        margin-bottom: 32px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .hero-badge-highlight {
        background: #ecfdf5;
        color: #059669;
        padding: 2px 10px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        font-weight: 500;
    }

    .hero-title {
        font-size: 64px;
        font-weight: 800;
        color: #111827;
        line-height: 1.1;
        margin-bottom: 24px;
        letter-spacing: -2px;
    }

    .hero-subtitle {
        font-size: 18px;
        color: #6b7280;
        max-width: 600px;
        margin: 0 auto 40px auto;
        line-height: 1.6;
    }

    .hero-subtitle strong {
        color: #111827;
        font-weight: 600;
    }

    /* Buttons */
    .btn-container {
        display: flex;
        justify-content: center;
        gap: 16px;
        margin-bottom: 16px;
    }

    .btn-primary {
        background: #111827;
        color: white;
        padding: 14px 32px;
        border-radius: 100px;
        font-size: 16px;
        font-weight: 500;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        transition: all 0.2s;
        border: none;
        cursor: pointer;
    }

    .btn-primary:hover {
        background: #374151;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    .btn-secondary {
        background: white;
        color: #374151;
        padding: 14px 32px;
        border-radius: 100px;
        font-size: 16px;
        font-weight: 500;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border: 1px solid #d1d5db;
        transition: all 0.2s;
        cursor: pointer;
    }

    .btn-secondary:hover {
        background: #f9fafb;
        border-color: #9ca3af;
    }

    /* Stats Section */
    .stats-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 24px;
        max-width: 900px;
        margin: 0 auto;
        padding: 40px 20px;
    }

    .stat-card {
        background: white;
        border: 1px solid #f3f4f6;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        transition: all 0.2s;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    .stat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.08);
        border-color: #e5e7eb;
    }

    .stat-number {
        font-size: 36px;
        font-weight: 800;
        color: #111827;
        margin-bottom: 4px;
    }

    .stat-label {
        font-size: 13px;
        color: #6b7280;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Feature Cards */
    .features-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 20px;
        max-width: 1000px;
        margin: 40px auto;
        padding: 0 20px;
    }

    .feature-card {
        background: white;
        border: 1px solid #f3f4f6;
        border-radius: 16px;
        padding: 32px;
        transition: all 0.2s;
    }

    .feature-card:hover {
        border-color: #10b981;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.1);
    }

    .feature-icon {
        font-size: 28px;
        margin-bottom: 16px;
    }

    .feature-title {
        font-size: 18px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 8px;
    }

    .feature-desc {
        font-size: 14px;
        color: #6b7280;
        line-height: 1.6;
    }

    /* Section Headers */
    .section-header {
        text-align: center;
        padding: 60px 20px 20px 20px;
    }

    .section-title {
        font-size: 40px;
        font-weight: 800;
        color: #111827;
        letter-spacing: -1px;
        margin-bottom: 12px;
    }

    .section-subtitle {
        font-size: 16px;
        color: #6b7280;
        max-width: 500px;
        margin: 0 auto;
    }

    /* Tech Stack */
    .tech-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        max-width: 800px;
        margin: 30px auto;
        padding: 0 20px;
    }

    .tech-item {
        background: #f9fafb;
        border: 1px solid #f3f4f6;
        border-radius: 12px;
        padding: 16px 20px;
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 14px;
        font-weight: 500;
        color: #374151;
    }

    .tech-icon {
        font-size: 20px;
    }

    /* Dashboard Cards */
    .dashboard-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
    }

    .incident-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 0;
        border-bottom: 1px solid #f3f4f6;
    }

    .incident-row:last-child {
        border-bottom: none;
    }

    .severity-badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
    }

    .severity-1 { background: #fef2f2; color: #dc2626; }
    .severity-2 { background: #fff7ed; color: #ea580c; }
    .severity-3 { background: #fefce8; color: #ca8a04; }
    .severity-4 { background: #eff6ff; color: #2563eb; }
    .severity-5 { background: #f0fdf4; color: #16a34a; }

    /* Footer */
    .footer {
        text-align: center;
        padding: 40px 20px;
        color: #9ca3af;
        font-size: 13px;
        border-top: 1px solid #f3f4f6;
        margin-top: 60px;
    }

    .footer a {
        color: #10b981;
        text-decoration: none;
    }

    /* Streamlit overrides */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        justify-content: center;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 100px;
        padding: 10px 24px;
        font-weight: 500;
    }

    div[data-testid="stExpander"] {
        border: 1px solid #f3f4f6;
        border-radius: 12px;
        margin-bottom: 8px;
    }

    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        padding: 12px 16px;
    }

    .stSelectbox > div > div {
        border-radius: 12px;
    }

    .stButton > button {
        border-radius: 100px;
        padding: 10px 24px;
        font-weight: 500;
        border: 1px solid #e5e7eb;
        transition: all 0.2s;
    }

    .stButton > button:hover {
        border-color: #10b981;
        color: #10b981;
    }

    .stButton > button[kind="primary"] {
        background: #111827;
        color: white;
        border: none;
    }

    .stButton > button[kind="primary"]:hover {
        background: #374151;
    }
</style>
""", unsafe_allow_html=True)


# ─── Session State ────────────────────────────────────────────────

def init_session_state():
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = None
    if "initialized" not in st.session_state:
        st.session_state.initialized = False
    if "page" not in st.session_state:
        st.session_state.page = "home"


def connect_to_db():
    try:
        orchestrator = Orchestrator()
        orchestrator.initialize()
        st.session_state.orchestrator = orchestrator
        st.session_state.initialized = True
        return True
    except Exception as e:
        st.error(f"Connection failed: {e}")
        return False


init_session_state()


# ─── Landing Page ─────────────────────────────────────────────────

def render_landing_page():
    # Hero Section
    st.markdown("""
    <div class="hero-container">
        <div class="hero-badge">
            🧠 Powered by <span class="hero-badge-highlight">CockroachDB × AWS</span> →
        </div>
        <h1 class="hero-title">The incident response<br>infrastructure agents build on</h1>
        <p class="hero-subtitle">
            Multi-agent AI system for <strong>diagnosing</strong>, <strong>correlating</strong>,
            and <strong>resolving</strong> production incidents with persistent, distributed memory.
        </p>
        <div class="btn-container">
            <span class="btn-primary" id="get-started">Launch Dashboard →</span>
            <span class="btn-secondary">See Architecture</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Stats
    st.markdown("""
    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-number">4</div>
            <div class="stat-label">AI Agents</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">0s</div>
            <div class="stat-label">Downtime</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">∞</div>
            <div class="stat-label">Memory</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">&lt;1s</div>
            <div class="stat-label">Search</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Features
    st.markdown("""
    <div class="section-header">
        <h2 class="section-title">How it works</h2>
        <p class="section-subtitle">Four specialized agents collaborate through shared persistent memory</p>
    </div>

    <div class="features-grid">
        <div class="feature-card">
            <div class="feature-icon">🚨</div>
            <div class="feature-title">Triage Agent</div>
            <div class="feature-desc">Classifies incoming alerts, assigns severity, and instantly matches known patterns from memory. Fast-paths known issues in seconds.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🔍</div>
            <div class="feature-title">Diagnosis Agent</div>
            <div class="feature-desc">Performs semantic search over past incidents using CockroachDB vector indexing. Finds similar root causes across your entire history.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🧬</div>
            <div class="feature-title">Correlator Agent</div>
            <div class="feature-desc">Identifies recurring failure patterns across all incidents. Builds institutional knowledge that gets smarter over time.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">✅</div>
            <div class="feature-title">Resolution Agent</div>
            <div class="feature-desc">Suggests fixes based on past successful resolutions, ranked by relevance. Learns from every incident you resolve.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tech Stack
    st.markdown("""
    <div class="section-header">
        <h2 class="section-title">Built with</h2>
        <p class="section-subtitle">Production-grade infrastructure for agentic memory</p>
    </div>

    <div class="tech-grid">
        <div class="tech-item"><span class="tech-icon">🪳</span> CockroachDB Cloud</div>
        <div class="tech-item"><span class="tech-icon">🔌</span> MCP Server</div>
        <div class="tech-item"><span class="tech-icon">📐</span> Vector Indexing</div>
        <div class="tech-item"><span class="tech-icon">☁️</span> Amazon Bedrock</div>
        <div class="tech-item"><span class="tech-icon">⚡</span> AWS Lambda</div>
        <div class="tech-item"><span class="tech-icon">🐳</span> Amazon ECS</div>
        <div class="tech-item"><span class="tech-icon">🦜</span> LangChain</div>
        <div class="tech-item"><span class="tech-icon">🐍</span> Python</div>
        <div class="tech-item"><span class="tech-icon">🗄️</span> Amazon S3</div>
    </div>
    """, unsafe_allow_html=True)

    # CTA
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Launch Dashboard", type="primary", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()

    # Footer
    st.markdown("""
    <div class="footer">
        Built for the <a href="https://cockroachdblabs.devpost.com/">CockroachDB × AWS Hackathon</a> ·
        <a href="https://github.com/sathiyanarayanan17/incidentmind">GitHub</a> ·
        MIT License
    </div>
    """, unsafe_allow_html=True)


# ─── Dashboard ────────────────────────────────────────────────────

def render_dashboard():
    # Top nav
    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        if st.button("← Home"):
            st.session_state.page = "home"
            st.rerun()
    with col2:
        st.markdown("<h2 style='text-align:center; margin:0;'>🧠 IncidentMind Dashboard</h2>", unsafe_allow_html=True)
    with col3:
        if st.session_state.initialized:
            st.markdown("🟢 Connected")
        else:
            st.markdown("🔴 Offline")

    st.markdown("<br>", unsafe_allow_html=True)

    # Connection check
    if not st.session_state.initialized:
        st.markdown("""
        <div style="text-align:center; padding: 60px 20px;">
            <h3>Connect to CockroachDB</h3>
            <p style="color: #6b7280;">Set up your <code>.env</code> file with credentials to get started.</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🔌 Connect", type="primary", use_container_width=True):
                with st.spinner("Connecting to CockroachDB..."):
                    connect_to_db()
        return

    orchestrator = st.session_state.orchestrator

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🚨 New Incident",
        "📋 Active",
        "🔍 Search Memory",
        "🧬 Patterns",
        "🧠 Agent Traces",
    ])

    # Tab 1: New Incident
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("#### Report Incident")
            title = st.text_input("Title", placeholder="e.g., High CPU on prod-web-01")
            severity = st.selectbox("Severity", [1, 2, 3, 4, 5], index=2, format_func=lambda x: {
                1: "🔴 P1 — Critical",
                2: "🟠 P2 — High",
                3: "🟡 P3 — Medium",
                4: "🔵 P4 — Low",
                5: "⚪ P5 — Info",
            }[x])
            source = st.selectbox("Source", ["cloudwatch", "pagerduty", "datadog", "grafana", "manual"])

        with col2:
            st.markdown("#### Symptoms")
            symptoms_text = st.text_area(
                "JSON",
                value='{\n  "error_message": "",\n  "affected_service": "",\n  "metrics": {}\n}',
                height=200,
                label_visibility="collapsed",
            )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Create & Process", type="primary"):
            if not title:
                st.error("Please enter an incident title")
            else:
                try:
                    symptoms = json.loads(symptoms_text)
                except json.JSONDecodeError:
                    symptoms = {"raw": symptoms_text}

                with st.spinner("🤖 Agents processing..."):
                    result = orchestrator.create_and_process_incident(
                        title=title, severity=severity, source=source, symptoms=symptoms,
                    )

                st.success(f"✅ Processed: `{result['incident_id']}`")
                for stage, data in result.get("stages", {}).items():
                    with st.expander(f"📍 {stage.title()}", expanded=True):
                        st.json(data)

    # Tab 2: Active Incidents
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        incidents = orchestrator.memory.get_open_incidents()

        if not incidents:
            st.markdown("""
            <div style="text-align:center; padding:40px; color:#9ca3af;">
                <p style="font-size:48px;">🎉</p>
                <p>No active incidents. All clear!</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for inc in incidents:
                sev = inc["severity"]
                sev_colors = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🔵", 5: "⚪"}
                with st.expander(f"{sev_colors.get(sev, '⚪')} [{inc['status']}] {inc['title']}"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Severity", f"P{sev}")
                    c2.metric("Status", inc["status"])
                    c3.metric("Source", inc.get("source", "—"))
                    if inc.get("root_cause"):
                        st.info(f"**Root Cause:** {inc['root_cause']}")
                    if inc.get("resolution"):
                        st.success(f"**Resolution:** {inc['resolution']}")

    # Tab 3: Semantic Search
    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Search Incident Memory")
        st.caption("Powered by CockroachDB Distributed Vector Indexing")

        search_query = st.text_input("Describe the issue", placeholder="e.g., database connection timeout", label_visibility="collapsed")
        col1, col2 = st.columns(2)
        content_type = col1.selectbox("Type", ["all", "symptom", "root_cause", "resolution"])
        min_sim = col2.slider("Min Similarity", 0.0, 1.0, 0.6)

        if st.button("🔎 Search") and search_query:
            with st.spinner("Searching vectors..."):
                emb = EmbeddingManager()
                results = emb.search_similar(
                    query_text=search_query,
                    content_type=content_type if content_type != "all" else None,
                    min_similarity=min_sim, limit=10,
                )
                emb.close()

            if results:
                for r in results:
                    score = r["similarity"]
                    bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
                    with st.expander(f"`{score:.0%}` {bar}  {r.get('incident_title', 'N/A')}"):
                        st.markdown(f"**Type:** {r['content_type']}")
                        st.markdown(f"**Content:** {r['content_text']}")
                        if r.get("root_cause"):
                            st.markdown(f"**Root Cause:** {r['root_cause']}")
                        if r.get("resolution"):
                            st.markdown(f"**Resolution:** {r['resolution']}")
            else:
                st.warning("No similar incidents found. Try a different query or lower the similarity threshold.")

    # Tab 4: Patterns
    with tab4:
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("#### Learned Patterns")
            st.caption("Discovered by the Correlator Agent over time")
        with col2:
            if st.button("🔄 Run Correlator"):
                with st.spinner("Analyzing..."):
                    result = orchestrator.run_correlator()
                st.json(result)

        patterns = orchestrator.memory.get_patterns()
        if not patterns:
            st.info("No patterns yet. Process more incidents to build institutional knowledge.")
        else:
            for p in patterns:
                conf = p["confidence"]
                bar = "🟩" * int(conf * 10) + "⬜" * (10 - int(conf * 10))
                with st.expander(f"{p['pattern_name']}  {bar} {conf:.0%}"):
                    st.markdown(f"**Action:** {p.get('suggested_action', '—')}")
                    st.markdown(f"**Seen:** {p.get('times_seen', 0)} times")
                    st.json(p.get("conditions", {}))

    # Tab 5: Agent Traces
    with tab5:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Agent Reasoning Traces")
        st.caption("See what agents were thinking during incident processing")

        recent = orchestrator.memory.get_recent_incidents(limit=10)
        if recent:
            selected = st.selectbox(
                "Select Incident",
                recent,
                format_func=lambda x: f"P{x['severity']} — {x['title']}",
            )
            if selected:
                with orchestrator.memory.conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
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
                        st.markdown(f"{emoji} **{mem['agent_type']}** · `{mem['memory_type']}`")
                        st.json(mem["content"])
                        st.divider()
                else:
                    st.info("No traces recorded for this incident yet.")
        else:
            st.info("No incidents to show.")


# ─── Router ───────────────────────────────────────────────────────

if st.session_state.page == "home":
    render_landing_page()
else:
    render_dashboard()
