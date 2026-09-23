# Enterprise Agentic RAG

Enterprise-oriented reference implementation for agentic RAG, evidence validation,
authorization-aware retrieval, AWS-style infrastructure, LocalStack integration,
Terraform/tflocal, observability, and evaluation.

> **Disclaimer:** This project uses publicly available Vanguard materials solely as a
> demonstration knowledge corpus. It does not represent Vanguard's internal systems,
> data, policies, architecture, or production implementation.

## Flow

```text
User -> FastAPI -> Query Router -> Agent Orchestrator
     -> Authorization -> Hybrid Retrieval -> Rerank -> Context
     -> LLM -> Citation Validation -> Answer Relevance
     -> Claim Support/Contradiction -> Confidence Gate
     -> Answer / Refuse -> Audit
```

## Local setup

Requirements: Python 3.11+, Docker, Terraform, and `tflocal`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[pdf,dev]"
docker compose up -d
tflocal -chdir=infrastructure/terraform init
tflocal -chdir=infrastructure/terraform apply -auto-approve
python scripts/seed_demo.py
uvicorn app.api.main:app --reload
```

Query:
```bash
curl -X POST http://localhost:8000/query   -H 'content-type: application/json'   -d '{"query":"What are the three keys to investing?","access_level":"PUBLIC"}'
```

Tests:
```bash
pytest
python scripts/evaluate.py
```


## PDF -> Markdown ingestion

PDF conversion is a first-class part of the ingestion path, not a README-only concept. The
project includes a manifest of five public Vanguard PDF sources. The repository stores their
authoritative URLs and metadata; the full PDFs are downloaded at runtime so the repo does not
redistribute third-party documents.

The executable path is:

```text
Vanguard PDF
    |
    v
Download / source acquisition
    |
    v
PDF -> Markdown (PyMuPDF4LLM)
    |
    v
Normalize Markdown
    |
    v
Metadata + SHA-256 + provenance
    |
    v
Chunking
    |
    v
Embedding / hybrid index
    |
    v
Agentic RAG retrieval
```

Run the PDF pipeline with:

```bash
pip install -e ".[pdf,dev]"
python scripts/download_and_ingest_pdfs.py
```

The script downloads the PDFs into `data/vanguard_public/source_pdfs/`, converts them into
`data/vanguard_public/converted_markdown/`, and writes provenance front matter containing the
source URL, retrieval timestamp, SHA-256 checksum, conversion engine, and access classification.

The selected public sources include Vanguard's financial wellness guide, Principles for Investing
Success, the 2026 dividend schedule, U.S. government obligations income information, and 2026
foreign tax credit information.

`app/ingestion/pdf_to_markdown.py` is intentionally isolated behind `pdf_to_markdown()` so a
production deployment can replace PyMuPDF4LLM with a managed document-AI/OCR service without
changing downstream chunking and RAG interfaces.

## Key design principles

* Retrieval and citation validity are not treated as proof of answer correctness.
* Claim-level validation catches unsupported and contradictory numeric/time claims.
* Authorization is applied before final context construction.
* Agent loops are bounded and inspectable.
* LocalStack + tflocal provide an AWS-like integration environment.
* Interfaces are replaceable for Bedrock, OpenSearch/vector stores, SQS/Lambda/ECS,
  Secrets Manager, CloudWatch, and OpenTelemetry-compatible telemetry.

## Layout

```text
app/
  agents/          routing and orchestration
  api/             FastAPI
  ingestion/       loading and chunking
  rag/             retrieval, citations, validation, confidence
  security/        authorization
  observability/   audit logging
infrastructure/terraform/
data/vanguard_public/
evaluation/
tests/
scripts/
localstack/init/
docs/architecture/
```

## Public corpus provenance

The `data/vanguard_public/` directory is no longer dummy data. It contains curated,
source-backed snapshots of current publicly accessible Vanguard pages, with the
authoritative URL and retrieval date embedded in every document and a `pdf_manifest.json`
catalog.

Run `python scripts/fetch_corpus.py` when network access is available to refresh raw
HTML copies under `data/vanguard_public/raw/`. The curated snapshots are intentionally
kept stable for reproducible evaluation.

The corpus currently covers:
- How to invest
- How to open an account
- How to buy an ETF
- Investment accounts
- Personal investor privacy notice
- What is an ETF?
