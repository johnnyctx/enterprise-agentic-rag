# Enterprise Agentic RAG

An enterprise-oriented, AWS-shaped reference implementation of an agentic RAG system. The repository is deliberately designed around replaceable interfaces, durable event boundaries, evidence validation, authorization-before-context, provenance, observability, and reproducible local integration testing.

> **Demonstration-corpus disclaimer:** the repository uses publicly available Vanguard materials only as a demonstration knowledge corpus. It does **not** represent Vanguard's internal systems, data, policies, architecture, controls, or production implementation.

## Architecture

```text
                 public PDF / enterprise document source
                                |
                                v
                         S3 object storage
                                |
                     ObjectCreated notification
                                v
                         SQS ingestion queue
                                |
                                v
                  containerized ingestion worker
                  |       |          |         |
                  |       |          |         +--> DynamoDB metadata
                  |       |          +------------> canonical Markdown
                  |       +-----------------------> SHA-256/provenance
                  +-------------------------------> structure-aware chunks
                                |
                                v
                  Hybrid retrieval index
                +---------------+---------------+
                |                               |
          lexical / FTS5                 vector / embeddings
                |                               |
                +---------------+---------------+
                                v
                         reciprocal rank fusion
                                |
                                v
                         authorization filter
                                |
                                v
                             reranker
                                |
                                v
                 bounded agentic orchestration loop
              route -> retrieve -> evaluate -> retry
                                |
                                v
                         LLM provider boundary
                    demo deterministic | Bedrock
                                |
                                v
                   citation + claim validation
                                |
                         answer relevance
                                |
                       confidence / refusal gate
                                |
                                v
                         FastAPI structured API
                                |
                                v
                         audit/observability
```

### AWS mapping

| Local reference | AWS production mapping | Purpose |
|---|---|---|
| LocalStack S3 | Amazon S3 | Raw source documents |
| LocalStack SQS | Amazon SQS | Durable ingestion boundary |
| Python worker container | ECS/Fargate worker | Long-running document processing |
| DynamoDB | Amazon DynamoDB | Document/provenance metadata |
| SQLite FTS5 + local vector index | OpenSearch / managed vector store | Hybrid retrieval |
| Deterministic LLM | Amazon Bedrock | Offline repeatability |
| FastAPI | ECS/Fargate/EKS/API Gateway | Query API |
| JSON audit logs | CloudWatch / OpenTelemetry | Operational telemetry |
| Secrets Manager resource | AWS Secrets Manager | Provider credentials/config |
| Terraform + tflocal | Terraform + AWS provider | Same infrastructure definition locally and in AWS |

The local vector implementation uses deterministic feature hashing so the complete pipeline works without downloading a model. It is intentionally an **embedding-provider boundary**, not a claim that feature hashing is the production semantic-embedding choice. A production implementation can replace the local vector adapter with Bedrock embeddings or another approved embedding service without changing orchestration contracts.

## Why the design is agentic

The agent is not simply `retrieve -> generate`. It has an explicit, bounded state machine:

1. classify the request;
2. create the first search plan;
3. retrieve using lexical + vector search;
4. fuse candidates and rerank;
5. apply authorization before context construction;
6. generate an answer with evidence markers;
7. validate citations, relevance, and claim support;
8. retry once with an expanded search plan when evidence is weak;
9. refuse when the evidence gate still fails;
10. emit an auditable trace.

The loop is bounded to prevent runaway agent behavior and uncontrolled cost/latency.

## Quick start: LocalStack + tflocal

Requirements:

- Python 3.14 (the reference runtime)
- Docker Desktop
- Terraform
- `tflocal`
- a LocalStack Hobby token for the current LocalStack image

Create the environment:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[pdf,dev]"
```

Set the local AWS credentials used by LocalStack:

```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export LOCALSTACK_AUTH_TOKEN='your-token'
```

Start LocalStack:

```bash
docker compose up -d localstack
```

Provision the infrastructure through Terraform/tflocal:

```bash
tflocal -chdir=infrastructure/terraform init
tflocal -chdir=infrastructure/terraform validate
tflocal -chdir=infrastructure/terraform plan
tflocal -chdir=infrastructure/terraform apply
```

Verify the AWS-shaped resources:

```bash
aws --endpoint-url=http://localhost:4566 s3 ls
aws --endpoint-url=http://localhost:4566 sqs list-queues
aws --endpoint-url=http://localhost:4566 dynamodb list-tables
aws --endpoint-url=http://localhost:4566 secretsmanager list-secrets
```

## End-to-end ingestion

The demonstration PDFs are not stored in Git. Download them from the URLs in `data/vanguard_public/pdf_manifest.json`:

```bash
python scripts/download_corpus.py
```

Publish the PDFs to S3. S3 notification configuration sends an event to SQS:

```bash
python scripts/upload_corpus.py
```

Start the worker:

```bash
docker compose up -d ingestion-worker
```

The worker:

- consumes SQS messages;
- downloads the exact S3 object/version;
- validates the PDF;
- converts PDF -> Markdown;
- attaches source URL, checksum, version and access metadata;
- persists canonical Markdown;
- chunks by document structure rather than arbitrary fixed windows;
- indexes the chunks;
- records metadata in DynamoDB;
- deletes the SQS message only after successful processing.

That final acknowledgement behavior is important: failures remain retryable instead of being silently acknowledged.

## Query API

Start the API:

```bash
docker compose up -d api
```

Health:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Query:

```bash
curl -s http://localhost:8000/query \
  -H 'content-type: application/json' \
  -d '{"query":"What are Vanguard’s principles for investing success?","access_level":"PUBLIC"}'
```

The response contains:

- answer;
- refusal status;
- confidence and confidence label;
- citations with document/section/source provenance;
- claim-level validation;
- agent attempts and ranked chunk IDs for debugging.

`debug` is intentionally useful for interview/demo inspection. A production API would normally gate detailed traces behind privileged diagnostics and avoid exposing internal implementation metadata to ordinary users.

## Offline development path

For unit/integration work where LocalStack and the public network are unnecessary, first run the PDF downloader so converted Markdown exists, then:

```bash
python scripts/seed_demo.py
uvicorn app.api.main:app --reload
```

This bypasses S3/SQS but exercises the same canonical Markdown, chunking, indexing, retrieval, validation and API layers.

## Bedrock provider

The default local provider is deterministic so tests are repeatable. For an AWS environment:

```bash
export LLM_PROVIDER=bedrock
export MODEL_NAME='your-approved-bedrock-model-id'
```

The `BedrockConverseLLM` adapter uses the Bedrock Converse API and preserves the same generator interface. The local orchestrator, evidence gates, and API contract do not need to change.

## Evaluation

The evaluation dataset intentionally matches the five-PDF demonstration corpus and includes refusal cases for information explicitly outside that corpus.

After indexing the corpus:

```bash
python scripts/evaluate.py
```

The harness reports per-question pass/fail, confidence, and final aggregate accuracy. For a production evaluation suite, extend this with golden answers, claim-level entailment labels, retrieval recall@k, MRR/nDCG, latency percentiles, token/cost accounting, and regression thresholds in CI.

## Tests and quality gates

```bash
python -m pytest -q
ruff check .
```

The test suite covers:

- PDF validation/normalization;
- provenance parsing;
- structure-aware chunking;
- ingestion-worker identity/idempotency behavior;
- lexical/vector hybrid retrieval;
- authorization filtering;
- citation validation;
- numeric/time claim contradiction detection;
- answer relevance;
- bounded retry/refusal behavior;
- FastAPI health/query behavior.

## Repository structure

```text
app/
  agents/             router + bounded agentic orchestrator
  api/                FastAPI API
  ingestion/          PDF conversion, provenance, chunking, S3/SQS worker
  index/              index package boundary
  llm/                deterministic + Bedrock provider adapters
  observability/      structured audit logging
  rag/                retrieval, reranking, citations, validation, confidence
  security/           authorization filtering

data/vanguard_public/
  pdf_manifest.json   authoritative public source URLs only

evaluation/           regression questions and metrics
infrastructure/       Terraform/tflocal AWS-shaped resources
localstack/            LocalStack bootstrap hook
scripts/               download, upload, seed, demo and evaluation workflows
tests/                 unit/integration tests
docs/architecture/     architecture and interview notes
```

## Engineering decisions

### Scalability

Document processing is separated from the API request path. SQS absorbs ingestion bursts; workers can scale independently. Retrieval is also isolated behind an index interface so a local single-node SQLite implementation can be replaced by a distributed managed search service.

### Reliability

S3 object versioning plus SHA-256 gives deterministic source identity. SQS visibility timeout and a dead-letter queue isolate poison messages. A message is acknowledged only after successful conversion, indexing and metadata persistence. The worker is safe to retry because indexing uses deterministic chunk IDs and upserts.

### Security and governance

Authorization is enforced before context reaches the generator. Source URLs, checksums, versions, access classification and conversion metadata travel with every chunk. The public demonstration corpus is explicitly separated from any claim about Vanguard internal information.

### Observability

Each request gets a correlation ID. Events record route, attempt, refusal and confidence decisions without logging credentials or raw document contents. Production mapping is CloudWatch/OpenTelemetry with metrics for retrieval quality, refusal rate, queue depth, processing failures, latency and cost.

### Maintainability

Provider boundaries are explicit: PDF conversion, index/retrieval, LLM generation, and infrastructure are replaceable. The orchestration layer depends on contracts rather than a specific model or search vendor.

### Cost and latency

The agent loop is bounded. Retrieval candidates are capped before reranking and context construction. Deterministic local generation is zero-model-cost for development; Bedrock can be introduced only where model generation adds value. Production should record token usage and latency by route and retry count.

## Important scope boundary

This is a **reference implementation for demonstrating enterprise RAG engineering patterns**. The Vanguard PDFs are public documents selected to make the ingestion and evidence pipeline concrete. Nothing in this repository should be presented in an interview as evidence of Vanguard's internal AWS architecture, internal agent architecture, proprietary controls, or production system design.
