#!/usr/bin/env bash
set -euo pipefail
docker compose up -d
tflocal -chdir=infrastructure/terraform init
tflocal -chdir=infrastructure/terraform apply -auto-approve
python scripts/seed_demo.py
uvicorn app.api.main:app --host 0.0.0.0 --port 8000
