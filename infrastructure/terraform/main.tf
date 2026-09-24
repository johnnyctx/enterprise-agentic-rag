resource "aws_s3_bucket" "documents" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_sqs_queue" "ingestion_dlq" {
  name = "${var.queue_name}-dlq"
}

resource "aws_sqs_queue" "ingestion" {
  name = var.queue_name

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ingestion_dlq.arn
    maxReceiveCount     = 5
  })
}

resource "aws_sqs_queue_policy" "ingestion" {
  queue_url = aws_sqs_queue.ingestion.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "AllowS3ToSendMessage"
        Effect = "Allow"

        Principal = {
          Service = "s3.amazonaws.com"
        }

        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.ingestion.arn

        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_s3_bucket.documents.arn
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_notification" "documents" {
  bucket = aws_s3_bucket.documents.id

  queue {
    queue_arn = aws_sqs_queue.ingestion.arn

    events = [
      "s3:ObjectCreated:*"
    ]

    filter_suffix = ".pdf"
  }

  depends_on = [
    aws_sqs_queue_policy.ingestion
  ]
}

resource "aws_dynamodb_table" "metadata" {
  name         = "enterprise-agentic-rag-metadata"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "doc_id"

  attribute {
    name = "doc_id"
    type = "S"
  }
}

resource "aws_secretsmanager_secret" "llm" {
  name = "enterprise-agentic-rag/llm"
}