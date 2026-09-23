import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_endpoint_url: str | None = os.getenv("AWS_ENDPOINT_URL") or None
    s3_bucket: str = os.getenv("S3_BUCKET", "enterprise-agentic-rag-documents")
    sqs_queue: str = os.getenv("SQS_QUEUE", "enterprise-agentic-rag-ingestion")
    vector_store: str = os.getenv("VECTOR_STORE", "memory")
    llm_provider: str = os.getenv("LLM_PROVIDER", "demo")
    model_name: str = os.getenv("MODEL_NAME", "deterministic-demo")
    environment: str = os.getenv("ENVIRONMENT", "local")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
