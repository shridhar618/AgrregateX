#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -p agrregatex restart
python3 scripts/wait.py
