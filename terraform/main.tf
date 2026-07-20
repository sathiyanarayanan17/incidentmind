# ─────────────────────────────────────────────────────────────────
# IncidentMind — Terraform Infrastructure
# AWS + CockroachDB Cloud deployment
# ─────────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ─── S3 Bucket for Log Artifacts ──────────────────────────────────

resource "aws_s3_bucket" "incident_artifacts" {
  bucket = "${var.project_name}-artifacts-${var.environment}"
  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "artifacts_versioning" {
  bucket = aws_s3_bucket.incident_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts_encryption" {
  bucket = aws_s3_bucket.incident_artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# ─── Lambda Function for Ingestion ───────────────────────────────

resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role.name
}

resource "aws_iam_role_policy" "lambda_bedrock" {
  name = "${var.project_name}-bedrock-access"
  role = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "incident_ingestion" {
  filename         = "lambda_package.zip"
  function_name    = "${var.project_name}-ingestion"
  role             = aws_iam_role.lambda_role.arn
  handler          = "src.ingestion.lambda_handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      COCKROACHDB_URL             = var.cockroachdb_url
      AWS_REGION_NAME             = var.aws_region
      BEDROCK_MODEL_ID            = var.bedrock_model_id
      BEDROCK_EMBEDDING_MODEL_ID  = var.bedrock_embedding_model_id
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# SNS Topic for CloudWatch Alarms
resource "aws_sns_topic" "incident_alerts" {
  name = "${var.project_name}-alerts"
}

resource "aws_sns_topic_subscription" "lambda_sub" {
  topic_arn = aws_sns_topic.incident_alerts.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.incident_ingestion.arn
}

resource "aws_lambda_permission" "sns_invoke" {
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.incident_ingestion.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.incident_alerts.arn
}

# ─── ECS Cluster for Agent Orchestrator ───────────────────────────

resource "aws_ecs_cluster" "agents" {
  name = "${var.project_name}-agents"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "orchestrator" {
  family                   = "${var.project_name}-orchestrator"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.lambda_role.arn
  task_role_arn            = aws_iam_role.lambda_role.arn

  container_definitions = jsonencode([
    {
      name  = "orchestrator"
      image = "${var.ecr_repository_url}:latest"
      portMappings = []
      environment = [
        { name = "COCKROACHDB_URL", value = var.cockroachdb_url },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "BEDROCK_MODEL_ID", value = var.bedrock_model_id },
        { name = "BEDROCK_EMBEDDING_MODEL_ID", value = var.bedrock_embedding_model_id },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "orchestrator"
        }
      }
    }
  ])
}

resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 30
}
