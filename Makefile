.PHONY: help setup up down build migrate test clean

help:
	@echo "Director Media Monitoring - Makefile"
	@echo ""
	@echo "Commands:"
	@echo "  make setup      - Initial setup (create .env, build images)"
	@echo "  make up         - Start all services"
	@echo "  make down       - Stop all services"
	@echo "  make build      - Build Docker images"
	@echo "  make migrate    - Run database migrations"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean up containers and volumes"

setup:
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@mkdir -p storage
	@docker compose build

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

migrate:
	docker compose exec api alembic upgrade head

test:
	docker compose exec api pytest tests/

clean:
	docker compose down -v
	rm -rf storage/*

