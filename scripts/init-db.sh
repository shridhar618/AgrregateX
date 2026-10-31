#!/usr/bin/env bash
set -euo pipefail
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" --set api_password="$API_DB_PASSWORD" <<'SQL'
CREATE ROLE agrregatex_api LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD :'api_password';
SQL
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /agrregatex/schema.sql
