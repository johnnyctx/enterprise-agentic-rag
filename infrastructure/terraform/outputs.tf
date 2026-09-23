output "bucket_name" { value = aws_s3_bucket.documents.bucket }
output "queue_url" { value = aws_sqs_queue.ingestion.url }
output "metadata_table" { value = aws_dynamodb_table.metadata.name }
