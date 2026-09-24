from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    aws_region: str = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

    # Local host processes use LocalStack on localhost.
    # Docker Compose overrides this with http://localstack:4566.
    # Production can set ENVIRONMENT=production and leave AWS_ENDPOINT_URL unset.
    aws_endpoint_url: str | None = os.getenv(
        "AWS_ENDPOINT_URL",
        "http://localhost:4566" if os.getenv("ENVIRONMENT", "local") == "local" else None,
    ) or None

    s3_bucket: str = os.getenv("S3_BUCKET", "enterprise-agentic-rag-documents")
    sqs_queue: str = os.getenv("SQS_QUEUE", "enterprise-agentic-rag-ingestion")
    metadata_table: str = os.getenv("METADATA_TABLE", "enterprise-agentic-rag-metadata")
    index_path: str = os.getenv("INDEX_PATH", "data/runtime/index.sqlite3")
    llm_provider: str = os.getenv("LLM_PROVIDER", "demo")
    model_name: str = os.getenv("MODEL_NAME", "deterministic-demo")
    environment: str = os.getenv("ENVIRONMENT", "local")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    max_agent_attempts: int = int(os.getenv("MAX_AGENT_ATTEMPTS", "2"))


settings = Settings()