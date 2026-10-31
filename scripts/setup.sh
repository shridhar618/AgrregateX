#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
import pathlib,secrets,json
p=pathlib.Path('.env')
if not p.exists():
 p.write_text('DB_PASSWORD='+secrets.token_hex(24)+'\nAPI_DB_PASSWORD='+secrets.token_hex(24)+'\n');p.chmod(0o600)
p=pathlib.Path('.secrets.json')
if not p.exists():
 p.write_text(json.dumps({'admin':secrets.token_urlsafe(32),'tenants':{str(i):secrets.token_urlsafe(32) for i in range(1,101)}},indent=2));p.chmod(0o600)
PY
systemctl --user start podman.socket
docker compose -p agrregatex up -d --build
