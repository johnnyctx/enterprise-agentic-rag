# Architecture Notes

The reference separates routing, authorization, retrieval, reranking, generation,
citation validation, answer relevance, claim support, contradiction detection,
confidence, and audit logging.

The agent loop is bounded and inspectable. `tflocal` is used to exercise Terraform
against LocalStack. Production adapters can replace the demo LLM and in-memory store
with Bedrock and a managed search/vector platform.

A citation being valid is not itself proof that the answer is correct.


## Document ingestion and PDF normalization

A heterogeneous enterprise corpus should be normalized before retrieval. For PDF sources the
reference implementation makes the transformation explicit:

`PDF -> PyMuPDF4LLM -> Markdown -> provenance metadata -> chunking -> indexing`

The PDF manifest contains five public Vanguard sources selected to exercise different document
shapes: a research guide, an investing-principles paper, a multi-page schedule, and tax reference
documents. The downloader is intentionally runtime-based. This keeps the Git repository small and
reproducible while preserving authoritative source URLs and document lineage.

Every converted artifact records a SHA-256 checksum of the source PDF, source URL, retrieval time,
conversion engine, document ID, and access level. That metadata supports lineage, idempotency,
reprocessing, auditability, and later rollback/version comparisons.

## Public demonstration corpus

The Vanguard corpus is demonstration data sourced from public Vanguard documents.
`data/vanguard_public/pdf_manifest.json` is the source acquisition manifest.
The ingestion workflow downloads the PDFs, records provenance and SHA-256 checksums,
converts PDFs to Markdown, and then passes the normalized documents into chunking
and retrieval. The public corpus does not represent Vanguard internal systems,
data, policies, or production architecture.
