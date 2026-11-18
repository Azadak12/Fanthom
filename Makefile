API_URL ?= http://localhost:8000

.PHONY: dev-api dev-web dev-worker check check-api check-web migrate migration seed export-seed gen-api e2e

dev-api:
	cd api && uv run fastapi dev app/main.py --port 8000

dev-web:
	cd web && pnpm dev

dev-worker:
	cd api && uv run python -m app.worker

check: check-api check-web

check-api:
	cd api && uv run ruff check . --quiet && uv run ruff format --check . --quiet && uv run mypy app && uv run pytest -q

check-web:
	cd web && pnpm typecheck && pnpm lint && pnpm test

migrate:
	cd api && uv run alembic upgrade head

migration:
	cd api && uv run alembic revision --autogenerate -m "$(m)"

seed:
	cd api && uv run python -m scripts.seed

export-seed:
	cd api && uv run python -m scripts.export_seed

gen-api:
	cd web && pnpm exec openapi-typescript $(API_URL)/openapi.json -o lib/api/schema.d.ts

e2e:
	cd web && pnpm e2e
