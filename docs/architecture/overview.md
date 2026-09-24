# Architecture and interview notes

## Reference architecture

The system separates source acquisition, durable ingestion, retrieval, reasoning, evidence validation and serving. The principal reliability boundary is S3 -> SQS -> worker: the API never waits for document conversion.

## Ingestion state machine

```text
UPLOADED
  -> EVENTED
  -> PROCESSING
  -> CONVERTED
  -> INDEXED
  -> ACKNOWLEDGED

failure at any processing stage
  -> message remains invisible until timeout
  -> SQS retry
  -> dead-letter queue after max receives
```

The source object's S3 version ID and SHA-256 checksum are recorded. The document ID is derived from bucket, key and version, which makes reprocessing deterministic and prevents accidental cross-version identity collisions.

## Retrieval

Local retrieval deliberately has two independent signals:

1. lexical retrieval through SQLite FTS5;
2. vector retrieval through deterministic feature-hashed embeddings.

Reciprocal rank fusion combines the candidate sets. A reranker then considers lexical overlap, vector score and query-term coverage. The `HybridIndex` interface is the local seam for an OpenSearch implementation.

The local vector implementation is a deterministic test/reference mechanism, not a semantic-model recommendation. Production can use an approved embedding provider and retain the same retrieval contract.

## Agent loop

The agent is a bounded state machine rather than an unconstrained autonomous process:

```text
classify
   |
   v
retrieve -> rerank -> authorize -> generate
                             |
                             v
                    citation validation
                             |
                             v
                     claim validation
                             |
                             v
                     relevance/confidence
                       /             \
                   pass             fail
                    |                 |
                  answer        broaden/retry
                                      |
                                  max attempts
                                      |
                                    refuse
```

The retry policy changes the search plan instead of blindly repeating the same retrieval call. This is the key difference between a validation loop and a simple single-pass RAG chain.

## Security boundary

Authorization is applied before final context construction. A public request can only receive PUBLIC chunks. INTERNAL and RESTRICTED access levels can be enabled by an authenticated application identity in a production adapter; this repository uses an explicit request field solely to demonstrate the boundary.

A real deployment should derive authorization from verified identity and policy claims rather than trusting a client-supplied access level.

## Evidence gates

Three independent checks are intentionally retained:

- citation integrity: referenced evidence IDs must exist in the generated context;
- claim support: factual claims are compared with cited evidence, including numeric/time checks;
- answer relevance: the answer must preserve question-specific terms and remain grounded in evidence.

A valid citation alone is not treated as proof of correctness.

## Production evolution

| Concern | Local reference | Production direction |
|---|---|---|
| Source storage | LocalStack S3 | S3 with lifecycle/versioning/encryption |
| Eventing | LocalStack SQS | SQS with DLQ, alarms, encryption |
| Worker | Docker | ECS/Fargate or equivalent |
| Metadata | LocalStack DynamoDB | DynamoDB with IAM least privilege |
| Search | SQLite FTS5 + hashed vectors | OpenSearch/vector service |
| LLM | deterministic / Bedrock | Bedrock model gateway + approved model catalog |
| Secrets | LocalStack Secrets Manager | Secrets Manager/KMS |
| Telemetry | structured logs | CloudWatch + OpenTelemetry |
| Evaluation | local JSON harness | CI regression + offline/online evaluation pipeline |

## Interview discussion points

- Why use SQS rather than a direct synchronous S3 trigger? It absorbs bursts and gives retry/DLQ semantics.
- Why a container worker rather than Lambda for the entire document path? PDFs can be large, conversion can be CPU/memory intensive, and the same worker boundary maps cleanly to ECS/Fargate.
- Why keep provenance on every chunk? Retrieval is not enough; the answer needs lineage back to a versioned source artifact.
- Why validate claims after generation? A model can produce a fluent answer that cites a related but non-supporting chunk.
- Why retry only once? Agentic flexibility needs a deterministic upper bound on latency and model/search cost.
- Why not provision OpenSearch locally? The local implementation should minimize infrastructure while preserving the production interface. A service should not be provisioned merely to make an architecture diagram look more impressive.
