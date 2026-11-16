.PHONY: up down logs test lint migrate simulate clean

up:
	docker-compose up --build -d

down:
	docker-compose down

logs:
	docker-compose logs -f api worker

migrate:
	docker-compose exec api alembic revision --autogenerate -m "auto_migration"
	docker-compose exec api alembic upgrade head

test:
	pytest -v --tb=short

lint:
	ruff check app/ tests/ scripts/
	ruff format --check app/ tests/ scripts/

simulate:
	python scripts/simulate_fleet.py --machines 20 --cycles 40 --workers 12

clean:
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} +
