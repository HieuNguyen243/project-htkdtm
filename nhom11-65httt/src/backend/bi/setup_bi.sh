#!/usr/bin/env bash

set -Eeuo pipefail

cd "$(dirname "$0")"

trap 'echo "[ERROR] Setup failed at line $LINENO"' ERR

DB_DIR="../../database"

COMPOSE=(
    docker compose
    --env-file .env
    -f docker-compose.yml
    -f docker-compose.superset.yml
)

echo "======================================"
echo " PHONG TRO BI - AUTOMATIC SETUP"
echo "======================================"

# 1. Check environment
if [ ! -f .env ]; then
    echo "Missing .env file."
    echo "Copy .env.example to .env and configure passwords."
    exit 1
fi

docker info > /dev/null
"${COMPOSE[@]}" config --quiet

# 2. Prepare Python
echo "[1/9] Preparing Python environment..."

if [ ! -d .venv ]; then
    if command -v py >/dev/null 2>&1; then
        py -3.12 -m venv .venv
    else
        python3.12 -m venv .venv
    fi
fi

if [ -f .venv/Scripts/activate ]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

python -m pip install -r requirements.txt
python -m pip install -r superset/requirements.txt

# Validate required configuration without printing secrets
python - <<'PY'
from dotenv import dotenv_values

config = dotenv_values(".env")
required = [
    "POSTGRES_PASSWORD",
    "DB_PASSWORD",
    "BI_READER_PASSWORD",
    "SUPERSET_DB_PASSWORD",
    "SUPERSET_SECRET_KEY",
    "SUPERSET_PASSWORD",
    "SUPERSET_USER",
]

for key in required:
    value = config.get(key)
    if not value or value == "change_me":
        raise SystemExit(f"Please configure {key} in .env")
PY

# 3. Start PostgreSQL
echo "[2/9] Starting PostgreSQL..."

"${COMPOSE[@]}" up -d --wait postgres

psql_admin() {
    docker exec -i phongtro_bi_db \
        psql -U bi_admin \
        -d phongtro_bi_demo \
        -v ON_ERROR_STOP=1 "$@"
}

# 4. Initialize database
echo "[3/9] Checking database schema..."

SCHEMA_COUNT=$(psql_admin -Atc "
SELECT COUNT(*)
FROM information_schema.schemata
WHERE schema_name IN ('raw','core','audit','analytics');
")

if [ "$SCHEMA_COUNT" = "0" ]; then

    echo "Fresh database detected."

    # Apply all migrations in one transaction
    {
        cat "$DB_DIR/migrations/001_create_schema.sql"
        printf '\n'
        cat "$DB_DIR/migrations/002_create_tables.sql"
        printf '\n'
        cat "$DB_DIR/migrations/003_constraints_indexes.sql"
        printf '\n'
        cat "$DB_DIR/migrations/004_create_roles.sql"
        printf '\n'
    } | psql_admin --single-transaction

else

    echo "Existing database detected."
    echo "Skipping non-repeatable migrations."

fi

# Verify expected tables and roles
psql_admin <<'SQL'
DO $$
BEGIN
    IF to_regclass('audit.ingest_batch') IS NULL
       OR to_regclass('raw.staging_listing') IS NULL
       OR to_regclass('core.listing') IS NULL
       OR to_regclass('core.listing_snapshot') IS NULL
       OR to_regclass('audit.import_issue') IS NULL
       OR NOT EXISTS (
           SELECT 1 FROM pg_roles
           WHERE rolname = 'bi_importer'
       )
       OR NOT EXISTS (
           SELECT 1 FROM pg_roles
           WHERE rolname = 'bi_reader'
       )
    THEN
        RAISE EXCEPTION 'Incomplete database schema';
    END IF;
END
$$;
SQL

# 5. Configure database role passwords
echo "[4/9] Configuring database roles..."

python - <<'PY'
import subprocess
from dotenv import dotenv_values

config = dotenv_values(".env")

def literal(value):
    return "'" + value.replace("'", "''") + "'"

sql = (
    "SET standard_conforming_strings = on;\n"
    "ALTER ROLE bi_importer PASSWORD "
    + literal(config["DB_PASSWORD"]) + ";\n"
    "ALTER ROLE bi_reader PASSWORD "
    + literal(config["BI_READER_PASSWORD"]) + ";\n"
)

subprocess.run(
    [
        "docker", "exec", "-i", "phongtro_bi_db",
        "psql", "-U", "bi_admin",
        "-d", "phongtro_bi_demo",
        "-v", "ON_ERROR_STOP=1"
    ],
    input=sql.encode("utf-8"),
    check=True
)
PY

# 6. Import synthetic test data
echo "[5/9] Importing demo data..."

python -m importer.import_data \
    --file tests/fixtures/B001/listings.csv \
    --manifest tests/fixtures/B001/manifest.json \
    --batch B001

python -m importer.import_data \
    --file tests/fixtures/B002/listings.csv \
    --manifest tests/fixtures/B002/manifest.json \
    --batch B002

# 7. Create analytics views
echo "[6/9] Creating analytics views..."

for view in \
    vw_listing_current \
    vw_market_price \
    vw_affordability \
    vw_listing_quality \
    vw_import_batch_quality
do
    psql_admin < "$DB_DIR/views/$view.sql"
done

psql_admin < "$DB_DIR/validation/check_database.sql"
psql_admin < "$DB_DIR/validation/check_analytics.sql"

# 8. Build and initialize Superset
echo "[7/9] Preparing Superset..."

"${COMPOSE[@]}" build superset_bi
"${COMPOSE[@]}" up -d --wait superset_meta

"${COMPOSE[@]}" run --rm -T \
    superset_bi superset db upgrade

# Initialize Superset roles
echo "Initializing Superset roles..."

"${COMPOSE[@]}" run --rm -T \
    superset_bi superset init

# Automatically create admin account
echo "Checking Superset admin account..."

python - <<'PY'
import json
import subprocess
from pathlib import Path
from dotenv import dotenv_values

config = dotenv_values(".env")

username = config.get("SUPERSET_USER", "admin")
password = config.get("SUPERSET_PASSWORD")

if not password or password == "change_me":
    raise SystemExit(
        "Please configure SUPERSET_PASSWORD in .env"
    )

payload = json.dumps({
    "username": username,
    "password": password,
})

script = Path("superset/init_admin.py").read_text(
    encoding="utf-8"
)

command = [
    "docker", "compose",
    "--env-file", ".env",
    "-f", "docker-compose.yml",
    "-f", "docker-compose.superset.yml",
    "run", "--rm", "-T",
    "superset_bi",
    "/app/.venv/bin/python",
    "-c", script,
]

subprocess.run(
    command,
    input=payload.encode("utf-8"),
    check=True,
)
PY

"${COMPOSE[@]}" up -d superset_bi

# 9. Wait for Superset
echo "[8/9] Waiting for Superset..."

READY=0

for attempt in $(seq 1 60); do
    if curl -fsS http://localhost:8089/health \
        >/dev/null 2>&1; then
        READY=1
        break
    fi
    sleep 5
done

if [ "$READY" != "1" ]; then
    echo "Superset startup timed out."
    "${COMPOSE[@]}" logs --tail 50 superset_bi
    exit 1
fi

# 10. Build dashboards
echo "[9/9] Creating BI dashboards..."

python superset/build_dashboards.py \
    --url http://localhost:8089 \
    --user admin \
    --bootstrap

echo "======================================"
echo " BI SETUP COMPLETED"
echo "======================================"
echo "Superset: http://localhost:8089"
echo "Market:"
echo "http://localhost:8089/superset/dashboard/phongtro-market/"
echo "Affordability:"
echo "http://localhost:8089/superset/dashboard/phongtro-affordability/"
echo "Quality:"
echo "http://localhost:8089/superset/dashboard/phongtro-quality/"
echo "Data origin: SYNTHETIC DEMO"
