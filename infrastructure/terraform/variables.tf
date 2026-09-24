variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "bucket_name" {
  type    = string
  default = "enterprise-agentic-rag-documents"
}

variable "queue_name" {
  type    = string
  default = "enterprise-agentic-rag-ingestion"
}

variable "metadata_table_name" {
  type    = string
  default = "enterprise-agentic-rag-metadata"
}
