#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/wait.py
python3 benchmarks/functional.py
if [[ "${1:-}" == --full ]]; then
 count=$(podman exec agrregatex-postgres-1 psql -At -U agrregatex_owner -d agrregatex -c 'select count(*) from orders;')
 if [[ "$count" -lt 1000000 ]]; then python3 generator/load.py 1000000 10; fi
 if [[ "$count" -le 1000000 ]]; then
  python3 benchmarks/run.py 1000000
  python3 benchmarks/freshness.py 1000000
  python3 benchmarks/safety.py 1000000
  python3 generator/load.py 10000000 100
 elif [[ ! -f benchmarks/results/benchmark-1000000.json || ! -f benchmarks/results/safety-1000000.json ]]; then
  printf 'BLOCKED: already above 1M, no saved 1M evidence. Preserve data; use separate small-scale test DB.\n' >&2
  exit 2
 fi
 python3 benchmarks/run.py 10000000
 python3 benchmarks/freshness.py 10000000
 python3 benchmarks/safety.py 10000000
 python3 benchmarks/growth.py
 python3 benchmarks/security.py
 python3 benchmarks/reliability.py
fi
python3 benchmarks/report.py
