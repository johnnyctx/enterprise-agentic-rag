"""Durable S3 -> SQS -> ingestion/indexing worker boundary."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from urllib.parse import unquote_plus

import boto3

from app.config import settings
from app.ingestion.chunker import chunk_document, load_markdown
from app.ingestion.pipeline import ingest_pdf
from app.rag.store import HybridIndex

logger = logging.getLogger(__name__)


def _client(service: str):
    return boto3.client(
        service,
        region_name=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


def _queue_url() -> str:
    configured = os.getenv("INGESTION_QUEUE_URL")
    if configured:
        return configured
    return _client("sqs").get_queue_url(QueueName=settings.sqs_queue)["QueueUrl"]


def _document_id(bucket: str, key: str, version_id: str | None) -> str:
    identity = f"{bucket}:{key}:{version_id or 'null'}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def _parse_s3_records(body: str) -> list[dict]:
    event = json.loads(body)

    # LocalStack/S3 sends a one-time TestEvent when the bucket
    # notification configuration is created. It is not a document event.
    if event.get("Event") == "s3:TestEvent":
        return []

    records = event.get("Records")
    if not isinstance(records, list):
        raise ValueError("SQS message does not contain S3 Records")

    return records


def _metadata_value(
    s3_client,
    bucket: str,
    key: str,
    field: str,
    default: str = "",
) -> str:
    try:
        head = s3_client.head_object(Bucket=bucket, Key=key)
        return str(head.get("Metadata", {}).get(field, default))
    except Exception:
        return default


def process_message(message: dict, index: HybridIndex | None = None) -> int:
    records = _parse_s3_records(message["Body"])

    # Non-document events such as S3 TestEvent are successfully acknowledged.
    if not records:
        return 0

    s3 = _client("s3")
    dynamodb = _client("dynamodb")
    index = index or HybridIndex(settings.index_path)
    processed = 0

    for record in records:
        if record.get("eventSource") != "aws:s3":
            raise ValueError("Unsupported event source")

        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        version_id = record["s3"]["object"].get("versionId")

        if not key.lower().endswith(".pdf"):
            continue

        document_id = _document_id(bucket, key, version_id)
        source_url = _metadata_value(
            s3,
            bucket,
            key,
            "source-url",
            f"s3://{bucket}/{key}",
        )
        title = _metadata_value(
            s3,
            bucket,
            key,
            "title",
            Path(key).stem.replace("_", " ").title(),
        )
        access_level = _metadata_value(
            s3,
            bucket,
            key,
            "access-level",
            "PUBLIC",
        ).upper()

        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / Path(key).name

            response = s3.get_object(
                Bucket=bucket,
                Key=key,
                **({"VersionId": version_id} if version_id else {}),
            )

            pdf_path.write_bytes(response["Body"].read())
            checksum = hashlib.sha256(pdf_path.read_bytes()).hexdigest()

            markdown_path = ingest_pdf(
                pdf_path,
                Path(tmp) / "markdown",
                source_url=source_url,
                document_id=document_id,
                title=title,
                access_level=access_level,
                version=version_id or checksum[:12],
            )

            # Persist the canonical representation separately from the transient PDF workspace.
            canonical_dir = Path(
                os.getenv(
                    "CANONICAL_MARKDOWN_DIR",
                    "data/runtime/canonical_markdown",
                )
            )
            canonical_dir.mkdir(parents=True, exist_ok=True)

            canonical_path = canonical_dir / markdown_path.name
            canonical_path.write_text(
                markdown_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            document = load_markdown(canonical_path)
            chunks = chunk_document(document)
            index.add(chunks)

            dynamodb.put_item(
                TableName=settings.metadata_table,
                Item={
                    "doc_id": {"S": document_id},
                    "bucket": {"S": bucket},
                    "object_key": {"S": key},
                    "version_id": {"S": version_id or ""},
                    "sha256": {"S": checksum},
                    "content_type": {"S": "application/pdf"},
                    "markdown_key": {"S": str(canonical_path)},
                    "chunk_count": {"N": str(len(chunks))},
                    "status": {"S": "INDEXED"},
                },
            )

            processed += 1
            logger.info(
                "indexed doc_id=%s chunks=%d",
                document_id,
                len(chunks),
            )

    return processed


def run_once(index: HybridIndex | None = None) -> bool:
    sqs = _client("sqs")

    response = sqs.receive_message(
        QueueUrl=_queue_url(),
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10,
        VisibilityTimeout=300,
    )

    messages = response.get("Messages", [])

    if not messages:
        return False

    message = messages[0]

    try:
        process_message(message, index)
    except Exception:
        logger.exception("ingestion failed; SQS message will retry")
        return False

    sqs.delete_message(
        QueueUrl=_queue_url(),
        ReceiptHandle=message["ReceiptHandle"],
    )

    return True


def main() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    logger.info(
        "starting ingestion worker queue=%s index=%s",
        settings.sqs_queue,
        settings.index_path,
    )

    while True:
        run_once()


if __name__ == "__main__":
    main()