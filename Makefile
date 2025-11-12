.PHONY: help dev up down build test lint format clean install check-all security-check

# Default target
help:
	@echo "Satellite Imagery API - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  dev         - Run development server with auto-reload"
	@echo "  dev-full    - Start services in Docker, then run dev server locally"
	@echo "  install     - Install Python dependencies"
	@echo "  install-dev - Install development dependencies"
	@echo ""
	@echo "Docker Services:"
	@echo "  services-up   - Start only DB and Redis in Docker"
	@echo "  services-down - Stop DB and Redis"
	@echo "  services-restart - Restart DB and Redis"
	@echo ""
	@echo "Docker (Full):"
	@echo "  up          - Start all services with Docker Compose"
	@echo "  down        - Stop all services"
	@echo "  build       - Build Docker images"
	@echo "  clean       - Clean up Docker resources"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  test        - Run tests with coverage"
	@echo "  test-fast   - Run tests without coverage (faster)"
	@echo "  lint        - Run all linting checks"
	@echo "  format      - Auto-format code"
	@echo "  check-all   - Run lint, format, and tests"
	@echo "  security    - Run security checks"
	@echo ""
	@echo "Utilities:"
	@echo "  clean-cache - Clean Python cache files"
	@echo "  requirements - Update requirements.txt from current environment"

# Development
dev:
	@echo "Starting development server..."
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app/

dev-full:
	@echo "Starting services and development server..."
	@make services-up
	@echo ""
	@echo "Starting development server..."
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app/

worker:
	@echo "Starting Arq worker..."
	arq app.workers.worker.WorkerConfig

worker-dev:
	@echo "Starting Arq worker with watch..."
	watchmedo auto-restart --pattern="*.py" --recursive --signal SIGTERM arq app.workers.worker.WorkerConfig

# Docker operations
services-up:
	@echo "Starting database and redis services..."
	docker-compose up -d db redis
	@echo "Waiting for services to be ready..."
	@sleep 3
	@echo "Services are running!"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Redis: localhost:6379"

services-down:
	@echo "Stopping database and redis services..."
	docker-compose stop db redis

services-restart:
	@make services-down
	@make services-up

up:
	@echo "Starting all services (including API)..."
	docker-compose up -d

down:
	@echo "Stopping all services..."
	docker-compose down

build:
	@echo "Building Docker images..."
	docker-compose build

# Testing and quality
test:
	@echo "Running tests with coverage..."
	pytest --cov=app --cov-report=term-missing --cov-report=html -v

test-fast:
	@echo "Running tests (fast mode)..."
	pytest -v

lint:
	@echo "Running linting checks..."
	@echo "  Black formatting check..."
	black --check .
	@echo "  Import sorting check..."
	isort --check-only .
	@echo "  Flake8 style check..."
	flake8 . --max-line-length=88 --extend-ignore=E203,W503 --exclude=venv/
	@echo "  Type checking with mypy..."
	mypy app/ --ignore-missing-imports --no-strict-optional
	@echo "All linting checks passed!"

format:
	@echo "Auto-formatting code..."
	black .
	isort .
	@echo "Code formatted!"

check-all: lint format test
	@echo "All checks completed successfully!"

security-check:
	@echo "Running security checks..."
	@echo "  Bandit security scan..."
	bandit -r app/ -f json -o bandit-report.json || true
	@echo "  Checking for secrets..."
	@if command -v trufflehog >/dev/null 2>&1; then \
		trufflehog --only-verified --json . > trufflehog-report.json || true; \
	else \
		echo "TruffleHog not installed. Install with: pip install trufflehog"; \
	fi
	@echo "Security checks completed!"

# Utilities
clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v
	docker system prune -f

clean-cache:
	@echo "Cleaning Python cache..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cache cleaned!"

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

install-dev:
	@echo "Installing development dependencies..."
	pip install -r requirements.txt
	pip install flake8 black isort mypy bandit pytest pytest-cov pytest-asyncio
	@echo "Development dependencies installed!"

requirements:
	@echo "Updating requirements.txt..."
	pip freeze > requirements.txt
	@echo "requirements.txt updated!"

# Database operations (if you add them later)
db-upgrade:
	@echo "Upgrading database..."
	@if command -v alembic >/dev/null 2>&1; then \
		alembic upgrade head; \
	else \
		echo "Alembic not installed"; \
	fi

db-downgrade:
	@echo "Downgrading database..."
	@if command -v alembic >/dev/null 2>&1; then \
		alembic downgrade -1; \
	else \
		echo "Alembic not installed"; \
	fi

# Quick development workflow
quick-dev: install-dev format lint test
	@echo "Ready for development!"

# Pre-commit hook (run this before committing)
pre-commit: format lint test-fast
	@echo "Pre-commit checks passed! Ready to commit."

# Install pre-commit hooks
install-hooks:
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "Pre-commit hooks installed!"

# Run pre-commit on all files
pre-commit-all:
	@echo "Running pre-commit on all files..."
	pre-commit run --all-files
	@echo "Pre-commit checks completed!"
