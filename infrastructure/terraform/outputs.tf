output "bucket_name" { value = aws_s3_bucket.documents.bucket }
output "queue_url" { value = aws_sqs_queue.ingestion.url }
output "dead_letter_queue_url" { value = aws_sqs_queue.ingestion_dlq.url }
output "metadata_table" { value = aws_dynamodb_table.metadata.name }
