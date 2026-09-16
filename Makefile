.PHONY: up down migrate seed logs ps

# One-shot local setup + start: fills in blank secrets, brings up postgres_db
# and redis, then runs migration + credential seeding once before starting the
# application services. --no-deps prevents Compose from repeating the job.
up:
	./scripts/setup_db.sh
	docker compose up -d --build --no-deps web_api web celery_worker celery_beat

down:
	docker compose down

# Re-run schema creation + app role/grants without restarting everything.
migrate:
	docker compose run --rm db_migrations

# Seed any missing demo staff credentials without changing existing passwords.
seed:
	docker compose run --rm db_migrations python -m database.seed_credentials

logs:
	docker compose logs -f web_api celery_worker celery_beat

ps:
	docker compose ps
