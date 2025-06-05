#!/usr/bin/env bash
set -euo pipefail

# Read connection details from environment or fall back to defaults
DB_HOST="${DB_HOST-localhost}"
DB_PORT="${DB_PORT-5432}"
DB_NAME="${DB_NAME-collabtool}"
DB_USER="${DB_USER-$USER}"

echo "► Running migrations on $DB_NAME@$DB_HOST:$DB_PORT as $DB_USER"

APPLIED_TABLE="schema_migrations"
psql "host=$DB_HOST port=$DB_PORT user=$DB_USER dbname=$DB_NAME" -v ON_ERROR_STOP=1 <<'EOSQL'
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT now()
);
EOSQL

for file in $(ls -1 db/migrations/*.sql | sort); do
  ver=$(basename "$file" .sql)
  already=$(psql "host=$DB_HOST port=$DB_PORT user=$DB_USER dbname=$DB_NAME" -tAc \
                "SELECT 1 FROM schema_migrations WHERE version='$ver'")
  if [[ "$already" == "1" ]]; then
    echo "✓ $ver already applied"
  else
    echo "→ applying $ver"
    psql "host=$DB_HOST port=$DB_PORT user=$DB_USER dbname=$DB_NAME"      \
         -v ON_ERROR_STOP=1 -f "$file"
    psql "host=$DB_HOST port=$DB_PORT user=$DB_USER dbname=$DB_NAME"      \
         -c "INSERT INTO schema_migrations(version) VALUES('$ver')"
  fi
done

echo "✔ All migrations applied."
