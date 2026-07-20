variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "incidentmind"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "cockroachdb_url" {
  description = "CockroachDB Cloud connection URL"
  type        = string
  sensitive   = true
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID for agent reasoning"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

variable "bedrock_embedding_model_id" {
  description = "Amazon Bedrock model ID for embeddings"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "ecr_repository_url" {
  description = "ECR repository URL for the orchestrator container image"
  type        = string
  default     = ""
}
