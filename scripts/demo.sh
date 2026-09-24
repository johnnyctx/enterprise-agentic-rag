#!/usr/bin/env bash
set -euo pipefail

# 1) Start LocalStack.
docker compose up -d localstack

# 2) Provision AWS-shaped resources with the same Terraform used for AWS.
tflocal -chdir=infrastructure/terraform init
tflocal -chdir=infrastructure/terraform apply -auto-approve

# 3) Download the demonstration corpus and publish PDFs to S3.
python scripts/download_corpus.py
python scripts/upload_corpus.py

# 4) Start the durable worker and API. S3 notifications flow into SQS.
docker compose up -d ingestion-worker api

echo "API: http://localhost:8000/health"
echo "Try: curl -s http://localhost:8000/health"
