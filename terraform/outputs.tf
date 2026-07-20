output "lambda_function_arn" {
  description = "ARN of the incident ingestion Lambda"
  value       = aws_lambda_function.incident_ingestion.arn
}

output "sns_topic_arn" {
  description = "ARN of the incident alerts SNS topic"
  value       = aws_sns_topic.incident_alerts.arn
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster running agents"
  value       = aws_ecs_cluster.agents.name
}

output "s3_bucket_name" {
  description = "S3 bucket for incident artifacts"
  value       = aws_s3_bucket.incident_artifacts.id
}
