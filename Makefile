.PHONY: up down migrate logs ps

# One-shot local setup + start: fills in blank secrets, brings up postgres_db
# and redis, waits for health, runs db_migrations, then starts the full stack.
up:
	./scripts/setup_db.sh
	docker compose up -d --build

down:
	docker compose down

# Re-run schema creation + app role/grants without restarting everything.
migrate:
	docker compose run --rm db_migrations

logs:
	docker compose logs -f web_api celery_worker celery_beat

ps:
	docker compose ps
