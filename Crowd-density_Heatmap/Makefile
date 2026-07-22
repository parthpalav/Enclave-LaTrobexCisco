.PHONY: help install backend frontend test lint up down logs clean

help:
	@echo "CrowdVision Heatmap Engine — common tasks"
	@echo "  make install     Install backend + frontend deps"
	@echo "  make backend     Run the FastAPI backend (dev, reload)"
	@echo "  make frontend    Run the Vite dev server"
	@echo "  make test        Run backend tests"
	@echo "  make lint        Ruff lint the backend"
	@echo "  make up          docker compose up (full stack)"
	@echo "  make down        docker compose down"
	@echo "  make logs        Tail compose logs"

install:
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	cd frontend && npm install

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && . .venv/bin/activate && pytest -q

lint:
	cd backend && . .venv/bin/activate && ruff check app

up:
	docker compose -f docker/docker-compose.yml up --build

down:
	docker compose -f docker/docker-compose.yml down

logs:
	docker compose -f docker/docker-compose.yml logs -f

clean:
	rm -rf backend/.venv backend/.venv-test frontend/node_modules frontend/dist
	find . -type d -name __pycache__ -exec rm -rf {} +
