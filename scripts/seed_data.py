"""Seed script — Initializes schema and loads sample incident data.

Run with: python scripts/seed_data.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.memory.cockroach import CockroachMemory
from src.memory.embeddings import EmbeddingManager


SAMPLE_INCIDENTS = [
    {
        "title": "High CPU usage on prod-web-01 (95% for 10 minutes)",
        "severity": 2,
        "source": "cloudwatch",
        "symptoms": {
            "error_message": "CPU utilization exceeded 95% threshold",
            "affected_service": "prod-web-01",
            "metrics": {"cpu_percent": 95, "duration_minutes": 10},
        },
        "root_cause": "Memory leak in image processing service causing excessive garbage collection",
        "resolution": "Restarted image-processor pod and deployed fix for memory leak in v2.3.1",
    },
    {
        "title": "Database connection pool exhausted — payment service",
        "severity": 1,
        "source": "pagerduty",
        "symptoms": {
            "error_message": "ConnectionPoolExhausted: No available connections after 30s timeout",
            "affected_service": "payment-service",
            "metrics": {"active_connections": 100, "max_pool_size": 100, "queue_depth": 47},
        },
        "root_cause": "Slow query on orders table due to missing index, holding connections",
        "resolution": "Added index on orders(user_id, created_at) and increased pool size to 150",
    },
    {
        "title": "502 Bad Gateway errors on /api/users endpoint",
        "severity": 2,
        "source": "datadog",
        "symptoms": {
            "error_message": "502 Bad Gateway",
            "affected_service": "api-gateway",
            "metrics": {"error_rate": 23.5, "p99_latency_ms": 12000},
        },
        "root_cause": "User service pods crashed due to OOM kill (memory limit 512Mi too low)",
        "resolution": "Increased memory limit to 1Gi and added HPA for user-service deployment",
    },
    {
        "title": "SSL certificate expiring in 24 hours — api.example.com",
        "severity": 2,
        "source": "cloudwatch",
        "symptoms": {
            "error_message": "Certificate expires in 24 hours",
            "affected_service": "api.example.com",
            "metrics": {"hours_remaining": 24},
        },
        "root_cause": "cert-manager renewal job failed due to DNS validation timeout",
        "resolution": "Manually renewed certificate and fixed DNS01 solver configuration",
    },
    {
        "title": "Kafka consumer lag exceeding 100k messages",
        "severity": 3,
        "source": "grafana",
        "symptoms": {
            "error_message": "Consumer group 'order-processor' lag exceeding threshold",
            "affected_service": "order-processor",
            "metrics": {"consumer_lag": 105000, "partition_count": 12},
        },
        "root_cause": "Downstream API rate limiting caused processing backlog",
        "resolution": "Implemented exponential backoff and increased consumer instances from 3 to 6",
    },
]


def main():
    print("🌱 IncidentMind — Seeding Database")
    print("=" * 50)

    # Initialize memory
    memory = CockroachMemory()
    embeddings = EmbeddingManager()

    # Create schema
    print("\n📋 Creating schema...")
    memory.initialize_schema()
    memory.create_vector_index()
    print("   ✅ Schema created")

    # Seed sample incidents
    print(f"\n📝 Seeding {len(SAMPLE_INCIDENTS)} sample incidents...")
    for i, incident_data in enumerate(SAMPLE_INCIDENTS, 1):
        # Create incident
        incident_id = memory.create_incident(
            title=incident_data["title"],
            severity=incident_data["severity"],
            source=incident_data["source"],
            symptoms=incident_data["symptoms"],
        )

        # Update with resolution
        memory.update_incident(
            incident_id,
            status="resolved",
            root_cause=incident_data["root_cause"],
            resolution=incident_data["resolution"],
        )

        # Store embeddings
        print(f"   [{i}/{len(SAMPLE_INCIDENTS)}] {incident_data['title'][:50]}...")

        # Symptom embedding
        symptom_text = f"{incident_data['title']}\n{incident_data['symptoms'].get('error_message', '')}"
        embeddings.store_incident_embedding(
            incident_id, "symptom", symptom_text
        )

        # Root cause embedding
        embeddings.store_incident_embedding(
            incident_id, "root_cause", incident_data["root_cause"]
        )

        # Resolution embedding
        embeddings.store_incident_embedding(
            incident_id, "resolution", incident_data["resolution"]
        )

    print(f"\n   ✅ {len(SAMPLE_INCIDENTS)} incidents seeded with embeddings")

    # Seed some correlation patterns
    print("\n🧬 Seeding correlation patterns...")
    patterns = [
        {
            "name": "Connection Pool Exhaustion",
            "conditions": {"keywords": ["connection pool", "exhausted", "no available connections", "timeout"]},
            "action": "Check for slow queries and missing indexes. Consider increasing pool size.",
            "confidence": 0.8,
        },
        {
            "name": "OOM Kill",
            "conditions": {"keywords": ["OOM", "out of memory", "memory limit", "killed"]},
            "action": "Increase memory limits and check for memory leaks. Review pod resource requests.",
            "confidence": 0.85,
        },
        {
            "name": "Certificate Expiry",
            "conditions": {"keywords": ["certificate", "expiring", "SSL", "TLS", "cert"]},
            "action": "Check cert-manager logs and renew certificate. Verify DNS validation.",
            "confidence": 0.9,
        },
    ]

    for p in patterns:
        memory.store_pattern(
            pattern_name=p["name"],
            conditions=p["conditions"],
            suggested_action=p["action"],
            confidence=p["confidence"],
        )
    print(f"   ✅ {len(patterns)} patterns seeded")

    # Cleanup
    memory.close()
    embeddings.close()

    print("\n" + "=" * 50)
    print("✅ Database seeded successfully!")
    print("   Run: streamlit run demo/app.py")


if __name__ == "__main__":
    main()
