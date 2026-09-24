import json

from app.ingestion.worker import _document_id, _parse_s3_records


def test_document_id_is_deterministic():
    assert _document_id("bucket", "documents/example.pdf", "v1") == _document_id("bucket", "documents/example.pdf", "v1")


def test_document_id_changes_with_version():
    assert _document_id("bucket", "documents/example.pdf", "v1") != _document_id("bucket", "documents/example.pdf", "v2")


def test_parse_s3_records():
    body = json.dumps({"Records": [{"eventSource": "aws:s3", "s3": {"bucket": {"name": "b"}, "object": {"key": "a.pdf"}}}]})
    assert _parse_s3_records(body)[0]["s3"]["object"]["key"] == "a.pdf"
