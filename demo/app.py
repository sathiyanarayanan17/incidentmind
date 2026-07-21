"""IncidentMind - Premium Multi-Agent DevOps Incident Responder Demo.

A comprehensive, production-quality Streamlit demo showcasing:
- Live Incident Simulation
- Agent Activity Feed
- Incident Timeline Visualization
- Knowledge Graph View
- MCP Server Live Query Panel
- Health Dashboard
- Audit Log & RBAC
- Multi-Region Indicator
- Rate Limiting & Circuit Breaker
- Dark/Light Theme Toggle
- Incident Heatmap
- Resolution Playbook Library
- Agent Performance Metrics
- Export & Sharing
- Confidence Calibration
- Predictive Alerts
- Multi-Agent Chat
- Runbook Execution Dry Run
- Incident Deduplication
- MTTR Dashboard
- Top Failure Categories
- Agent ROI Calculator

Run with: streamlit run demo/app.py
"""

import sys
import os
import json
import random
import time
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
import math

import streamlit as st
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#  Conditional Imports (graceful fallback for demo mode) 

DEMO_MODE = True
try:
    from src.memory.cockroach import CockroachMemory
    from src.memory.embeddings import EmbeddingManager
    from src.orchestrator.main import Orchestrator
    if os.getenv("COCKROACHDB_URL"):
        DEMO_MODE = False
except ImportError:
    pass

#  Page Config 

st.set_page_config(
    page_title="IncidentMind - AI Incident Response",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

#  Session State Init 

if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"
if "incidents" not in st.session_state:
    st.session_state.incidents = []
if "agent_feed" not in st.session_state:
    st.session_state.agent_feed = []
if "audit_log" not in st.session_state:
    st.session_state.audit_log = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "multi_agent_chat" not in st.session_state:
    st.session_state.multi_agent_chat = []
if "confidence_votes" not in st.session_state:
    st.session_state.confidence_votes = {"up": 0, "down": 0}
if "demo_ticker" not in st.session_state:
    st.session_state.demo_ticker = 0
if "runbook_approvals" not in st.session_state:
    st.session_state.runbook_approvals = {}
if "region" not in st.session_state:
    st.session_state.region = random.choice(["us-east-1", "eu-west-1", "ap-south-1"])
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "user_role" not in st.session_state:
    st.session_state.user_role = "Admin"


#  Theme Colors 

def get_colors():
    if st.session_state.theme == "dark":
        return {
            "bg": "#111111",
            "surface": "#1a1a1a",
            "surface2": "#2a2a2a",
            "text": "#f5f5f5",
            "text_secondary": "#999999",
            "accent": "#10b981",
            "accent_hover": "#059669",
            "danger": "#ef4444",
            "warning": "#f59e0b",
            "info": "#3b82f6",
            "border": "#2a2a2a",
            "card_shadow": "rgba(0,0,0,0.3)",
        }
    else:
        return {
            "bg": "#f5f7f5",
            "surface": "#ffffff",
            "surface2": "#f0f2f0",
            "text": "#111827",
            "text_secondary": "#6b7280",
            "accent": "#10b981",
            "accent_hover": "#059669",
            "danger": "#ef4444",
            "warning": "#f59e0b",
            "info": "#3b82f6",
            "border": "#e5e7eb",
            "card_shadow": "rgba(0,0,0,0.06)",
        }


#  Mock Data Generators 

INCIDENT_TYPES = [
    {"title": "Database Connection Pool Exhausted", "service": "payment-service", "severity": "critical"},
    {"title": "API Latency Spike > 5s", "service": "gateway-api", "severity": "high"},
    {"title": "Memory Leak Detected in Worker", "service": "task-worker", "severity": "high"},
    {"title": "SSL Certificate Expiring in 24h", "service": "auth-service", "severity": "medium"},
    {"title": "Disk Usage at 92%", "service": "logging-service", "severity": "warning"},
    {"title": "Kubernetes Pod CrashLoopBackOff", "service": "ml-inference", "severity": "critical"},
    {"title": "Redis Cache Miss Rate > 80%", "service": "cache-layer", "severity": "high"},
    {"title": "DNS Resolution Timeout", "service": "service-mesh", "severity": "critical"},
    {"title": "Rate Limit Exceeded on /api/v2", "service": "gateway-api", "severity": "medium"},
    {"title": "Deadlock Detected in Transaction", "service": "order-service", "severity": "critical"},
    {"title": "Container OOMKilled", "service": "data-pipeline", "severity": "high"},
    {"title": "Healthcheck Failing on Node 3", "service": "cluster-mgmt", "severity": "warning"},
    {"title": "Unauthorized Access Attempt Blocked", "service": "auth-service", "severity": "medium"},
    {"title": "Message Queue Backlog > 10k", "service": "event-bus", "severity": "high"},
    {"title": "CDN Cache Invalidation Storm", "service": "cdn-proxy", "severity": "medium"},
]

AGENT_NAMES = ["TriageAgent", "DiagnosisAgent", "ResolutionAgent", "CorrelatorAgent"]

AGENT_ACTIONS = [
    "Analyzing incident severity based on historical patterns",
    "Correlating with 3 similar incidents from past 7 days",
    "Running root cause analysis via chain-of-thought",
    "Querying CockroachDB for related service topology",
    "Generating resolution playbook from knowledge base",
    "Executing semantic search over past resolutions",
    "Calculating blast radius across dependent services",
    "Triggering automated runbook Step 1/3",
    "Validating fix with canary deployment check",
    "Updating incident status and notifying on-call",
]

RESOLUTION_PLAYBOOKS = [
    {"name": "DB Connection Pool Recovery", "steps": ["Scale connection pool to 200", "Restart idle connections", "Enable connection recycling", "Monitor for 5 minutes"], "success_rate": 94},
    {"name": "Memory Leak Mitigation", "steps": ["Trigger heap dump", "Identify leaking objects", "Apply memory limit patch", "Rolling restart pods"], "success_rate": 87},
    {"name": "Pod CrashLoop Recovery", "steps": ["Check resource limits", "Inspect container logs", "Verify health probes", "Redeploy with fixes"], "success_rate": 91},
    {"name": "SSL Certificate Renewal", "steps": ["Generate new CSR", "Submit to CA", "Deploy new cert", "Verify TLS handshake"], "success_rate": 99},
    {"name": "Cache Layer Recovery", "steps": ["Flush stale entries", "Warm cache with hot keys", "Adjust TTL policies", "Monitor hit rate"], "success_rate": 88},
    {"name": "DNS Resolution Fix", "steps": ["Check CoreDNS pods", "Flush DNS cache", "Verify upstream resolvers", "Test resolution latency"], "success_rate": 95},
    {"name": "Queue Backlog Drain", "steps": ["Scale consumers 3x", "Enable batch processing", "Skip poison messages", "Reset consumer offsets"], "success_rate": 82},
    {"name": "Disk Space Recovery", "steps": ["Identify large files", "Rotate/compress logs", "Clean temp files", "Expand volume if needed"], "success_rate": 96},
]

REGIONS = [
    {"name": "us-east-1", "label": "N. Virginia", "lat": 39.0, "lon": -77.5},
    {"name": "eu-west-1", "label": "Ireland", "lat": 53.0, "lon": -8.0},
    {"name": "ap-south-1", "label": "Mumbai", "lat": 19.0, "lon": 72.8},
]

RBAC_ROLES = [
    {"role": "Admin", "permissions": ["read", "write", "delete", "approve", "configure"], "color": "#ef4444"},
    {"role": "SRE Lead", "permissions": ["read", "write", "approve", "execute_runbook"], "color": "#f59e0b"},
    {"role": "Engineer", "permissions": ["read", "write", "execute_runbook"], "color": "#3b82f6"},
    {"role": "Viewer", "permissions": ["read"], "color": "#6b7280"},
]


def generate_incident():
    """Generate a realistic mock incident."""
    template = random.choice(INCIDENT_TYPES)
    incident_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc)
    return {
        "id": f"INC-{incident_id.upper()}",
        "title": template["title"],
        "service": template["service"],
        "severity": template["severity"],
        "status": random.choice(["open", "triaging", "diagnosing", "resolving", "resolved"]),
        "created_at": now - timedelta(minutes=random.randint(1, 120)),
        "updated_at": now,
        "assigned_agent": random.choice(AGENT_NAMES),
        "region": random.choice(["us-east-1", "eu-west-1", "ap-south-1"]),
        "confidence": round(random.uniform(0.72, 0.98), 2),
        "mttr_minutes": random.randint(3, 45),
    }


def generate_agent_action():
    """Generate a mock agent action for the feed."""
    return {
        "timestamp": datetime.now(timezone.utc),
        "agent": random.choice(AGENT_NAMES),
        "action": random.choice(AGENT_ACTIONS),
        "incident_id": f"INC-{str(uuid.uuid4())[:8].upper()}",
        "duration_ms": random.randint(50, 3000),
    }


def seed_demo_data():
    """Seed initial demo data if empty."""
    if not st.session_state.incidents:
        st.session_state.incidents = [generate_incident() for _ in range(12)]
    if not st.session_state.agent_feed:
        st.session_state.agent_feed = [generate_agent_action() for _ in range(20)]
    if not st.session_state.audit_log:
        st.session_state.audit_log = [
            {"ts": datetime.now(timezone.utc) - timedelta(minutes=i*3),
             "user": random.choice(["admin@company.com", "sre-lead@company.com", "engineer@company.com"]),
             "action": random.choice(["viewed_incident", "approved_runbook", "escalated", "changed_severity", "exported_report"]),
             "target": f"INC-{str(uuid.uuid4())[:8].upper()}"}
            for i in range(30)
        ]

seed_demo_data()



#  CSS Injection 

def inject_css():
    """Inject comprehensive custom CSS based on current theme."""
    c = get_colors()
    st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Global */
    .stApp {{
        font-family: 'Inter', sans-serif;
        background-color: {c['bg']};
        color: {c['text']};
    }}

    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .stDeployButton {{display: none;}}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: {c['surface']};
        border-right: 1px solid {c['border']};
    }}
    section[data-testid="stSidebar"] .stMarkdown p {{
        color: {c['text']};
    }}

    /* Cards */
    .metric-card {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 24px;
        margin: 8px 0;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px {c['card_shadow']};
    }}
    .metric-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 25px {c['card_shadow']};
        border-color: {c['accent']};
    }}
    .metric-value {{
        font-size: 2.5rem;
        font-weight: 800;
        color: {c['accent']};
        font-family: 'JetBrains Mono', monospace;
    }}
    .metric-label {{
        font-size: 0.85rem;
        color: {c['text_secondary']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 4px;
    }}

    /* Hero */
    .hero-container {{
        text-align: center;
        padding: 60px 20px 40px 20px;
        position: relative;
        overflow: hidden;
    }}
    .hero-container::before {{
        content: '';
        position: absolute;
        top: 0; right: 0;
        width: 60%; height: 100%;
        background: repeating-linear-gradient(
            -45deg, transparent, transparent 10px,
            rgba(16, 185, 129, 0.04) 10px,
            rgba(16, 185, 129, 0.04) 11px
        );
        pointer-events: none;
    }}
    .hero-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 100px;
        padding: 8px 16px;
        font-size: 14px;
        margin-bottom: 24px;
        color: {c['text']};
    }}
    .hero-badge-highlight {{
        background: rgba(16,185,129,0.1);
        color: {c['accent']};
        padding: 2px 10px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        font-weight: 500;
    }}
    .hero-title {{
        font-size: 3.5rem;
        font-weight: 900;
        line-height: 1.1;
        margin-bottom: 16px;
        color: {c['text']};
    }}
    .hero-title .gradient {{
        background: linear-gradient(135deg, {c['accent']}, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .hero-subtitle {{
        font-size: 1.2rem;
        color: {c['text_secondary']};
        max-width: 600px;
        margin: 0 auto 32px auto;
    }}

    /* Stat Grid */
    .stat-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin: 24px 0;
    }}

    /* Feed Item */
    .feed-item {{
        display: flex;
        gap: 12px;
        padding: 12px 16px;
        border-left: 3px solid {c['accent']};
        background: {c['surface']};
        border-radius: 0 8px 8px 0;
        margin: 8px 0;
        font-size: 0.9rem;
        transition: background 0.2s;
    }}
    .feed-item:hover {{
        background: {c['surface2']};
    }}
    .feed-agent {{
        font-weight: 600;
        color: {c['accent']};
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
    }}
    .feed-action {{
        color: {c['text']};
    }}
    .feed-time {{
        color: {c['text_secondary']};
        font-size: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
    }}

    /* Timeline */
    .timeline-container {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0;
        margin: 32px 0;
    }}
    .timeline-step {{
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 16px 24px;
        position: relative;
    }}
    .timeline-dot {{
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        margin-bottom: 8px;
    }}
    .timeline-dot.active {{
        background: {c['accent']};
        color: white;
        box-shadow: 0 0 20px rgba(16,185,129,0.4);
    }}
    .timeline-dot.pending {{
        background: {c['surface2']};
        color: {c['text_secondary']};
    }}
    .timeline-dot.done {{
        background: rgba(16,185,129,0.2);
        color: {c['accent']};
    }}
    .timeline-label {{
        font-size: 0.8rem;
        font-weight: 600;
        color: {c['text']};
    }}
    .timeline-connector {{
        width: 60px;
        height: 2px;
        background: {c['border']};
        margin-bottom: 24px;
    }}
    .timeline-connector.done {{
        background: {c['accent']};
    }}

    /* Severity badges */
    .badge {{
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }}
    .badge-critical {{ background: rgba(239,68,68,0.15); color: #ef4444; }}
    .badge-high {{ background: rgba(245,158,11,0.15); color: #f59e0b; }}
    .badge-medium {{ background: rgba(59,130,246,0.15); color: #3b82f6; }}
    .badge-warning {{ background: rgba(168,85,247,0.15); color: #a855f7; }}
    .badge-resolved {{ background: rgba(16,185,129,0.15); color: #10b981; }}

    /* Table styles */
    .styled-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
    }}
    .styled-table th {{
        background: {c['surface2']};
        padding: 12px 16px;
        text-align: left;
        font-weight: 600;
        color: {c['text_secondary']};
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
    }}
    .styled-table td {{
        padding: 12px 16px;
        border-bottom: 1px solid {c['border']};
        color: {c['text']};
    }}
    .styled-table tr:hover td {{
        background: {c['surface']};
    }}

    /* Chat */
    .chat-bubble {{
        padding: 12px 16px;
        border-radius: 12px;
        margin: 8px 0;
        max-width: 80%;
        font-size: 0.9rem;
    }}
    .chat-user {{
        background: {c['accent']};
        color: white;
        margin-left: auto;
        border-bottom-right-radius: 4px;
    }}
    .chat-agent {{
        background: {c['surface2']};
        color: {c['text']};
        border-bottom-left-radius: 4px;
    }}

    /* Section Headers */
    .section-header {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {c['text']};
        margin: 32px 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid {c['accent']};
        display: inline-block;
    }}

    /* Progress bar custom */
    .progress-bar {{
        background: {c['surface2']};
        border-radius: 8px;
        height: 8px;
        overflow: hidden;
        margin: 8px 0;
    }}
    .progress-fill {{
        height: 100%;
        border-radius: 8px;
        background: linear-gradient(90deg, {c['accent']}, #06b6d4);
        transition: width 0.5s ease;
    }}

    /* Nav items */
    .nav-item {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 16px;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
        color: {c['text_secondary']};
        font-size: 0.9rem;
        margin: 2px 0;
    }}
    .nav-item:hover, .nav-item.active {{
        background: rgba(16,185,129,0.1);
        color: {c['accent']};
    }}

    /* Heatmap cell */
    .heatmap-cell {{
        width: 14px;
        height: 14px;
        border-radius: 3px;
        display: inline-block;
        margin: 1px;
    }}

    /* Knowledge graph node */
    .kg-node {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: {c['surface2']};
        border: 2px solid {c['accent']};
        font-size: 0.7rem;
        font-weight: 600;
        color: {c['text']};
        margin: 8px;
        transition: transform 0.2s;
    }}
    .kg-node:hover {{
        transform: scale(1.1);
    }}

    /* Buttons override */
    .stButton > button {{
        background: {c['accent']} !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 8px 24px !important;
        transition: all 0.2s !important;
    }}
    .stButton > button:hover {{
        background: {c['accent_hover']} !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(16,185,129,0.3) !important;
    }}
</style>
""", unsafe_allow_html=True)

inject_css()


#  Landing Page (Front Page) 

def render_landing_page():
    c = get_colors()

    # Top navigation bar with working buttons
    nav_col1, nav_col2, nav_col3, nav_col4, nav_col5, nav_col6, nav_col7 = st.columns([2, 1, 1, 1, 1, 1, 1])
    with nav_col1:
        st.markdown(f'<div style="font-size:1.2rem; font-weight:900; color:{c["text"]}; padding:8px 0;">IncidentMind</div>', unsafe_allow_html=True)
    with nav_col2:
        if st.button("Features", key="nav_features"):
            pass  # scrolls to features section below
    with nav_col3:
        if st.button("How it Works", key="nav_howitworks"):
            pass
    with nav_col4:
        if st.button("Architecture", key="nav_arch"):
            pass
    with nav_col5:
        if st.button("Docs", key="nav_docs"):
            pass
    with nav_col6:
        if st.button("Sign In", key="nav_signin_btn"):
            st.session_state.current_page = "signin"
            st.rerun()
    with nav_col7:
        if st.button("Dashboard", key="nav_dash_btn", type="primary"):
            st.session_state.current_page = "signin"
            st.rerun()

    # SECTION 1: Hero
    st.markdown(f"""<div style="text-align:center; padding:60px 20px 40px 20px; position:relative; overflow:hidden;">
<div style="position:absolute; top:0; right:0; width:50%; height:100%; background:repeating-linear-gradient(-55deg, transparent, transparent 8px, rgba(16,185,129,0.06) 8px, rgba(16,185,129,0.06) 9px); pointer-events:none;"></div>
<div style="display:inline-flex; align-items:center; gap:8px; background:{c['surface']}; border:1px solid {c['border']}; border-radius:100px; padding:8px 20px; font-size:0.85rem; color:{c['text_secondary']}; margin-bottom:40px;">Powered by AI <span style="background:rgba(16,185,129,0.12); color:{c['accent']}; padding:3px 12px; border-radius:4px; font-family:JetBrains Mono,monospace; font-size:0.75rem; font-weight:600; margin-left:8px;">Agentic Memory</span></div>
<h1 style="font-size:3.8rem; font-weight:900; color:{c['text']}; line-height:1.05; margin:0 auto 24px auto; max-width:800px; letter-spacing:-2px;">The incident response infrastructure agents build on</h1>
<p style="font-size:1.1rem; color:{c['text_secondary']}; max-width:600px; margin:0 auto 40px auto; line-height:1.6;">End-to-end incident detection, diagnosis, and resolution for production systems, SRE teams, and AI agents.</p>
</div>""", unsafe_allow_html=True)

    # CTA Buttons
    col1, col2, col3, col4, col5 = st.columns([2, 1.2, 0.5, 1.2, 2])
    with col2:
        if st.button("Get started", type="primary", use_container_width=True, key="cta_start"):
            st.session_state.current_page = "signin"
            st.rerun()
    with col4:
        if st.button("See live demo", use_container_width=True, key="cta_demo"):
            st.session_state.logged_in = True
            st.session_state.user_name = "Demo User"
            st.session_state.user_email = "demo@incidentmind.ai"
            st.session_state.user_role = "Viewer"
            st.session_state.current_page = "home"
            st.rerun()

    st.markdown(f'<p style="text-align:center; font-size:0.85rem; color:{c["text_secondary"]}; margin-top:8px;">Open source - <a href="https://github.com/sathiyanarayanan17/incidentmind" style="color:{c["accent"]};">View on GitHub</a></p>', unsafe_allow_html=True)

    # SECTION 2: Dashboard Preview
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""<div style="max-width:900px; margin:0 auto; background:{c['surface']}; border:1px solid {c['border']}; border-radius:12px; overflow:hidden; box-shadow:0 20px 60px {c['card_shadow']};">
<div style="background:{c['surface2']}; padding:10px 16px; display:flex; align-items:center; gap:8px; border-bottom:1px solid {c['border']};">
<div style="width:10px; height:10px; border-radius:50%; background:#ef4444;"></div>
<div style="width:10px; height:10px; border-radius:50%; background:#f59e0b;"></div>
<div style="width:10px; height:10px; border-radius:50%; background:#10b981;"></div>
<div style="flex:1; text-align:center;"><span style="background:{c['bg']}; padding:4px 24px; border-radius:6px; font-size:0.75rem; color:{c['text_secondary']}; font-family:JetBrains Mono,monospace;">incidentmind/dashboard</span></div>
</div>
<div style="padding:24px; display:grid; grid-template-columns:repeat(4,1fr); gap:16px;">
<div style="background:{c['bg']}; border-radius:8px; padding:16px; text-align:center;"><div style="font-size:1.8rem; font-weight:800; color:{c['accent']}; font-family:JetBrains Mono,monospace;">4</div><div style="font-size:0.7rem; color:{c['text_secondary']}; text-transform:uppercase;">Active Agents</div></div>
<div style="background:{c['bg']}; border-radius:8px; padding:16px; text-align:center;"><div style="font-size:1.8rem; font-weight:800; color:{c['accent']}; font-family:JetBrains Mono,monospace;">12</div><div style="font-size:0.7rem; color:{c['text_secondary']}; text-transform:uppercase;">Incidents Today</div></div>
<div style="background:{c['bg']}; border-radius:8px; padding:16px; text-align:center;"><div style="font-size:1.8rem; font-weight:800; color:{c['accent']}; font-family:JetBrains Mono,monospace;">8m</div><div style="font-size:0.7rem; color:{c['text_secondary']}; text-transform:uppercase;">Avg MTTR</div></div>
<div style="background:{c['bg']}; border-radius:8px; padding:16px; text-align:center;"><div style="font-size:1.8rem; font-weight:800; color:{c['accent']}; font-family:JetBrains Mono,monospace;">99.9%</div><div style="font-size:0.7rem; color:{c['text_secondary']}; text-transform:uppercase;">Uptime</div></div>
</div>
</div>""", unsafe_allow_html=True)

    # SECTION 3: Features / How it Works
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(f"""<div style="text-align:center; padding:40px 20px;">
<h2 style="font-size:2.2rem; font-weight:800; color:{c['text']}; letter-spacing:-1px; margin-bottom:12px;">How it works</h2>
<p style="font-size:1rem; color:{c['text_secondary']}; max-width:500px; margin:0 auto 32px auto;">Four specialized agents collaborate through shared persistent memory in CockroachDB</p>
</div>
<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:16px; max-width:900px; margin:0 auto; padding:0 20px;">
<div style="background:{c['surface']}; border:1px solid {c['border']}; border-radius:12px; padding:24px; text-align:center;">
<div style="font-size:1.5rem; font-weight:800; color:{c['accent']}; margin-bottom:12px;">1</div>
<div style="font-size:0.95rem; font-weight:700; color:{c['text']}; margin-bottom:6px;">Triage</div>
<div style="font-size:0.8rem; color:{c['text_secondary']}; line-height:1.5;">Classifies severity, matches known patterns instantly</div>
</div>
<div style="background:{c['surface']}; border:1px solid {c['border']}; border-radius:12px; padding:24px; text-align:center;">
<div style="font-size:1.5rem; font-weight:800; color:{c['accent']}; margin-bottom:12px;">2</div>
<div style="font-size:0.95rem; font-weight:700; color:{c['text']}; margin-bottom:6px;">Diagnosis</div>
<div style="font-size:0.8rem; color:{c['text_secondary']}; line-height:1.5;">Semantic search over past incidents via vector embeddings</div>
</div>
<div style="background:{c['surface']}; border:1px solid {c['border']}; border-radius:12px; padding:24px; text-align:center;">
<div style="font-size:1.5rem; font-weight:800; color:{c['accent']}; margin-bottom:12px;">3</div>
<div style="font-size:0.95rem; font-weight:700; color:{c['text']}; margin-bottom:6px;">Correlate</div>
<div style="font-size:0.8rem; color:{c['text_secondary']}; line-height:1.5;">Finds recurring failure patterns, builds knowledge over time</div>
</div>
<div style="background:{c['surface']}; border:1px solid {c['border']}; border-radius:12px; padding:24px; text-align:center;">
<div style="font-size:1.5rem; font-weight:800; color:{c['accent']}; margin-bottom:12px;">4</div>
<div style="font-size:0.95rem; font-weight:700; color:{c['text']}; margin-bottom:6px;">Resolve</div>
<div style="font-size:0.8rem; color:{c['text_secondary']}; line-height:1.5;">Suggests fixes ranked by past success rates</div>
</div>
</div>""", unsafe_allow_html=True)

    # SECTION 4: Architecture
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(f"""<div style="text-align:center; padding:40px 20px;">
<h2 style="font-size:2.2rem; font-weight:800; color:{c['text']}; letter-spacing:-1px; margin-bottom:12px;">Architecture</h2>
<p style="font-size:1rem; color:{c['text_secondary']}; max-width:500px; margin:0 auto 32px auto;">Production-grade infrastructure for agentic memory</p>
</div>
<div style="max-width:700px; margin:0 auto; background:{c['surface']}; border:1px solid {c['border']}; border-radius:12px; padding:32px; font-family:JetBrains Mono,monospace; font-size:0.75rem; color:{c['text_secondary']}; line-height:2;">
<div style="text-align:center; color:{c['text']}; font-weight:600; margin-bottom:16px;">Event Sources (CloudWatch, PagerDuty, Slack)</div>
<div style="text-align:center; color:{c['accent']};">|</div>
<div style="text-align:center; color:{c['accent']};">v</div>
<div style="text-align:center; color:{c['text']}; font-weight:600;">AWS Lambda (Event Ingestion)</div>
<div style="text-align:center; color:{c['accent']};">|</div>
<div style="text-align:center; color:{c['accent']};">v</div>
<div style="text-align:center; color:{c['text']}; font-weight:600;">Agent Orchestrator (ECS)</div>
<div style="text-align:center; color:{c['text_secondary']};">[TriageAgent] [DiagnosisAgent] [CorrelatorAgent] [ResolutionAgent]</div>
<div style="text-align:center; color:{c['accent']};">|</div>
<div style="text-align:center; color:{c['accent']};">v</div>
<div style="text-align:center; color:{c['accent']}; font-weight:700; font-size:0.85rem;">CockroachDB Cloud (Shared Agentic Memory)</div>
<div style="text-align:center; color:{c['text_secondary']};">Agent State | Incident History | Vector Embeddings | Patterns</div>
<div style="text-align:center; color:{c['accent']}; margin-top:8px;">^</div>
<div style="text-align:center; color:{c['accent']};">| MCP Server</div>
<div style="text-align:center; color:{c['text']}; font-weight:600;">Claude / Cursor (Human Operator)</div>
</div>""", unsafe_allow_html=True)

    # SECTION 5: Tech Stack
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(f"""<div style="text-align:center; padding:20px 20px;">
<h2 style="font-size:2.2rem; font-weight:800; color:{c['text']}; letter-spacing:-1px; margin-bottom:32px;">Built with</h2>
</div>
<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:12px; max-width:700px; margin:0 auto; padding:0 20px;">
<div style="background:{c['surface']}; border:1px solid {c['border']}; border-radius:10px; padding:14px 18px; font-size:0.85rem; font-weight:500; color:{c['text']};">CockroachDB Cloud</div>
<div style="background:{c['surface']}; border:1px solid {c['border']}; border-radius:10px; padding:14px 18px; font-size:0.85rem; font-weight:500; color:{c['text']};">MCP Server</div>
<div style="background:{c['surface']}; border:1px solid {c['border']}; border-radius:10px; padding:14px 18px; font-size:0.85rem; font-weight:500; color:{c['text']};">Vector Indexing</div>
<div style="background:{c['surface']}; border:1px solid {c['border']}; border-radius:10px; padding:14px 18px; font-size:0.85rem; font-weight:500; color:{c['text']};">Amazon Bedrock</div>
<div style="background:{c['surface']}; border:1px solid {c['border']}; border-radius:10px; padding:14px 18px; font-size:0.85rem; font-weight:500; color:{c['text']};">AWS Lambda</div>
<div style="background:{c['surface']}; border:1px solid {c['border']}; border-radius:10px; padding:14px 18px; font-size:0.85rem; font-weight:500; color:{c['text']};">Amazon ECS</div>
<div style="background:{c['surface']}; border:1px solid {c['border']}; border-radius:10px; padding:14px 18px; font-size:0.85rem; font-weight:500; color:{c['text']};">LangChain</div>
<div style="background:{c['surface']}; border:1px solid {c['border']}; border-radius:10px; padding:14px 18px; font-size:0.85rem; font-weight:500; color:{c['text']};">Python</div>
<div style="background:{c['surface']}; border:1px solid {c['border']}; border-radius:10px; padding:14px 18px; font-size:0.85rem; font-weight:500; color:{c['text']};">Amazon S3</div>
</div>""", unsafe_allow_html=True)

    # Footer
    st.markdown(f"""<div style="text-align:center; margin-top:48px; padding:24px; border-top:1px solid {c['border']}; font-size:0.8rem; color:{c['text_secondary']};">
Built with CockroachDB + AWS Bedrock + LangChain | <span style="font-family:JetBrains Mono,monospace; font-size:0.7rem;">CockroachDB x AWS Hackathon 2024</span>
</div>""", unsafe_allow_html=True)


#  Sign In Page (separate page) 

def render_signin_page():
    c = get_colors()

    # Top bar with back button
    col1, col2, col3 = st.columns([1, 4, 1])
    with col1:
        if st.button("Back", key="signin_back"):
            st.session_state.current_page = "home"
            st.rerun()
    with col2:
        st.markdown(f'<div style="text-align:center; font-size:1.1rem; font-weight:800; color:{c["text"]}; padding:8px 0;">IncidentMind</div>', unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Sign in card
    st.markdown(f"""<div style="text-align:center; margin-bottom:24px;">
<h2 style="font-size:1.8rem; font-weight:800; color:{c['text']};">Sign in to IncidentMind</h2>
<p style="font-size:0.9rem; color:{c['text_secondary']};">Choose your preferred sign-in method</p>
</div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.3, 1, 1.3])
    with col2:
        # Google
        if st.button("Continue with Google", use_container_width=True, key="btn_google"):
            st.session_state.logged_in = True
            st.session_state.user_name = "Google User"
            st.session_state.user_email = "user@gmail.com"
            st.session_state.user_role = "Admin"
            st.session_state.current_page = "home"
            st.rerun()

        # GitHub
        if st.button("Continue with GitHub", use_container_width=True, key="btn_github"):
            st.session_state.logged_in = True
            st.session_state.user_name = "GitHub User"
            st.session_state.user_email = "user@github.com"
            st.session_state.user_role = "Admin"
            st.session_state.current_page = "home"
            st.rerun()

        st.markdown(f'<div style="text-align:center; font-size:0.8rem; color:{c["text_secondary"]}; margin:16px 0; padding:8px 0; border-top:1px solid {c["border"]}; border-bottom:1px solid {c["border"]};">or sign in with email</div>', unsafe_allow_html=True)

        # Email
        email = st.text_input("Email", placeholder="you@company.com", key="si_email", label_visibility="collapsed")
        password = st.text_input("Password", type="password", placeholder="Password", key="si_pass", label_visibility="collapsed")
        phone = st.text_input("Mobile (optional)", placeholder="+91 9876543210", key="si_phone", label_visibility="collapsed")

        if st.button("Sign In", type="primary", use_container_width=True, key="btn_email_signin"):
            name = email.split("@")[0].replace(".", " ").title() if email else "User"
            st.session_state.logged_in = True
            st.session_state.user_email = email or "demo@incidentmind.ai"
            st.session_state.user_name = name
            st.session_state.user_role = "Admin"
            st.session_state.current_page = "home"
            st.rerun()

        st.markdown(f'<div style="text-align:center; font-size:0.75rem; color:{c["text_secondary"]}; margin-top:16px;">Demo mode: any email works, no password needed</div>', unsafe_allow_html=True)


#  Sidebar Navigation (matching professional grouped style) 

def render_sidebar():
    c = get_colors()
    with st.sidebar:
        # Back link + Logo
        st.markdown(f"""
        <div style="padding:12px 8px 8px 8px;">
            <a href="#" style="font-size:0.8rem; color:{c['accent']}; text-decoration:none; display:flex; align-items:center; gap:6px;">
                <span style="font-size:0.7rem;">&#8592;</span> Back to Hub
            </a>
        </div>
        <div style="display:flex; align-items:center; gap:12px; padding:8px 12px 20px 12px; border-bottom:1px solid {c['border']}; margin-bottom:16px;">
            <div style="width:36px; height:36px; background:linear-gradient(135deg, {c['accent']}, #06b6d4); border-radius:8px; display:flex; align-items:center; justify-content:center;">
                <span style="color:white; font-weight:800; font-size:14px;">IM</span>
            </div>
            <div>
                <div style="font-size:0.95rem; font-weight:700; color:{c['text']};">INCIDENTMIND</div>
                <div style="font-size:0.7rem; color:{c['text_secondary']}; text-transform:uppercase; letter-spacing:0.5px;">{st.session_state.user_role}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Theme toggle
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Dark", use_container_width=True, key="btn_dark"):
                st.session_state.theme = "dark"
                st.rerun()
        with col2:
            if st.button("Light", use_container_width=True, key="btn_light"):
                st.session_state.theme = "light"
                st.rerun()

        # SECTION: INCIDENT OPS
        st.markdown(f"""
        <div style="padding:20px 12px 6px 12px; font-size:0.7rem; font-weight:600; color:{c['text_secondary']}; text-transform:uppercase; letter-spacing:1px;">
            Incident Operations
        </div>
        """, unsafe_allow_html=True)

        incident_ops = [
            ("home", "Overview"),
            ("incidents", "Live Incidents"),
            ("agent_feed", "Agent Feed"),
            ("heatmap", "Incident Heatmap"),
            ("dedup", "Deduplication"),
            ("predictions", "Predictive Alerts"),
        ]
        for key, label in incident_ops:
            is_active = st.session_state.current_page == key
            if st.button(
                f"{'  > ' if is_active else '    '}{label}{'  *' if is_active else ''}",
                key=f"nav_{key}",
                use_container_width=True,
            ):
                st.session_state.current_page = key
                st.rerun()

        # SECTION: AGENT TOOLS
        st.markdown(f"""
        <div style="padding:20px 12px 6px 12px; font-size:0.7rem; font-weight:600; color:{c['text_secondary']}; text-transform:uppercase; letter-spacing:1px;">
            Agent Tools
        </div>
        """, unsafe_allow_html=True)

        agent_tools = [
            ("mcp_query", "MCP Query Panel"),
            ("multi_chat", "Multi-Agent Chat"),
            ("runbook", "Runbook Dry Run"),
            ("playbooks", "Playbook Library"),
            ("knowledge_graph", "Knowledge Graph"),
            ("calibration", "Confidence Calibration"),
        ]
        for key, label in agent_tools:
            is_active = st.session_state.current_page == key
            if st.button(
                f"{'  > ' if is_active else '    '}{label}{'  *' if is_active else ''}",
                key=f"nav_{key}",
                use_container_width=True,
            ):
                st.session_state.current_page = key
                st.rerun()

        # SECTION: INFRASTRUCTURE
        st.markdown(f"""
        <div style="padding:20px 12px 6px 12px; font-size:0.7rem; font-weight:600; color:{c['text_secondary']}; text-transform:uppercase; letter-spacing:1px;">
            Infrastructure
        </div>
        """, unsafe_allow_html=True)

        infra_pages = [
            ("health", "Health Dashboard"),
            ("regions", "Multi-Region"),
            ("rate_limit", "Rate Limiting"),
            ("rbac", "RBAC & Access"),
            ("audit", "Audit Log"),
        ]
        for key, label in infra_pages:
            is_active = st.session_state.current_page == key
            if st.button(
                f"{'  > ' if is_active else '    '}{label}{'  *' if is_active else ''}",
                key=f"nav_{key}",
                use_container_width=True,
            ):
                st.session_state.current_page = key
                st.rerun()

        # SECTION: ANALYTICS
        st.markdown(f"""
        <div style="padding:20px 12px 6px 12px; font-size:0.7rem; font-weight:600; color:{c['text_secondary']}; text-transform:uppercase; letter-spacing:1px;">
            Analytics & Reports
        </div>
        """, unsafe_allow_html=True)

        analytics_pages = [
            ("performance", "Agent Performance"),
            ("mttr", "MTTR Dashboard"),
            ("categories", "Failure Categories"),
            ("roi", "ROI Calculator"),
            ("export", "Export & Share"),
        ]
        for key, label in analytics_pages:
            is_active = st.session_state.current_page == key
            if st.button(
                f"{'  > ' if is_active else '    '}{label}{'  *' if is_active else ''}",
                key=f"nav_{key}",
                use_container_width=True,
            ):
                st.session_state.current_page = key
                st.rerun()

        # USER PROFILE (at bottom, like the screenshot)
        st.markdown(f"""
        <div style="margin-top:32px; padding-top:16px; border-top:1px solid {c['border']};">
            <div style="display:flex; align-items:center; gap:10px; padding:8px 12px;">
                <div style="width:32px; height:32px; background:{c['accent']}; border-radius:50%; display:flex; align-items:center; justify-content:center;">
                    <span style="color:white; font-weight:700; font-size:13px;">{st.session_state.user_name[0].upper() if st.session_state.user_name else 'U'}</span>
                </div>
                <div>
                    <div style="font-size:0.85rem; font-weight:600; color:{c['text']};">{st.session_state.user_name}</div>
                    <div style="font-size:0.7rem; color:{c['text_secondary']};">{st.session_state.user_role.lower()}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Sign Out", key="nav_signout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_page = "home"
            st.rerun()

        # Region indicator
        st.markdown(f"""
        <div style="margin-top:12px; padding:10px 12px; background:{c['surface2']}; border-radius:8px; font-size:0.75rem;">
            <div style="color:{c['text_secondary']};">Active Region</div>
            <div style="color:{c['accent']}; font-family:'JetBrains Mono',monospace; font-weight:600; margin-top:2px;">{st.session_state.region}</div>
        </div>
        """, unsafe_allow_html=True)

        if DEMO_MODE:
            st.markdown(f"""
            <div style="margin-top:8px; padding:6px 12px; background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); border-radius:6px; text-align:center;">
                <span style="color:#f59e0b; font-size:0.75rem; font-weight:600;">DEMO MODE</span>
            </div>
            """, unsafe_allow_html=True)


# Render login or main app
if not st.session_state.logged_in:
    # Hide sidebar on login page
    st.markdown("""
    <style>
        section[data-testid="stSidebar"] {display: none;}
        .stApp > header {display: none;}
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.current_page == "signin":
        render_signin_page()
    else:
        render_landing_page()
    st.stop()

render_sidebar()


#  Helper Rendering Functions 

def render_metric_card(label, value, icon="", delta=None):
    c = get_colors()
    delta_html = ""
    if delta:
        delta_color = c['accent'] if delta.startswith("+") or delta.startswith("↓") else c['danger']
        delta_html = f'<div style="font-size:0.8rem; color:{delta_color}; margin-top:4px;">{delta}</div>'
    return f"""
    <div class="metric-card">
        <div style="font-size:1.5rem; margin-bottom:8px;">{icon}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        {delta_html}
    </div>
    """


def render_severity_badge(severity):
    return f'<span class="badge badge-{severity}">{severity}</span>'


def render_progress_bar(value, max_val=100):
    pct = min((value / max_val) * 100, 100)
    return f"""
    <div class="progress-bar">
        <div class="progress-fill" style="width: {pct}%;"></div>
    </div>
    """



# 
# PAGE: HOME (Hero Landing)
# 

def page_home():
    c = get_colors()

    # Hero Section
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-badge">
            <span> Powered by</span>
            <span class="hero-badge-highlight">CockroachDB + AWS Bedrock</span>
        </div>
        <h1 class="hero-title">
            Multi-Agent<br><span class="gradient">Incident Response</span>
        </h1>
        <p class="hero-subtitle">
            AI agents that autonomously triage, diagnose, and resolve production incidents
            using distributed memory and vector search.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Key Stats
    total_incidents = len(st.session_state.incidents)
    resolved = len([i for i in st.session_state.incidents if i["status"] == "resolved"])
    avg_confidence = np.mean([i["confidence"] for i in st.session_state.incidents]) if st.session_state.incidents else 0
    avg_mttr = np.mean([i["mttr_minutes"] for i in st.session_state.incidents]) if st.session_state.incidents else 0

    cols = st.columns(4)
    metrics = [
        ("Total Incidents", str(total_incidents), "", "+3 today"),
        ("Resolved", str(resolved), "", f"{int(resolved/max(total_incidents,1)*100)}% rate"),
        ("Avg Confidence", f"{avg_confidence:.0%}", "", "+2% this week"),
        ("Avg MTTR", f"{avg_mttr:.0f}m", "⏱", "↓12% improvement"),
    ]
    for col, (label, value, icon, delta) in zip(cols, metrics):
        with col:
            st.markdown(render_metric_card(label, value, icon, delta), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Architecture Overview
    st.markdown(f'<div class="section-header"> Architecture Pipeline</div>', unsafe_allow_html=True)

    # Pipeline visualization
    st.markdown(f"""
    <div class="timeline-container">
        <div class="timeline-step">
            <div class="timeline-dot active"></div>
            <div class="timeline-label">Ingest</div>
        </div>
        <div class="timeline-connector done"></div>
        <div class="timeline-step">
            <div class="timeline-dot active"></div>
            <div class="timeline-label">Triage</div>
        </div>
        <div class="timeline-connector done"></div>
        <div class="timeline-step">
            <div class="timeline-dot active"></div>
            <div class="timeline-label">Diagnose</div>
        </div>
        <div class="timeline-connector done"></div>
        <div class="timeline-step">
            <div class="timeline-dot active"></div>
            <div class="timeline-label">Correlate</div>
        </div>
        <div class="timeline-connector done"></div>
        <div class="timeline-step">
            <div class="timeline-dot active"></div>
            <div class="timeline-label">Resolve</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Technology Stack
    st.markdown(f'<div class="section-header"> Technology Stack</div>', unsafe_allow_html=True)
    tech_cols = st.columns(4)
    techs = [
        (" CockroachDB", "Distributed SQL + Vector indexing for incident memory"),
        (" AWS Bedrock", "Claude & Titan models for agent reasoning & embeddings"),
        (" LangChain", "Agent framework with tool-calling & chain-of-thought"),
        (" MCP Protocol", "Model Context Protocol for live system querying"),
    ]
    for col, (title, desc) in zip(tech_cols, techs):
        with col:
            st.markdown(f"""
            <div class="metric-card" style="text-align:center; min-height: 160px;">
                <div style="font-size:2rem; margin-bottom:12px;">{title.split(' ')[0]}</div>
                <div style="font-weight:700; color:{c['text']}; margin-bottom:8px;">{title.split(' ', 1)[1]}</div>
                <div style="font-size:0.8rem; color:{c['text_secondary']};">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    # Live demo simulation button
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(" Simulate New Incident", use_container_width=True, key="sim_btn"):
            new_incident = generate_incident()
            st.session_state.incidents.insert(0, new_incident)
            st.session_state.agent_feed.insert(0, {
                "timestamp": datetime.now(timezone.utc),
                "agent": "TriageAgent",
                "action": f"New incident detected: {new_incident['title']}",
                "incident_id": new_incident["id"],
                "duration_ms": random.randint(100, 500),
            })
            st.session_state.audit_log.insert(0, {
                "ts": datetime.now(timezone.utc),
                "user": "system",
                "action": "incident_created",
                "target": new_incident["id"],
            })
            st.rerun()


# 
# PAGE: LIVE INCIDENTS
# 

def page_incidents():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Live Incident Feed</div>', unsafe_allow_html=True)

    # Controls
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        search = st.text_input(" Search incidents...", key="inc_search", placeholder="service name, keyword...")
    with col2:
        sev_filter = st.selectbox("Severity", ["All", "critical", "high", "medium", "warning"], key="sev_filter")
    with col3:
        status_filter = st.selectbox("Status", ["All", "open", "triaging", "diagnosing", "resolving", "resolved"], key="status_filter")
    with col4:
        if st.button(" New Incident", key="new_inc"):
            new_inc = generate_incident()
            st.session_state.incidents.insert(0, new_inc)
            st.rerun()

    # Filter
    filtered = st.session_state.incidents
    if search:
        filtered = [i for i in filtered if search.lower() in i["title"].lower() or search.lower() in i["service"].lower()]
    if sev_filter != "All":
        filtered = [i for i in filtered if i["severity"] == sev_filter]
    if status_filter != "All":
        filtered = [i for i in filtered if i["status"] == status_filter]

    # Incident table
    if filtered:
        table_html = f"""
        <table class="styled-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Title</th>
                    <th>Service</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Agent</th>
                    <th>Confidence</th>
                    <th>MTTR</th>
                </tr>
            </thead>
            <tbody>
        """
        for inc in filtered[:20]:
            status_colors = {"open": c['danger'], "triaging": c['warning'], "diagnosing": c['info'], "resolving": c['accent'], "resolved": c['text_secondary']}
            status_color = status_colors.get(inc["status"], c['text'])
            table_html += f"""
                <tr>
                    <td><code style="color:{c['accent']}; font-family:'JetBrains Mono',monospace; font-size:0.8rem;">{inc['id']}</code></td>
                    <td style="font-weight:500;">{inc['title']}</td>
                    <td><code style="font-size:0.8rem;">{inc['service']}</code></td>
                    <td>{render_severity_badge(inc['severity'])}</td>
                    <td><span style="color:{status_color}; font-weight:600;"> {inc['status']}</span></td>
                    <td style="font-family:'JetBrains Mono',monospace; font-size:0.8rem;">{inc['assigned_agent']}</td>
                    <td><span style="color:{c['accent']}; font-weight:600;">{inc['confidence']:.0%}</span></td>
                    <td>{inc['mttr_minutes']}m</td>
                </tr>
            """
        table_html += "</tbody></table>"
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("No incidents match your filters.")

    # Incident Timeline for selected incident
    st.markdown(f'<br><div class="section-header"> Incident Pipeline View</div>', unsafe_allow_html=True)
    if filtered:
        selected = filtered[0]
        stages = ["open", "triaging", "diagnosing", "resolving", "resolved"]
        current_idx = stages.index(selected["status"]) if selected["status"] in stages else 0
        icons = ["", "", "", "", ""]
        labels = ["Open", "Triage", "Diagnosis", "Resolution", "Resolved"]

        timeline_html = '<div class="timeline-container">'
        for i, (icon, label) in enumerate(zip(icons, labels)):
            dot_class = "done" if i < current_idx else ("active" if i == current_idx else "pending")
            timeline_html += f"""
            <div class="timeline-step">
                <div class="timeline-dot {dot_class}">{icon}</div>
                <div class="timeline-label">{label}</div>
            </div>
            """
            if i < len(icons) - 1:
                conn_class = "done" if i < current_idx else ""
                timeline_html += f'<div class="timeline-connector {conn_class}"></div>'
        timeline_html += '</div>'
        st.markdown(timeline_html, unsafe_allow_html=True)
        st.caption(f"Showing pipeline for: **{selected['id']}** - {selected['title']}")



# 
# PAGE: AGENT ACTIVITY FEED
# 

def page_agent_feed():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Real-Time Agent Activity</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button(" Refresh Feed", key="refresh_feed"):
            for _ in range(3):
                st.session_state.agent_feed.insert(0, generate_agent_action())
            st.rerun()

    # Agent filter
    agent_filter = st.multiselect("Filter by Agent", AGENT_NAMES, default=AGENT_NAMES, key="agent_filter_feed")

    feed = [f for f in st.session_state.agent_feed if f["agent"] in agent_filter]

    for item in feed[:25]:
        agent_colors = {
            "TriageAgent": "#10b981",
            "DiagnosisAgent": "#3b82f6",
            "ResolutionAgent": "#f59e0b",
            "CorrelatorAgent": "#a855f7",
        }
        agent_color = agent_colors.get(item["agent"], c['accent'])
        time_str = item["timestamp"].strftime("%H:%M:%S")
        st.markdown(f"""
        <div class="feed-item" style="border-left-color: {agent_color};">
            <div style="min-width: 60px;">
                <div class="feed-time">{time_str}</div>
            </div>
            <div style="flex:1;">
                <div class="feed-agent" style="color:{agent_color};">{item['agent']}</div>
                <div class="feed-action">{item['action']}</div>
                <div style="font-size:0.75rem; color:{c['text_secondary']}; margin-top:4px;">
                    {item['incident_id']} · {item['duration_ms']}ms
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# 
# PAGE: KNOWLEDGE GRAPH
# 

def page_knowledge_graph():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Incident Knowledge Graph</div>', unsafe_allow_html=True)
    st.caption("Visual connections between related incidents, services, and root causes.")

    # Generate graph data
    services = list(set(i["service"] for i in st.session_state.incidents))[:8]
    incidents = st.session_state.incidents[:6]

    # SVG-based knowledge graph
    svg_width = 800
    svg_height = 500
    center_x, center_y = svg_width // 2, svg_height // 2

    svg_elements = []

    # Draw service nodes in a circle
    service_positions = []
    for i, svc in enumerate(services):
        angle = (2 * math.pi * i) / len(services)
        x = center_x + int(180 * math.cos(angle))
        y = center_y + int(180 * math.sin(angle))
        service_positions.append((x, y, svc))

    # Draw incident nodes in inner circle
    incident_positions = []
    for i, inc in enumerate(incidents):
        angle = (2 * math.pi * i) / len(incidents) + 0.3
        x = center_x + int(90 * math.cos(angle))
        y = center_y + int(90 * math.sin(angle))
        incident_positions.append((x, y, inc))

    # Draw connections
    for ix, iy, inc in incident_positions:
        for sx, sy, svc in service_positions:
            if inc["service"] == svc:
                svg_elements.append(f'<line x1="{ix}" y1="{iy}" x2="{sx}" y2="{sy}" stroke="{c["accent"]}" stroke-width="1.5" opacity="0.4"/>')

    # Draw random correlations between incidents
    for i in range(len(incident_positions) - 1):
        if random.random() > 0.5:
            x1, y1, _ = incident_positions[i]
            x2, y2, _ = incident_positions[i + 1]
            svg_elements.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c["warning"]}" stroke-width="1" opacity="0.3" stroke-dasharray="4,4"/>')

    # Draw service nodes
    for x, y, svc in service_positions:
        svg_elements.append(f'<circle cx="{x}" cy="{y}" r="28" fill="{c["surface2"]}" stroke="{c["accent"]}" stroke-width="2"/>')
        # Truncate service name
        short_name = svc[:10]
        svg_elements.append(f'<text x="{x}" y="{y+4}" text-anchor="middle" fill="{c["text"]}" font-size="9" font-family="Inter">{short_name}</text>')

    # Draw incident nodes
    sev_colors = {"critical": "#ef4444", "high": "#f59e0b", "medium": "#3b82f6", "warning": "#a855f7"}
    for x, y, inc in incident_positions:
        node_color = sev_colors.get(inc["severity"], c["accent"])
        svg_elements.append(f'<circle cx="{x}" cy="{y}" r="20" fill="{node_color}" opacity="0.8"/>')
        svg_elements.append(f'<text x="{x}" y="{y+4}" text-anchor="middle" fill="white" font-size="8" font-weight="bold" font-family="JetBrains Mono">{inc["id"][-6:]}</text>')

    # Central orchestrator node
    svg_elements.append(f'<circle cx="{center_x}" cy="{center_y}" r="24" fill="{c["accent"]}" opacity="0.9"/>')
    svg_elements.append(f'<text x="{center_x}" y="{center_y+4}" text-anchor="middle" fill="white" font-size="10" font-weight="bold"></text>')

    svg_html = f"""
    <div style="text-align:center; padding: 20px; background:{c['surface']}; border-radius:12px; border:1px solid {c['border']};">
        <svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">
            {''.join(svg_elements)}
        </svg>
        <div style="margin-top:12px; font-size:0.8rem; color:{c['text_secondary']};">
            <span style="color:#ef4444;"></span> Critical &nbsp;
            <span style="color:#f59e0b;"></span> High &nbsp;
            <span style="color:#3b82f6;"></span> Medium &nbsp;
            <span style="color:{c['accent']};"></span> Services &nbsp;
            <span style="color:{c['warning']};">- -</span> Correlated
        </div>
    </div>
    """
    st.markdown(svg_html, unsafe_allow_html=True)

    # Stats
    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns(3)
    with cols[0]:
        st.markdown(render_metric_card("Connected Services", str(len(services)), ""), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(render_metric_card("Correlated Incidents", str(random.randint(4, 8)), ""), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(render_metric_card("Root Causes Found", str(random.randint(2, 5)), ""), unsafe_allow_html=True)


# 
# PAGE: MCP SERVER LIVE QUERY PANEL
# 

def page_mcp_query():
    c = get_colors()
    st.markdown(f'<div class="section-header"> MCP Server - Natural Language Query</div>', unsafe_allow_html=True)
    st.caption("Query your incident data using natural language via the Model Context Protocol.")

    # Chat interface
    chat_container = st.container()

    # Display chat history
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f"""
                <div style="display:flex; justify-content:flex-end; margin:8px 0;">
                    <div class="chat-bubble chat-user">{msg['content']}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="display:flex; justify-content:flex-start; margin:8px 0;">
                    <div class="chat-bubble chat-agent"> {msg['content']}</div>
                </div>
                """, unsafe_allow_html=True)

    # Input
    query = st.text_input("Ask about your incidents...", key="mcp_input",
                          placeholder="e.g., Show me all critical incidents from payment-service")

    if query:
        st.session_state.chat_history.append({"role": "user", "content": query})

        # Mock responses based on keywords
        response = _generate_mcp_response(query)
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()

    # Suggested queries
    st.markdown(f"<br><div style='color:{c['text_secondary']}; font-size:0.85rem; font-weight:600;'> Try these queries:</div>", unsafe_allow_html=True)
    suggestions = [
        "What are the most common incident types this week?",
        "Show me unresolved critical incidents",
        "Which service has the highest failure rate?",
        "What's the average MTTR for database incidents?",
        "Find incidents correlated with the payment-service outage",
    ]
    for s in suggestions:
        if st.button(f"→ {s}", key=f"suggest_{hash(s)}"):
            st.session_state.chat_history.append({"role": "user", "content": s})
            st.session_state.chat_history.append({"role": "assistant", "content": _generate_mcp_response(s)})
            st.rerun()


def _generate_mcp_response(query: str) -> str:
    """Generate mock MCP response based on query keywords."""
    q = query.lower()
    if "critical" in q:
        critical = [i for i in st.session_state.incidents if i["severity"] == "critical"]
        return f"Found **{len(critical)} critical incidents**. Top ones: {', '.join(i['id'] for i in critical[:3])}. Services affected: {', '.join(set(i['service'] for i in critical[:3]))}."
    elif "common" in q or "types" in q:
        return "Top incident types this week: **Database issues (34%)**, API latency (28%), Memory issues (18%), Certificate expiry (12%), Other (8%). Recommend focusing on DB connection pooling optimization."
    elif "mttr" in q or "time" in q:
        avg = np.mean([i["mttr_minutes"] for i in st.session_state.incidents])
        return f"Average MTTR across all incidents: **{avg:.1f} minutes**. Database incidents average 12.3min, API issues average 8.7min. MTTR has improved 15% this month."
    elif "service" in q or "failure" in q:
        services = [i["service"] for i in st.session_state.incidents]
        from collections import Counter
        top = Counter(services).most_common(3)
        return f"Highest failure services: **{top[0][0]}** ({top[0][1]} incidents), {top[1][0]} ({top[1][1]}), {top[2][0]} ({top[2][1]}). Recommending increased monitoring on {top[0][0]}."
    elif "correlated" in q or "related" in q:
        return "Found **3 correlated incidents** in the last 24h linked to payment-service: INC-A3F2 (DB pool), INC-B7C1 (latency), INC-D9E4 (timeout). Root cause: connection pool saturation cascading to dependent services."
    else:
        return f"Based on your query, I found {random.randint(3,8)} relevant incidents. The most common pattern involves service degradation during peak hours (14:00-16:00 UTC). Recommend pre-scaling and connection pool tuning."



# 
# PAGE: HEALTH DASHBOARD
# 

def page_health():
    c = get_colors()
    st.markdown(f'<div class="section-header"> System Health Dashboard</div>', unsafe_allow_html=True)

    # Overall status
    st.markdown(f"""
    <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); border-radius:12px; padding:16px 24px; display:flex; align-items:center; gap:12px; margin-bottom:24px;">
        <div style="font-size:1.5rem;"></div>
        <div>
            <div style="font-weight:700; color:{c['accent']};">All Systems Operational</div>
            <div style="font-size:0.8rem; color:{c['text_secondary']};">Last checked: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Agent heartbeats
    st.markdown(f"<div style='font-weight:700; color:{c['text']}; margin:16px 0 8px 0;'> Agent Heartbeats</div>", unsafe_allow_html=True)
    agent_health = [
        ("TriageAgent", "healthy", "23ms", "2.1k processed"),
        ("DiagnosisAgent", "healthy", "45ms", "1.8k processed"),
        ("ResolutionAgent", "healthy", "67ms", "1.2k processed"),
        ("CorrelatorAgent", "healthy", "34ms", "890 processed"),
    ]

    cols = st.columns(4)
    for col, (name, status, latency, processed) in zip(cols, agent_health):
        with col:
            status_icon = "" if status == "healthy" else ""
            st.markdown(f"""
            <div class="metric-card" style="text-align:center;">
                <div style="font-size:1.2rem;">{status_icon}</div>
                <div style="font-weight:700; color:{c['text']}; font-size:0.9rem; margin:8px 0;">{name}</div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:{c['accent']};">{latency}</div>
                <div style="font-size:0.75rem; color:{c['text_secondary']}; margin-top:4px;">{processed}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Database health
    st.markdown(f"<div style='font-weight:700; color:{c['text']}; margin:16px 0 8px 0;'> CockroachDB Cluster Health</div>", unsafe_allow_html=True)
    db_cols = st.columns(4)
    db_metrics = [
        ("Connections", "47/200", "", None),
        ("Query Latency (p99)", "12ms", "", "↓3ms"),
        ("Storage Used", "2.4 GB", "", None),
        ("Uptime", "99.97%", "", "+0.02%"),
    ]
    for col, (label, value, icon, delta) in zip(db_cols, db_metrics):
        with col:
            st.markdown(render_metric_card(label, value, icon, delta), unsafe_allow_html=True)

    # Connection pool visualization
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-weight:600; color:{c['text']}; margin-bottom:8px;'>Connection Pool Utilization</div>", unsafe_allow_html=True)
    st.markdown(render_progress_bar(47, 200), unsafe_allow_html=True)
    st.caption("47 of 200 connections in use (23.5%)")

    # Region latencies
    st.markdown(f"<div style='font-weight:600; color:{c['text']}; margin:16px 0 8px 0;'> Cross-Region Latencies</div>", unsafe_allow_html=True)
    latency_data = pd.DataFrame({
        "Route": ["us-east-1 → eu-west-1", "us-east-1 → ap-south-1", "eu-west-1 → ap-south-1"],
        "Latency": ["78ms", "195ms", "142ms"],
        "Status": [" Good", " Elevated", " Good"],
    })
    st.dataframe(latency_data, use_container_width=True, hide_index=True)


# 
# PAGE: AUDIT LOG
# 

def page_audit():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Audit Log</div>', unsafe_allow_html=True)
    st.caption("Every agent action and user interaction is recorded for compliance and debugging.")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        user_filter = st.selectbox("Filter by User", ["All", "admin@company.com", "sre-lead@company.com", "engineer@company.com", "system"], key="audit_user")
    with col2:
        action_filter = st.selectbox("Filter by Action", ["All", "viewed_incident", "approved_runbook", "escalated", "changed_severity", "exported_report", "incident_created"], key="audit_action")

    logs = st.session_state.audit_log
    if user_filter != "All":
        logs = [l for l in logs if l["user"] == user_filter]
    if action_filter != "All":
        logs = [l for l in logs if l["action"] == action_filter]

    # Render log table
    table_html = f"""
    <table class="styled-table">
        <thead><tr><th>Timestamp</th><th>User</th><th>Action</th><th>Target</th></tr></thead>
        <tbody>
    """
    for log in logs[:30]:
        action_icons = {"viewed_incident": "", "approved_runbook": "", "escalated": "", "changed_severity": "", "exported_report": "", "incident_created": ""}
        icon = action_icons.get(log["action"], "")
        table_html += f"""
        <tr>
            <td style="font-family:'JetBrains Mono',monospace; font-size:0.8rem;">{log['ts'].strftime('%Y-%m-%d %H:%M:%S')}</td>
            <td>{log['user']}</td>
            <td>{icon} {log['action']}</td>
            <td><code style="color:{c['accent']};">{log['target']}</code></td>
        </tr>
        """
    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)

    st.markdown(f"<div style='margin-top:16px; font-size:0.8rem; color:{c['text_secondary']};'>Showing {min(len(logs), 30)} of {len(logs)} entries</div>", unsafe_allow_html=True)


# 
# PAGE: RBAC & ACCESS CONTROL
# 

def page_rbac():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Role-Based Access Control</div>', unsafe_allow_html=True)
    st.caption("IncidentMind enforces least-privilege access across all operations.")

    # Role cards
    for role in RBAC_ROLES:
        perms_html = " ".join([f'<span style="background:rgba(16,185,129,0.1); color:{c["accent"]}; padding:3px 8px; border-radius:4px; font-size:0.75rem; margin:2px;">{p}</span>' for p in role["permissions"]])
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid {role['color']};">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-weight:700; color:{c['text']}; font-size:1.1rem;">{role['role']}</div>
                    <div style="margin-top:8px;">{perms_html}</div>
                </div>
                <div style="font-size:2rem; opacity:0.3;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Access matrix
    st.markdown(f'<br><div style="font-weight:700; color:{c["text"]};">Access Matrix</div>', unsafe_allow_html=True)
    matrix_data = {
        "Resource": ["Incidents", "Runbooks", "Agent Config", "Audit Logs", "System Settings"],
        "Admin": [" Full", " Full", " Full", " Full", " Full"],
        "SRE Lead": [" Full", " Execute", " View", " Full", " None"],
        "Engineer": [" R/W", " Execute", " None", " View", " None"],
        "Viewer": [" View", " View", " None", " None", " None"],
    }
    st.dataframe(pd.DataFrame(matrix_data), use_container_width=True, hide_index=True)


# 
# PAGE: MULTI-REGION
# 

def page_regions():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Multi-Region Architecture</div>', unsafe_allow_html=True)
    st.caption("CockroachDB's multi-region capabilities ensure data locality and low-latency access.")

    # Region cards
    cols = st.columns(3)
    for col, region in zip(cols, REGIONS):
        is_active = region["name"] == st.session_state.region
        border_color = c['accent'] if is_active else c['border']
        badge = f'<span style="background:{c["accent"]}; color:white; padding:2px 8px; border-radius:4px; font-size:0.7rem;">ACTIVE</span>' if is_active else ""
        with col:
            st.markdown(f"""
            <div class="metric-card" style="border-color:{border_color}; border-width:2px; text-align:center;">
                <div style="font-size:1.5rem; margin-bottom:8px;"></div>
                <div style="font-weight:700; color:{c['text']};">{region['label']}</div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:{c['text_secondary']}; margin:4px 0;">{region['name']}</div>
                {badge}
                <div style="margin-top:8px; font-size:0.8rem; color:{c['text_secondary']};">
                    Latency: {random.randint(2, 15)}ms
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Region switch demo
    st.markdown("<br>", unsafe_allow_html=True)
    new_region = st.selectbox("Switch Active Region", [r["name"] for r in REGIONS], index=[r["name"] for r in REGIONS].index(st.session_state.region), key="region_select")
    if new_region != st.session_state.region:
        st.session_state.region = new_region
        st.rerun()

    # Replication topology
    st.markdown(f"""
    <div class="metric-card" style="margin-top:16px;">
        <div style="font-weight:700; color:{c['text']}; margin-bottom:12px;"> Replication Topology</div>
        <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:{c['text_secondary']};">
            <br>
              us-east-1 (Primary) ←→ eu-west-1 (Read) <br>
                   ↕                         ↕           <br>
                       ap-south-1 (Read Replica)         <br>
            <br>
            <br>
            Replication Factor: 3  Survival Goal: Region  Lease Preference: {st.session_state.region}
        </div>
    </div>
    """, unsafe_allow_html=True)


# 
# PAGE: RATE LIMITING & CIRCUIT BREAKER
# 

def page_rate_limit():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Rate Limiting & Circuit Breakers</div>', unsafe_allow_html=True)

    # Rate limit status
    st.markdown(f"<div style='font-weight:700; color:{c['text']}; margin:16px 0 8px 0;'> API Rate Limits</div>", unsafe_allow_html=True)

    endpoints = [
        ("/api/v1/incidents", 847, 1000, "healthy"),
        ("/api/v1/query", 234, 500, "healthy"),
        ("/api/v1/runbook/execute", 12, 50, "healthy"),
        ("/api/v1/agents/status", 456, 500, "warning"),
        ("/api/v1/export", 8, 20, "healthy"),
    ]

    for endpoint, used, limit, status in endpoints:
        pct = used / limit * 100
        bar_color = c['accent'] if pct < 70 else (c['warning'] if pct < 90 else c['danger'])
        st.markdown(f"""
        <div style="padding:12px 16px; background:{c['surface']}; border-radius:8px; margin:8px 0; border:1px solid {c['border']};">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <code style="font-size:0.85rem; color:{c['text']};">{endpoint}</code>
                <span style="font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:{bar_color};">{used}/{limit} req/min</span>
            </div>
            <div style="background:{c['surface2']}; border-radius:4px; height:6px; overflow:hidden;">
                <div style="width:{pct}%; height:100%; background:{bar_color}; border-radius:4px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Circuit breakers
    st.markdown(f"<br><div style='font-weight:700; color:{c['text']}; margin:16px 0 8px 0;'> Circuit Breaker States</div>", unsafe_allow_html=True)

    breakers = [
        ("payment-service", "CLOSED", "Operating normally", c['accent']),
        ("auth-service", "CLOSED", "Operating normally", c['accent']),
        ("ml-inference", "HALF-OPEN", "Testing recovery (3/5 success)", c['warning']),
        ("legacy-api", "OPEN", "Tripped 2m ago - 5 consecutive failures", c['danger']),
    ]

    for service, state, desc, color in breakers:
        st.markdown(f"""
        <div class="metric-card" style="border-left:4px solid {color}; padding:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-weight:600; color:{c['text']};">{service}</div>
                    <div style="font-size:0.8rem; color:{c['text_secondary']}; margin-top:4px;">{desc}</div>
                </div>
                <div style="background:{color}20; color:{color}; padding:4px 12px; border-radius:6px; font-weight:700; font-size:0.8rem;">
                    {state}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)



# 
# PAGE: INCIDENT HEATMAP
# 

def page_heatmap():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Incident Heatmap</div>', unsafe_allow_html=True)
    st.caption("Visualize incident frequency by day and hour to identify patterns.")

    # Generate heatmap data (7 days x 24 hours)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hours = list(range(24))

    # Generate realistic data with peaks during business hours
    heatmap_data = []
    for d in range(7):
        row = []
        for h in range(24):
            base = random.randint(0, 2)
            # Peak during business hours on weekdays
            if d < 5 and 9 <= h <= 17:
                base += random.randint(2, 6)
            # Deployment windows
            if d < 5 and h in [14, 15]:
                base += random.randint(1, 4)
            row.append(base)
        heatmap_data.append(row)

    # Render heatmap as HTML
    max_val = max(max(row) for row in heatmap_data)

    heatmap_html = f"""
    <div style="background:{c['surface']}; border-radius:12px; padding:24px; border:1px solid {c['border']};">
        <div style="overflow-x:auto;">
            <table style="border-collapse:collapse; width:100%;">
                <tr>
                    <td style="width:40px;"></td>
    """
    # Hour headers
    for h in hours:
        heatmap_html += f'<td style="text-align:center; font-size:0.65rem; color:{c["text_secondary"]}; padding:2px;">{h:02d}</td>'
    heatmap_html += "</tr>"

    for d, day in enumerate(days):
        heatmap_html += f'<tr><td style="font-size:0.75rem; color:{c["text_secondary"]}; padding-right:8px; font-weight:600;">{day}</td>'
        for h in range(24):
            val = heatmap_data[d][h]
            intensity = val / max(max_val, 1)
            if intensity == 0:
                bg = c['surface2']
            elif intensity < 0.3:
                bg = "rgba(16,185,129,0.2)"
            elif intensity < 0.6:
                bg = "rgba(16,185,129,0.4)"
            elif intensity < 0.8:
                bg = "rgba(245,158,11,0.5)"
            else:
                bg = "rgba(239,68,68,0.6)"
            heatmap_html += f'<td style="padding:2px;"><div style="width:100%; height:20px; background:{bg}; border-radius:3px; min-width:14px;" title="{day} {h:02d}:00 - {val} incidents"></div></td>'
        heatmap_html += "</tr>"

    heatmap_html += f"""
            </table>
        </div>
        <div style="margin-top:16px; display:flex; align-items:center; gap:8px; justify-content:center;">
            <span style="font-size:0.75rem; color:{c['text_secondary']};">Less</span>
            <div style="width:14px; height:14px; background:{c['surface2']}; border-radius:3px;"></div>
            <div style="width:14px; height:14px; background:rgba(16,185,129,0.2); border-radius:3px;"></div>
            <div style="width:14px; height:14px; background:rgba(16,185,129,0.4); border-radius:3px;"></div>
            <div style="width:14px; height:14px; background:rgba(245,158,11,0.5); border-radius:3px;"></div>
            <div style="width:14px; height:14px; background:rgba(239,68,68,0.6); border-radius:3px;"></div>
            <span style="font-size:0.75rem; color:{c['text_secondary']};">More</span>
        </div>
    </div>
    """
    st.markdown(heatmap_html, unsafe_allow_html=True)

    # Insights
    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns(3)
    with cols[0]:
        st.markdown(render_metric_card("Peak Hour", "14:00-15:00", "", "Deployment window"), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(render_metric_card("Quietest Day", "Sunday", "", "82% fewer incidents"), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(render_metric_card("Weekly Total", str(sum(sum(row) for row in heatmap_data)), "", None), unsafe_allow_html=True)


# 
# PAGE: RESOLUTION PLAYBOOK LIBRARY
# 

def page_playbooks():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Resolution Playbook Library</div>', unsafe_allow_html=True)
    st.caption("Searchable library of automated resolution strategies learned from past incidents.")

    # Search
    search = st.text_input(" Search playbooks...", key="pb_search", placeholder="e.g., memory, connection, SSL...")

    playbooks = RESOLUTION_PLAYBOOKS
    if search:
        playbooks = [p for p in playbooks if search.lower() in p["name"].lower() or any(search.lower() in s.lower() for s in p["steps"])]

    for pb in playbooks:
        success_color = c['accent'] if pb['success_rate'] >= 90 else (c['warning'] if pb['success_rate'] >= 80 else c['danger'])
        steps_html = "".join([f'<div style="padding:4px 0; color:{c["text_secondary"]}; font-size:0.8rem;">  {i+1}. {step}</div>' for i, step in enumerate(pb["steps"])])

        st.markdown(f"""
        <div class="metric-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div style="flex:1;">
                    <div style="font-weight:700; color:{c['text']}; font-size:1rem; margin-bottom:8px;"> {pb['name']}</div>
                    {steps_html}
                </div>
                <div style="text-align:center; min-width:80px;">
                    <div style="font-size:1.8rem; font-weight:800; color:{success_color}; font-family:'JetBrains Mono',monospace;">{pb['success_rate']}%</div>
                    <div style="font-size:0.7rem; color:{c['text_secondary']};">Success Rate</div>
                </div>
            </div>
            {render_progress_bar(pb['success_rate'])}
        </div>
        """, unsafe_allow_html=True)


# 
# PAGE: AGENT PERFORMANCE METRICS
# 

def page_performance():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Agent Performance Metrics</div>', unsafe_allow_html=True)

    # Key metrics
    cols = st.columns(4)
    perf_metrics = [
        ("Avg Time-to-Triage", "1.2s", "", "↓0.3s from last week"),
        ("Avg Diagnosis Time", "4.7s", "", "↓1.1s improvement"),
        ("Resolution Accuracy", "94.2%", "", "+2.1% this month"),
        ("Incidents/Hour", "47", "", "+12% capacity"),
    ]
    for col, (label, value, icon, delta) in zip(cols, perf_metrics):
        with col:
            st.markdown(render_metric_card(label, value, icon, delta), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Performance over time chart (using native Streamlit)
    st.markdown(f"<div style='font-weight:700; color:{c['text']}; margin-bottom:8px;'> Performance Trend (Last 30 Days)</div>", unsafe_allow_html=True)

    # Generate trend data
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    perf_df = pd.DataFrame({
        'Date': dates,
        'Triage (s)': [max(0.8, 2.5 - i * 0.05 + random.uniform(-0.2, 0.2)) for i in range(30)],
        'Diagnosis (s)': [max(3.0, 7.0 - i * 0.12 + random.uniform(-0.5, 0.5)) for i in range(30)],
        'Resolution (s)': [max(5.0, 15.0 - i * 0.3 + random.uniform(-1.0, 1.0)) for i in range(30)],
    })
    perf_df = perf_df.set_index('Date')
    st.line_chart(perf_df, use_container_width=True)

    # Per-agent breakdown
    st.markdown(f"<br><div style='font-weight:700; color:{c['text']}; margin-bottom:8px;'> Per-Agent Breakdown</div>", unsafe_allow_html=True)
    agent_perf = pd.DataFrame({
        "Agent": AGENT_NAMES,
        "Avg Latency": ["1.2s", "4.7s", "8.3s", "2.1s"],
        "Success Rate": ["97%", "94%", "91%", "96%"],
        "Actions Today": [234, 189, 145, 98],
        "Errors": [3, 7, 12, 2],
    })
    st.dataframe(agent_perf, use_container_width=True, hide_index=True)



# 
# PAGE: EXPORT & SHARING
# 

def page_export():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Export & Sharing</div>', unsafe_allow_html=True)
    st.caption("Export incident data, generate PDF reports, and share with your team.")

    # Export options
    cols = st.columns(3)
    with cols[0]:
        st.markdown(f"""
        <div class="metric-card" style="text-align:center;">
            <div style="font-size:2rem; margin-bottom:12px;"></div>
            <div style="font-weight:700; color:{c['text']};">PDF Report</div>
            <div style="font-size:0.8rem; color:{c['text_secondary']}; margin-top:8px;">Full incident summary with charts and timeline</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(" Generate PDF", key="export_pdf", use_container_width=True):
            st.success(" PDF report generated! (demo_report_2024.pdf)")

    with cols[1]:
        st.markdown(f"""
        <div class="metric-card" style="text-align:center;">
            <div style="font-size:2rem; margin-bottom:12px;"></div>
            <div style="font-weight:700; color:{c['text']};">CSV Export</div>
            <div style="font-size:0.8rem; color:{c['text_secondary']}; margin-top:8px;">Raw incident data for custom analysis</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(" Export CSV", key="export_csv", use_container_width=True):
            df = pd.DataFrame([{
                "id": i["id"], "title": i["title"], "severity": i["severity"],
                "status": i["status"], "service": i["service"], "mttr": i["mttr_minutes"]
            } for i in st.session_state.incidents])
            csv = df.to_csv(index=False)
            st.download_button(" Download CSV", csv, "incidents.csv", "text/csv", key="dl_csv")

    with cols[2]:
        st.markdown(f"""
        <div class="metric-card" style="text-align:center;">
            <div style="font-size:2rem; margin-bottom:12px;"></div>
            <div style="font-weight:700; color:{c['text']};">Notifications</div>
            <div style="font-size:0.8rem; color:{c['text_secondary']}; margin-top:8px;">Send incident summaries to Slack/PagerDuty</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(" Send Notification", key="send_notif", use_container_width=True):
            st.success(" Notification sent to #incidents-critical channel!")

    # Sharing links (mock)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-weight:700; color:{c['text']}; margin-bottom:8px;'> Shareable Links</div>", unsafe_allow_html=True)
    st.code("https://incidentmind.app/share/report/2024-07-21-abc123", language="text")
    st.caption("Link expires in 7 days. Viewer access only.")


# 
# PAGE: CONFIDENCE CALIBRATION
# 

def page_calibration():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Confidence Calibration</div>', unsafe_allow_html=True)
    st.caption("Human feedback loop to improve agent accuracy over time.")

    # Show recent resolutions for feedback
    st.markdown(f"<div style='font-weight:700; color:{c['text']}; margin:16px 0 8px 0;'>Recent Agent Decisions - Rate Quality:</div>", unsafe_allow_html=True)

    decisions = [
        {"incident": "INC-A3F2B1C4", "decision": "Root cause: Connection pool exhaustion due to long-running queries. Recommended: Increase pool size to 200 and add query timeout of 30s.", "confidence": 0.94},
        {"incident": "INC-B7C1D9E4", "decision": "Classified as duplicate of INC-X9Y2. Merged investigation threads.", "confidence": 0.87},
        {"incident": "INC-F2E8A1B3", "decision": "Predicted cascading failure in 15min. Pre-scaled auth-service replicas from 3→8.", "confidence": 0.78},
    ]

    for i, d in enumerate(decisions):
        conf_color = c['accent'] if d['confidence'] >= 0.9 else (c['warning'] if d['confidence'] >= 0.8 else c['info'])
        st.markdown(f"""
        <div class="metric-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div style="flex:1;">
                    <div style="font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:{c['accent']}; margin-bottom:4px;">{d['incident']}</div>
                    <div style="color:{c['text']}; font-size:0.9rem;">{d['decision']}</div>
                </div>
                <div style="text-align:center; min-width:60px;">
                    <div style="font-weight:700; color:{conf_color}; font-size:1.2rem;">{d['confidence']:.0%}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button(" Correct", key=f"up_{i}"):
                st.session_state.confidence_votes["up"] += 1
                st.success("Thanks! Positive feedback recorded.")
        with col2:
            if st.button(" Wrong", key=f"down_{i}"):
                st.session_state.confidence_votes["down"] += 1
                st.warning("Feedback noted. Agent will be recalibrated.")

    # Calibration stats
    st.markdown("<br>", unsafe_allow_html=True)
    total_votes = st.session_state.confidence_votes["up"] + st.session_state.confidence_votes["down"]
    accuracy = st.session_state.confidence_votes["up"] / max(total_votes, 1) * 100

    cols = st.columns(3)
    with cols[0]:
        st.markdown(render_metric_card("Total Feedback", str(total_votes), ""), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(render_metric_card("Human Approval", f"{accuracy:.0f}%", ""), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(render_metric_card("Calibration Score", f"{min(accuracy + 5, 99):.0f}%", ""), unsafe_allow_html=True)


# 
# PAGE: PREDICTIVE ALERTS
# 

def page_predictions():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Predictive Alerts</div>', unsafe_allow_html=True)
    st.caption("Pattern-based predictions using historical incident data and embeddings.")

    # Active predictions
    predictions = [
        {"title": "Database Connection Saturation", "service": "payment-service", "probability": 0.87,
         "eta": "~15 min", "reason": "Connection pool at 82%, rate of increase matches 3 past incidents that led to exhaustion.", "action": "Pre-scale to 300 connections"},
        {"title": "Memory Pressure on ML Workers", "service": "ml-inference", "probability": 0.73,
         "eta": "~45 min", "reason": "Memory usage growing 2.1% per hour. Pattern matches OOM events from June.", "action": "Trigger GC and scale horizontally"},
        {"title": "Certificate Expiry Chain Failure", "service": "auth-service", "probability": 0.91,
         "eta": "~23 hours", "reason": "Intermediate CA cert expires in 23h. Last rotation was 364 days ago.", "action": "Auto-renew via cert-manager"},
        {"title": "Cascading Timeout Storm", "service": "service-mesh", "probability": 0.65,
         "eta": "~2 hours", "reason": "Upstream latency creeping up. Similar pattern preceded 2 cascading failures.", "action": "Enable circuit breakers preemptively"},
    ]

    for pred in predictions:
        prob_color = c['danger'] if pred['probability'] >= 0.85 else (c['warning'] if pred['probability'] >= 0.7 else c['info'])
        st.markdown(f"""
        <div class="metric-card" style="border-left:4px solid {prob_color};">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div style="flex:1;">
                    <div style="font-weight:700; color:{c['text']}; font-size:1rem;"> {pred['title']}</div>
                    <div style="font-size:0.8rem; color:{c['text_secondary']}; margin:4px 0;">
                        <code>{pred['service']}</code> · ETA: {pred['eta']}
                    </div>
                    <div style="font-size:0.85rem; color:{c['text']}; margin:8px 0;">
                        <strong>Reason:</strong> {pred['reason']}
                    </div>
                    <div style="font-size:0.85rem; color:{c['accent']};">
                        <strong>Suggested Action:</strong> {pred['action']}
                    </div>
                </div>
                <div style="text-align:center; min-width:80px;">
                    <div style="font-size:2rem; font-weight:800; color:{prob_color}; font-family:'JetBrains Mono',monospace;">{pred['probability']:.0%}</div>
                    <div style="font-size:0.7rem; color:{c['text_secondary']};">probability</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# 
# PAGE: MULTI-AGENT CHAT
# 

def page_multi_chat():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Multi-Agent Discussion</div>', unsafe_allow_html=True)
    st.caption("Watch agents collaborate to diagnose and resolve incidents in real-time.")

    # Simulate or display conversation
    if not st.session_state.multi_agent_chat:
        st.session_state.multi_agent_chat = [
            {"agent": "TriageAgent", "msg": "New incident INC-A3F2: Database Connection Pool Exhausted on payment-service. Severity assessed as CRITICAL based on blast radius (4 downstream services).", "ts": "10:23:01"},
            {"agent": "CorrelatorAgent", "msg": "I found 3 similar incidents in the last 30 days (INC-7B2C, INC-9D4E, INC-1F6A). All involved payment-service during peak traffic. Common pattern: connection pool at >95% before failure.", "ts": "10:23:03"},
            {"agent": "DiagnosisAgent", "msg": "Root cause analysis complete. The connection pool is configured at max=100 but we're seeing 97 active connections. Long-running analytics queries (avg 12s) are not releasing connections fast enough during peak load.", "ts": "10:23:08"},
            {"agent": "ResolutionAgent", "msg": "I recommend the 'DB Connection Pool Recovery' playbook (94% success rate). Steps: 1) Kill idle connections older than 30s, 2) Increase pool to 200, 3) Add query timeout of 5s for analytics. Shall I execute?", "ts": "10:23:12"},
            {"agent": "TriageAgent", "msg": "Approved. Confidence score: 0.94. Executing playbook. I'll monitor for 5 minutes post-execution and auto-close if connection count drops below 60%.", "ts": "10:23:14"},
            {"agent": "ResolutionAgent", "msg": " Playbook executed successfully. Connection pool now at 34/200 (17%). Downstream services recovering. MTTR: 13 seconds (automated).", "ts": "10:23:27"},
        ]

    agent_colors = {
        "TriageAgent": "#10b981",
        "DiagnosisAgent": "#3b82f6",
        "ResolutionAgent": "#f59e0b",
        "CorrelatorAgent": "#a855f7",
    }
    agent_icons = {
        "TriageAgent": "",
        "DiagnosisAgent": "",
        "ResolutionAgent": "",
        "CorrelatorAgent": "",
    }

    for msg in st.session_state.multi_agent_chat:
        color = agent_colors.get(msg["agent"], c['accent'])
        icon = agent_icons.get(msg["agent"], "")
        st.markdown(f"""
        <div style="display:flex; gap:12px; margin:12px 0; padding:12px 16px; background:{c['surface']}; border-radius:12px; border:1px solid {c['border']}; border-left:3px solid {color};">
            <div style="font-size:1.5rem;">{icon}</div>
            <div style="flex:1;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span style="font-weight:700; color:{color}; font-size:0.85rem;">{msg['agent']}</span>
                    <span style="font-family:'JetBrains Mono',monospace; font-size:0.7rem; color:{c['text_secondary']};">{msg['ts']}</span>
                </div>
                <div style="color:{c['text']}; font-size:0.9rem; line-height:1.5;">{msg['msg']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Simulate new message
    if st.button(" Simulate Agent Discussion", key="sim_chat"):
        new_msgs = [
            {"agent": random.choice(AGENT_NAMES), "msg": random.choice(AGENT_ACTIONS) + f" for incident INC-{str(uuid.uuid4())[:6].upper()}.", "ts": datetime.now(timezone.utc).strftime("%H:%M:%S")},
        ]
        st.session_state.multi_agent_chat.extend(new_msgs)
        st.rerun()



# 
# PAGE: RUNBOOK EXECUTION DRY RUN
# 

def page_runbook():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Runbook Execution - Dry Run</div>', unsafe_allow_html=True)
    st.caption("Preview and approve automated resolution commands before execution.")

    # Select playbook
    pb_names = [pb["name"] for pb in RESOLUTION_PLAYBOOKS]
    selected_pb = st.selectbox("Select Playbook", pb_names, key="rb_select")
    playbook = next(pb for pb in RESOLUTION_PLAYBOOKS if pb["name"] == selected_pb)

    st.markdown(f"""
    <div class="metric-card">
        <div style="font-weight:700; color:{c['text']}; margin-bottom:12px;"> {playbook['name']}</div>
        <div style="font-size:0.85rem; color:{c['text_secondary']}; margin-bottom:4px;">Success Rate: <span style="color:{c['accent']}; font-weight:700;">{playbook['success_rate']}%</span></div>
    </div>
    """, unsafe_allow_html=True)

    # Command preview with approval
    st.markdown(f"<br><div style='font-weight:700; color:{c['text']}; margin-bottom:8px;'> Commands to Execute:</div>", unsafe_allow_html=True)

    mock_commands = {
        "DB Connection Pool Recovery": [
            "kubectl exec -it payment-db-0 -- psql -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < now() - interval '30 seconds';\"",
            "kubectl set env deployment/payment-service DB_POOL_MAX=200",
            "kubectl set env deployment/payment-service DB_QUERY_TIMEOUT=5000",
            "kubectl rollout restart deployment/payment-service",
        ],
        "Memory Leak Mitigation": [
            "kubectl exec -it ml-worker-0 -- jcmd 1 GC.heap_dump /tmp/heapdump.hprof",
            "kubectl patch deployment ml-inference -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"ml-worker\",\"resources\":{\"limits\":{\"memory\":\"4Gi\"}}}]}}}}'",
            "kubectl rollout restart deployment/ml-inference --timeout=120s",
            "kubectl get pods -l app=ml-inference -w",
        ],
    }

    commands = mock_commands.get(selected_pb, [f"echo 'Executing step: {s}'" for s in playbook["steps"]])

    for i, cmd in enumerate(commands):
        step_key = f"{selected_pb}_{i}"
        approved = st.session_state.runbook_approvals.get(step_key, False)

        status_icon = "" if approved else "⏳"
        border = c['accent'] if approved else c['border']

        st.markdown(f"""
        <div style="background:{c['surface']}; border:1px solid {border}; border-radius:8px; padding:12px 16px; margin:8px 0;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:600; color:{c['text']}; font-size:0.85rem;">Step {i+1} {status_icon}</span>
                <span style="font-size:0.75rem; color:{c['text_secondary']};">{'Approved' if approved else 'Pending approval'}</span>
            </div>
            <code style="font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:{c['accent']}; word-break:break-all;">{cmd}</code>
        </div>
        """, unsafe_allow_html=True)

        if not approved:
            if st.button(f" Approve Step {i+1}", key=f"approve_{step_key}"):
                st.session_state.runbook_approvals[step_key] = True
                st.session_state.audit_log.insert(0, {
                    "ts": datetime.now(timezone.utc),
                    "user": "sre-lead@company.com",
                    "action": "approved_runbook",
                    "target": f"{selected_pb} Step {i+1}",
                })
                st.rerun()

    # Execute all
    all_approved = all(st.session_state.runbook_approvals.get(f"{selected_pb}_{i}", False) for i in range(len(commands)))
    if all_approved:
        st.success(" All steps approved!")
        if st.button(" Execute Runbook", key="execute_rb", use_container_width=True):
            st.balloons()
            st.success(f" Runbook '{selected_pb}' executed successfully! MTTR: {random.randint(8, 30)}s")


# 
# PAGE: INCIDENT DEDUPLICATION
# 

def page_dedup():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Incident Deduplication</div>', unsafe_allow_html=True)
    st.caption("AI-powered detection of duplicate and related incidents using vector similarity.")

    # Generate dedup groups
    dedup_groups = [
        {
            "primary": "INC-A3F2B1C4",
            "title": "Database Connection Pool Exhausted",
            "duplicates": [
                {"id": "INC-7B2CD9E4", "similarity": 0.96, "title": "DB pool at 100% - payment-service"},
                {"id": "INC-1F6A2B3C", "similarity": 0.92, "title": "Connection timeout on payment-db"},
                {"id": "INC-9D4E5F6A", "similarity": 0.88, "title": "Payment service unresponsive - DB issue"},
            ]
        },
        {
            "primary": "INC-B7C1D9E4",
            "title": "API Latency Spike > 5s",
            "duplicates": [
                {"id": "INC-E8F2A1B3", "similarity": 0.94, "title": "Gateway response time degraded"},
                {"id": "INC-C4D5E6F7", "similarity": 0.89, "title": "Slow API responses on /api/v2"},
            ]
        },
        {
            "primary": "INC-F2E8A1B3",
            "title": "Kubernetes Pod CrashLoopBackOff",
            "duplicates": [
                {"id": "INC-A1B2C3D4", "similarity": 0.91, "title": "ML inference pod restarting continuously"},
            ]
        },
    ]

    # Stats
    total_dupes = sum(len(g["duplicates"]) for g in dedup_groups)
    cols = st.columns(3)
    with cols[0]:
        st.markdown(render_metric_card("Dedup Groups", str(len(dedup_groups)), ""), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(render_metric_card("Duplicates Found", str(total_dupes), ""), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(render_metric_card("Noise Reduced", f"{int(total_dupes/(total_dupes+len(dedup_groups))*100)}%", ""), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Show groups
    for group in dedup_groups:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-weight:700; color:{c['text']}; margin-bottom:8px;">
                <span style="color:{c['accent']}; font-family:'JetBrains Mono',monospace;">{group['primary']}</span> - {group['title']}
            </div>
            <div style="font-size:0.8rem; color:{c['text_secondary']}; margin-bottom:12px;">Primary incident • {len(group['duplicates'])} duplicate(s) merged</div>
        """, unsafe_allow_html=True)

        for dup in group["duplicates"]:
            sim_color = c['accent'] if dup['similarity'] >= 0.95 else (c['warning'] if dup['similarity'] >= 0.9 else c['info'])
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:12px; padding:8px 12px; background:{c['surface2']}; border-radius:6px; margin:4px 0;">
                <span style="font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:{c['text_secondary']};">{dup['id']}</span>
                <span style="flex:1; font-size:0.85rem; color:{c['text']};">{dup['title']}</span>
                <span style="font-weight:700; color:{sim_color}; font-family:'JetBrains Mono',monospace; font-size:0.8rem;">{dup['similarity']:.0%} match</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)


# 
# PAGE: MTTR DASHBOARD
# 

def page_mttr():
    c = get_colors()
    st.markdown(f'<div class="section-header">⏱ Mean Time to Resolve (MTTR)</div>', unsafe_allow_html=True)

    # Key MTTR metrics
    cols = st.columns(4)
    mttr_metrics = [
        ("Overall MTTR", "8.3 min", "⏱", "↓23% from last month"),
        ("Critical MTTR", "4.1 min", "", "↓31% improvement"),
        ("Automated Resolution", "13 sec", "", "87% of incidents"),
        ("Human Escalation", "34 min", "", "13% of incidents"),
    ]
    for col, (label, value, icon, delta) in zip(cols, mttr_metrics):
        with col:
            st.markdown(render_metric_card(label, value, icon, delta), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # MTTR Trend Chart
    st.markdown(f"<div style='font-weight:700; color:{c['text']}; margin-bottom:8px;'> MTTR Trend (Last 12 Weeks)</div>", unsafe_allow_html=True)
    weeks = pd.date_range(end=datetime.now(), periods=12, freq='W')
    mttr_df = pd.DataFrame({
        'Week': weeks,
        'MTTR (minutes)': [18, 16, 15, 14, 12, 11, 10, 9.5, 9, 8.8, 8.5, 8.3],
        'Target': [10] * 12,
    })
    mttr_df = mttr_df.set_index('Week')
    st.line_chart(mttr_df, use_container_width=True)

    # MTTR by severity
    st.markdown(f"<br><div style='font-weight:700; color:{c['text']}; margin-bottom:8px;'> MTTR by Severity</div>", unsafe_allow_html=True)
    severity_mttr = pd.DataFrame({
        "Severity": ["Critical", "High", "Medium", "Warning"],
        "Avg MTTR (min)": [4.1, 8.7, 15.2, 22.8],
        "Incidents": [23, 45, 67, 31],
        "Auto-Resolved %": ["92%", "85%", "78%", "65%"],
    })
    st.dataframe(severity_mttr, use_container_width=True, hide_index=True)

    # MTTR by service
    st.markdown(f"<br><div style='font-weight:700; color:{c['text']}; margin-bottom:8px;'> MTTR by Service (Top 5)</div>", unsafe_allow_html=True)
    service_mttr = pd.DataFrame({
        "Service": ["payment-service", "gateway-api", "ml-inference", "auth-service", "data-pipeline"],
        "Avg MTTR": ["5.2 min", "7.1 min", "12.4 min", "3.8 min", "9.6 min"],
        "Trend": ["↓ Improving", "↓ Improving", "→ Stable", "↓ Best", "↑ Worsening"],
    })
    st.dataframe(service_mttr, use_container_width=True, hide_index=True)



# 
# PAGE: TOP FAILURE CATEGORIES
# 

def page_categories():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Top Failure Categories</div>', unsafe_allow_html=True)

    # Category data
    categories = [
        {"name": "Database Issues", "count": 34, "pct": 28, "color": "#ef4444"},
        {"name": "API Latency", "count": 28, "pct": 23, "color": "#f59e0b"},
        {"name": "Memory/Resource", "count": 22, "pct": 18, "color": "#3b82f6"},
        {"name": "Network/DNS", "count": 15, "pct": 12, "color": "#a855f7"},
        {"name": "Certificate/TLS", "count": 12, "pct": 10, "color": "#06b6d4"},
        {"name": "Kubernetes", "count": 8, "pct": 7, "color": "#10b981"},
        {"name": "Other", "count": 3, "pct": 2, "color": "#6b7280"},
    ]

    # Horizontal bar chart (custom HTML)
    chart_html = f'<div style="background:{c["surface"]}; border-radius:12px; padding:24px; border:1px solid {c["border"]};">'
    for cat in categories:
        chart_html += f"""
        <div style="display:flex; align-items:center; gap:12px; margin:12px 0;">
            <div style="width:140px; font-size:0.85rem; font-weight:500; color:{c['text']};">{cat['name']}</div>
            <div style="flex:1; background:{c['surface2']}; border-radius:6px; height:24px; overflow:hidden; position:relative;">
                <div style="width:{cat['pct']}%; height:100%; background:{cat['color']}; border-radius:6px; transition:width 0.5s;"></div>
            </div>
            <div style="width:60px; text-align:right; font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:{c['text']}; font-weight:600;">{cat['count']}</div>
            <div style="width:40px; text-align:right; font-size:0.8rem; color:{c['text_secondary']};">{cat['pct']}%</div>
        </div>
        """
    chart_html += "</div>"
    st.markdown(chart_html, unsafe_allow_html=True)

    # Pie chart using Streamlit bar_chart (simplified)
    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns(2)

    with cols[0]:
        st.markdown(f"<div style='font-weight:700; color:{c['text']}; margin-bottom:8px;'> Incidents by Service</div>", unsafe_allow_html=True)
        service_counts = {}
        for inc in st.session_state.incidents:
            service_counts[inc["service"]] = service_counts.get(inc["service"], 0) + 1
        svc_df = pd.DataFrame({"Service": list(service_counts.keys()), "Count": list(service_counts.values())})
        svc_df = svc_df.sort_values("Count", ascending=False).head(8)
        st.bar_chart(svc_df.set_index("Service"), use_container_width=True)

    with cols[1]:
        st.markdown(f"<div style='font-weight:700; color:{c['text']}; margin-bottom:8px;'> Severity Distribution</div>", unsafe_allow_html=True)
        sev_counts = {}
        for inc in st.session_state.incidents:
            sev_counts[inc["severity"]] = sev_counts.get(inc["severity"], 0) + 1
        sev_df = pd.DataFrame({"Severity": list(sev_counts.keys()), "Count": list(sev_counts.values())})
        st.bar_chart(sev_df.set_index("Severity"), use_container_width=True)

    # Trend comparison
    st.markdown(f"<br><div style='font-weight:700; color:{c['text']}; margin-bottom:8px;'> Category Trends (4 Weeks)</div>", unsafe_allow_html=True)
    trend_df = pd.DataFrame({
        'Week': pd.date_range(end=datetime.now(), periods=4, freq='W'),
        'Database': [12, 10, 8, 4],
        'API': [8, 9, 7, 5],
        'Memory': [6, 7, 5, 5],
        'Network': [4, 3, 4, 4],
    })
    trend_df = trend_df.set_index('Week')
    st.line_chart(trend_df, use_container_width=True)


# 
# PAGE: AGENT ROI CALCULATOR
# 

def page_roi():
    c = get_colors()
    st.markdown(f'<div class="section-header"> Agent ROI Calculator</div>', unsafe_allow_html=True)
    st.caption("Calculate the return on investment from AI-automated incident response.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"<div style='font-weight:700; color:{c['text']}; margin-bottom:12px;'> Input Parameters</div>", unsafe_allow_html=True)
        incidents_per_month = st.slider("Incidents per Month", 50, 500, 200, key="roi_incidents")
        avg_manual_mttr = st.slider("Avg Manual MTTR (minutes)", 15, 120, 45, key="roi_manual_mttr")
        engineer_hourly_cost = st.slider("Engineer Hourly Cost ($)", 50, 250, 150, key="roi_cost")
        automation_rate = st.slider("Automation Rate (%)", 50, 95, 85, key="roi_auto")
        ai_mttr = st.slider("AI Agent MTTR (minutes)", 1, 15, 3, key="roi_ai_mttr")

    with col2:
        st.markdown(f"<div style='font-weight:700; color:{c['text']}; margin-bottom:12px;'> ROI Results</div>", unsafe_allow_html=True)

        # Calculations
        manual_hours_per_month = (incidents_per_month * avg_manual_mttr) / 60
        manual_cost_per_month = manual_hours_per_month * engineer_hourly_cost

        automated_incidents = int(incidents_per_month * automation_rate / 100)
        manual_incidents = incidents_per_month - automated_incidents

        ai_hours = (automated_incidents * ai_mttr) / 60
        remaining_manual_hours = (manual_incidents * avg_manual_mttr) / 60
        new_cost = remaining_manual_hours * engineer_hourly_cost + 2000  # platform cost

        savings_per_month = manual_cost_per_month - new_cost
        savings_per_year = savings_per_month * 12
        roi_pct = (savings_per_year / (2000 * 12)) * 100  # ROI on platform investment

        time_saved_hours = manual_hours_per_month - (ai_hours + remaining_manual_hours)

        st.markdown(render_metric_card("Monthly Savings", f"${savings_per_month:,.0f}", "", f"${savings_per_year:,.0f}/year"), unsafe_allow_html=True)
        st.markdown(render_metric_card("Hours Saved/Month", f"{time_saved_hours:.0f}h", "⏰", f"{time_saved_hours*12:.0f}h/year"), unsafe_allow_html=True)
        st.markdown(render_metric_card("ROI", f"{roi_pct:.0f}%", "", "On platform investment"), unsafe_allow_html=True)

    # Comparison table
    st.markdown(f"<br><div style='font-weight:700; color:{c['text']}; margin-bottom:8px;'> Before vs After Comparison</div>", unsafe_allow_html=True)
    comparison = pd.DataFrame({
        "Metric": ["Incidents/Month", "Avg MTTR", "Engineer Hours/Month", "Monthly Cost", "Auto-Resolution Rate"],
        "Before (Manual)": [str(incidents_per_month), f"{avg_manual_mttr} min", f"{manual_hours_per_month:.0f}h", f"${manual_cost_per_month:,.0f}", "0%"],
        "After (AI Agents)": [str(incidents_per_month), f"{ai_mttr} min (automated)", f"{remaining_manual_hours:.0f}h", f"${new_cost:,.0f}", f"{automation_rate}%"],
        "Improvement": ["-", f"↓{avg_manual_mttr - ai_mttr} min", f"↓{time_saved_hours:.0f}h", f"↓${savings_per_month:,.0f}", f"+{automation_rate}%"],
    })
    st.dataframe(comparison, use_container_width=True, hide_index=True)

    # Payback period
    platform_annual_cost = 2000 * 12
    if savings_per_year > 0:
        payback_months = platform_annual_cost / (savings_per_year / 12)
        st.markdown(f"""
        <div class="metric-card" style="text-align:center; margin-top:16px; border-color:{c['accent']};">
            <div style="font-size:0.9rem; color:{c['text_secondary']};">Estimated Payback Period</div>
            <div style="font-size:2.5rem; font-weight:800; color:{c['accent']}; font-family:'JetBrains Mono',monospace;">{payback_months:.1f} months</div>
            <div style="font-size:0.8rem; color:{c['text_secondary']}; margin-top:4px;">Platform pays for itself in under {math.ceil(payback_months)} months</div>
        </div>
        """, unsafe_allow_html=True)


# 
# MAIN ROUTER
# 

PAGE_MAP = {
    "home": page_home,
    "incidents": page_incidents,
    "agent_feed": page_agent_feed,
    "knowledge_graph": page_knowledge_graph,
    "mcp_query": page_mcp_query,
    "health": page_health,
    "audit": page_audit,
    "rbac": page_rbac,
    "regions": page_regions,
    "rate_limit": page_rate_limit,
    "heatmap": page_heatmap,
    "playbooks": page_playbooks,
    "performance": page_performance,
    "export": page_export,
    "calibration": page_calibration,
    "predictions": page_predictions,
    "multi_chat": page_multi_chat,
    "runbook": page_runbook,
    "dedup": page_dedup,
    "mttr": page_mttr,
    "categories": page_categories,
    "roi": page_roi,
}

# Route to correct page
current = st.session_state.current_page
if current in PAGE_MAP:
    PAGE_MAP[current]()
else:
    page_home()

#  Footer 
c = get_colors()
st.markdown(f"""
<div style="margin-top:64px; padding:24px; text-align:center; border-top:1px solid {c['border']};">
    <div style="font-size:0.8rem; color:{c['text_secondary']};">
         IncidentMind - Multi-Agent DevOps Incident Responder<br>
        Built with CockroachDB • AWS Bedrock • LangChain • MCP Protocol<br>
        <span style="font-family:'JetBrains Mono',monospace;">CockroachDB × AWS Hackathon 2024</span>
    </div>
</div>
""", unsafe_allow_html=True)
