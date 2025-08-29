.PHONY: help dev up down build test lint clean install

# Default target
help:
	@echo "Available commands:"
	@echo "  dev      - Run development server with auto-reload"
	@echo "  up       - Start all services with Docker Compose"
	@echo "  down     - Stop all services"
	@echo "  build    - Build Docker images"
	@echo "  test     - Run tests"
	@echo "  lint     - Run linting and formatting checks"
	@echo "  clean    - Clean up Docker resources"
	@echo "  install  - Install Python dependencies"

# Development
dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Docker operations
up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

# Testing and quality
test:
	pytest tests/ -v

lint:
	black app/ --check
	isort app/ --check-only
	flake8 app/

format:
	black app/
	isort app/

# Utilities
clean:
	docker-compose down -v
	docker system prune -f

install:
	pip install -r requirements.txt

# Database operations
db-upgrade:
	docker-compose exec api alembic upgrade head

db-downgrade:
	docker-compose exec api alembic downgrade -1