# IncidentMind 🧠⚡

**Multi-Agent DevOps Incident Responder with Persistent Agentic Memory**

An AI-powered incident response system where specialized agents collaborate to diagnose, correlate, and resolve production incidents — all sharing a persistent, distributed memory layer powered by CockroachDB on AWS.

![Architecture](architecture.png)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Event Sources                        │
│  (CloudWatch Alarms, PagerDuty, Slack webhooks)      │
└──────────────────────┬──────────────────────────────┘
                       ▼
            ┌─────────────────────┐
            │   AWS Lambda         │
            │   (Event Ingestion)  │
            └──────────┬──────────┘
                       ▼
┌──────────────────────────────────────────────────────┐
│              Agent Orchestrator (ECS)                  │
│                                                        │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────┐  │
│  │  Triage   │  │ Diagnosis  │  │   Correlator     │  │
│  │  Agent    │  │  Agent     │  │   Agent          │  │
│  └─────┬────┘  └─────┬──────┘  └────────┬─────────┘  │
│        └──────────────┴───────────────────┘            │
└───────────────────────┼────────────────────────────────┘
                        ▼
         ┌──────────────────────────────┐
         │      CockroachDB Cloud        │
         │  (Shared Agentic Memory)      │
         │                              │
         │  • Agent state & tasks       │
         │  • Incident history          │
         │  • Vector embeddings (RAG)   │
         │  • Correlation patterns      │
         │  • Reasoning traces          │
         └──────────────────────────────┘
                        ▲
                        │ MCP Server
                        ▼
              ┌──────────────────┐
              │  Claude/Cursor    │
              │  (Human operator  │
              │   queries memory) │
              └──────────────────┘
```

## 🚀 Features

- **Triage Agent** — Classifies incoming alerts, assigns severity, matches known patterns
- **Diagnosis Agent** — Semantic search over past incidents using vector embeddings to find similar root causes
- **Correlator Agent** — Identifies recurring failure patterns and builds institutional knowledge
- **Resolution Agent** — Suggests fixes based on past successful resolutions
- **Zero-downtime Recovery** — Kill any agent mid-task; it resumes from CockroachDB state
- **MCP Server Integration** — Human operators query incident memory via Claude/Cursor
- **Learning Over Time** — The system gets smarter with every resolved incident

## 🛠️ CockroachDB Tools Used

| Tool | Usage |
|------|-------|
| **Distributed Vector Indexing** | Semantic search over incident history, symptoms, and resolutions |
| **MCP Server** | Human operators query incident memory directly via Claude/Cursor |
| **ccloud CLI** | Automated cluster provisioning, backup scheduling, RBAC setup |

## ☁️ AWS Services Used

| Service | Usage |
|---------|-------|
| **Amazon Bedrock** | Claude 3.5 Sonnet for agent reasoning, Titan Embeddings v2 for vectors |
| **AWS Lambda** | Event ingestion from monitoring sources |
| **Amazon ECS** | Persistent agent orchestrator runtime |
| **Amazon S3** | Raw log artifacts and incident attachments |

## 📦 Prerequisites

- Python 3.11+
- AWS Account with Bedrock access
- CockroachDB Cloud account
- Docker (for local development)
- Terraform (for infrastructure deployment)

## 🏁 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/sathiyanarayanan17/incidentmind.git
cd incidentmind
```

### 2. Set up environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your CockroachDB and AWS credentials
```

### 3. Set up CockroachDB cluster

```bash
# Using ccloud CLI
chmod +x scripts/setup_cluster.sh
./scripts/setup_cluster.sh
```

### 4. Initialize the database schema

```bash
python scripts/seed_data.py
```

### 5. Run the demo

```bash
streamlit run demo/app.py
```

### 6. Run the agent orchestrator

```bash
python -m src.orchestrator.main
```

## 🧪 Testing

```bash
pytest tests/ -v
```

## 📁 Project Structure

```
incidentmind/
├── LICENSE
├── README.md
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── terraform/              # AWS + CockroachDB infrastructure
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── src/
│   ├── agents/             # Agent implementations
│   │   ├── base.py
│   │   ├── triage.py
│   │   ├── diagnosis.py
│   │   ├── correlator.py
│   │   └── resolution.py
│   ├── memory/             # CockroachDB memory layer
│   │   ├── cockroach.py
│   │   ├── embeddings.py
│   │   └── state.py
│   ├── ingestion/          # AWS Lambda handler
│   │   └── lambda_handler.py
│   └── orchestrator/       # Main agent loop
│       └── main.py
├── scripts/
│   ├── setup_cluster.sh    # ccloud CLI automation
│   └── seed_data.py        # Schema + sample data
├── mcp/
│   └── mcp_config.json     # MCP Server configuration
├── demo/
│   └── app.py              # Streamlit demo UI
└── tests/
    └── test_memory.py
```

## 🔒 Security

- Service account RBAC via ccloud CLI
- Read-only MCP Server access for operators
- All credentials in environment variables (never committed)
- Serializable transaction isolation for concurrent agent writes

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

## 🏆 Hackathon

Built for the [CockroachDB × AWS Hackathon](https://cockroachdblabs.devpost.com/) on Devpost.
