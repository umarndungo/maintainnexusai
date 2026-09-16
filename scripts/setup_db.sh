#!/usr/bin/env bash
# Bring up Postgres + Redis via docker-compose.yml and run the one-shot
# db_migrations job, which creates the schema, seeds missing demo credentials,
# creates the APP_DB_USER app role, and applies its least-privilege grants (see
# database/run_migrations.py and database/seed_credentials.py). This script
# does not duplicate that work — it just gets Compose's own services to run it
# once in the right order with a valid .env.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="$ROOT_DIR/.env"

if command -v docker compose >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  DC=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  DC=(docker-compose)
else
  echo "error: neither 'docker compose' nor 'docker-compose' is available" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "No .env found; creating one from .env.example"
  cp "$ROOT_DIR/.env.example" "$ENV_FILE"
fi

# shellcheck disable=SC1090
gen_secret() { openssl rand -base64 32 | tr -d '\n'; }

get_var() { grep -E "^${1}=" "$ENV_FILE" | tail -n1 | cut -d'=' -f2-; }

set_var() {
  local key="$1" value="$2"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    sed -i.bak "s|^${key}=.*|${key}=${value}|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

# Fail fast on any secret that must be non-default/non-empty; fill it in
# with a fresh random value instead of guessing what the user wants.
for key in POSTGRES_PASSWORD APP_DB_PASSWORD AUTH_SECRET INTERNAL_SERVICE_TOKEN; do
  current="$(get_var "$key" || true)"
  if [[ -z "$current" ]]; then
    generated="$(gen_secret)"
    set_var "$key" "$generated"
    echo "Generated a random value for $key in .env (it was empty)."
  fi
done

echo "Starting postgres_db and redis..."
"${DC[@]}" up -d postgres_db redis

echo "Waiting for postgres_db to become healthy..."
for _ in $(seq 1 30); do
  status="$("${DC[@]}" ps postgres_db --format '{{.Health}}' 2>/dev/null || true)"
  if [[ "$status" == "healthy" ]]; then
    break
  fi
  sleep 2
done
if [[ "$status" != "healthy" ]]; then
  echo "error: postgres_db did not become healthy in time" >&2
  "${DC[@]}" logs postgres_db | tail -n 50 >&2
  exit 1
fi

echo "Running schema migrations, credential seed, and app role/grants..."
"${DC[@]}" run --rm --build db_migrations

echo
echo "Done. Database, seeded credentials, app user, and permissions are set up."
echo "Bring up the rest of the stack with: ${DC[*]} up -d"
