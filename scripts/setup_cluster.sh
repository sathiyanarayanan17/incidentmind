#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# IncidentMind — CockroachDB Cluster Setup via ccloud CLI
# 
# This script automates:
# 1. Cluster creation
# 2. Database and user setup
# 3. Service account for agent access (RBAC)
# 4. Backup schedule configuration
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-incidentmind-prod}"
REGION="${REGION:-aws-us-east-1}"
PLAN="${PLAN:-basic}"
DB_NAME="incidentmind"

echo "🚀 IncidentMind — CockroachDB Cloud Setup"
echo "==========================================="
echo ""

# Check ccloud CLI is installed
if ! command -v ccloud &> /dev/null; then
    echo "❌ ccloud CLI not found. Install from: https://www.cockroachlabs.com/docs/cockroachcloud/ccloud-get-started"
    exit 1
fi

# Step 1: Create cluster
echo "📦 Creating CockroachDB cluster: $CLUSTER_NAME"
CLUSTER_ID=$(ccloud cluster create "$CLUSTER_NAME" \
    --plan "$PLAN" \
    --cloud-provider aws \
    --region "$REGION" \
    --output json | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "   ✅ Cluster created: $CLUSTER_ID"

# Step 2: Wait for cluster to be ready
echo "⏳ Waiting for cluster to be ready..."
ccloud cluster wait "$CLUSTER_ID" --timeout 300

# Step 3: Create database
echo "🗄️  Creating database: $DB_NAME"
ccloud cluster sql "$CLUSTER_ID" --execute "CREATE DATABASE IF NOT EXISTS $DB_NAME;"
echo "   ✅ Database created"

# Step 4: Create service account for agent access
echo "🔐 Creating service account for agent RBAC..."
SA_ID=$(ccloud service-account create "incidentmind-agent" \
    --description "Service account for IncidentMind agents" \
    --output json | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "   ✅ Service account created: $SA_ID"

# Step 5: Create API key for the service account
echo "🔑 Creating API key..."
API_KEY=$(ccloud service-account api-key create "$SA_ID" \
    --description "IncidentMind agent key" \
    --output json)

echo "   ✅ API key created"
echo ""
echo "   ⚠️  Save these credentials — they won't be shown again:"
echo "   $API_KEY"

# Step 6: Configure backup schedule
echo "💾 Configuring backup schedule..."
ccloud cluster backup configure "$CLUSTER_ID" \
    --schedule "daily" \
    --retention-days 30

echo "   ✅ Daily backups configured (30-day retention)"

# Step 7: Get connection string
echo ""
echo "📋 Connection Details:"
echo "─────────────────────"
CONNECTION_STRING=$(ccloud cluster connection-string "$CLUSTER_ID" \
    --database "$DB_NAME" \
    --output json | python -c "import sys,json; print(json.load(sys.stdin)['connection_string'])")

echo "   Connection URL: $CONNECTION_STRING"
echo ""
echo "   Add to your .env file:"
echo "   COCKROACHDB_URL=$CONNECTION_STRING"
echo "   COCKROACHDB_CLUSTER_ID=$CLUSTER_ID"
echo ""
echo "✅ Setup complete! Run 'python scripts/seed_data.py' to initialize the schema."
