.PHONY: help install dev test lint ingest docker-build docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install      Install backend and frontend dependencies"
	@echo "  make test         Run backend (pytest) and frontend (vitest) test suites"
	@echo "  make lint         Run Ruff Python linter and ESLint"
	@echo "  make ingest       Fetch and rebuild clean SQLite database from Elexon BMRS API"
	@echo "  make docker-build Build Docker images for backend and frontend"
	@echo "  make docker-up    Start entire application stack using Docker Compose"
	@echo "  make docker-down  Stop Docker containers"

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

test:
	python -m pytest backend/tests -v
	cd frontend && npm test

lint:
	ruff check backend
	cd frontend && npm run lint

ingest:
	python -m backend.ingest.build_dataset

docker-build:
	docker compose build

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
