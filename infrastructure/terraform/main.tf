resource "aws_s3_bucket" "documents" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_sqs_queue" "ingestion" {
  name = var.queue_name
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
