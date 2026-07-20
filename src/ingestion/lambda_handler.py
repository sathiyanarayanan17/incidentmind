"""AWS Lambda handler for incident ingestion.

This Lambda function receives incident alerts from:
- CloudWatch Alarms (via SNS)
- PagerDuty webhooks
- Manual API calls

It creates the incident in CockroachDB and triggers the agent pipeline.
"""

import json
import os
import structlog

from src.memory.cockroach import CockroachMemory

logger = structlog.get_logger(__name__)


def lambda_handler(event, context):
    """AWS Lambda entry point for incident ingestion.
    
    Supports multiple event sources:
    - SNS (CloudWatch Alarms)
    - API Gateway (direct HTTP)
    - EventBridge
    """
    logger.info("lambda_invoked", event_source=_detect_source(event))
    
    memory = CockroachMemory()

    try:
        # Parse the incident from the event
        incident_data = _parse_event(event)

        if not incident_data:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Could not parse incident from event"}),
            }

        # Create the incident in CockroachDB
        incident_id = memory.create_incident(
            title=incident_data["title"],
            severity=incident_data.get("severity", 3),
            source=incident_data.get("source", "lambda"),
            symptoms=incident_data.get("symptoms", {}),
        )

        logger.info("incident_ingested", incident_id=incident_id, title=incident_data["title"])

        return {
            "statusCode": 201,
            "body": json.dumps({
                "incident_id": incident_id,
                "title": incident_data["title"],
                "status": "created",
                "message": "Incident created and queued for processing",
            }),
        }

    except Exception as e:
        logger.error("lambda_error", error=str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
    finally:
        memory.close()


def _detect_source(event: dict) -> str:
    """Detect the event source."""
    if "Records" in event and event["Records"][0].get("EventSource") == "aws:sns":
        return "sns"
    if "httpMethod" in event:
        return "api_gateway"
    if "source" in event and event["source"].startswith("aws."):
        return "eventbridge"
    return "direct"


def _parse_event(event: dict) -> dict | None:
    """Parse incident data from various event sources."""
    source = _detect_source(event)

    if source == "sns":
        return _parse_sns_event(event)
    elif source == "api_gateway":
        return _parse_api_gateway_event(event)
    elif source == "direct":
        return _parse_direct_event(event)
    return None


def _parse_sns_event(event: dict) -> dict | None:
    """Parse CloudWatch Alarm via SNS."""
    try:
        record = event["Records"][0]
        message = json.loads(record["Sns"]["Message"])

        # CloudWatch Alarm format
        if "AlarmName" in message:
            severity_map = {"ALARM": 2, "INSUFFICIENT_DATA": 3, "OK": 5}
            return {
                "title": f"CloudWatch Alarm: {message['AlarmName']}",
                "severity": severity_map.get(message.get("NewStateValue"), 3),
                "source": "cloudwatch",
                "symptoms": {
                    "alarm_name": message["AlarmName"],
                    "description": message.get("AlarmDescription", ""),
                    "reason": message.get("NewStateReason", ""),
                    "metric": message.get("Trigger", {}).get("MetricName", ""),
                    "namespace": message.get("Trigger", {}).get("Namespace", ""),
                },
            }
        # Generic SNS message
        return {
            "title": record["Sns"].get("Subject", "SNS Alert"),
            "severity": 3,
            "source": "sns",
            "symptoms": message if isinstance(message, dict) else {"message": message},
        }
    except (KeyError, json.JSONDecodeError) as e:
        logger.error("sns_parse_error", error=str(e))
        return None


def _parse_api_gateway_event(event: dict) -> dict | None:
    """Parse direct API Gateway request."""
    try:
        body = json.loads(event.get("body", "{}"))
        if not body.get("title"):
            return None
        return {
            "title": body["title"],
            "severity": body.get("severity", 3),
            "source": body.get("source", "api"),
            "symptoms": body.get("symptoms", {}),
        }
    except json.JSONDecodeError:
        return None


def _parse_direct_event(event: dict) -> dict | None:
    """Parse direct Lambda invocation."""
    if "title" in event:
        return {
            "title": event["title"],
            "severity": event.get("severity", 3),
            "source": event.get("source", "direct"),
            "symptoms": event.get("symptoms", {}),
        }
    return None
