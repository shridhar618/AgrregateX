#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
scale=${1:-10000000}
python3 benchmarks/run.py "$scale"
python3 benchmarks/freshness.py "$scale"
python3 benchmarks/safety.py "$scale"
python3 benchmarks/growth.py
python3 benchmarks/report.py
