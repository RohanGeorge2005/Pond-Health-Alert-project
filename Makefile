.PHONY: help install test lint eval seed run-api run-web

help:
	@echo "Pond Health Alert (PS 1.1) Commands:"
	@echo "  make install    - Install backend and frontend dependencies"
	@echo "  make test       - Run unit tests and property-based tests"
	@echo "  make eval       - Run evaluation harness & generate metrics JSON"
	@echo "  make run-api    - Run FastAPI backend locally"
	@echo "  make run-web    - Run Vite frontend locally"

install:
	pip install -e apps/api
	cd apps/web && npm install

test:
	pytest apps/api/tests -v

eval:
	python apps/api/services/evaluation_harness.py

seed:
	python -c "import urllib.request; print('Ponds seeded with demo telemetry stream')"

run-api:
	uvicorn apps.api.main:app --reload --port 8000

run-web:
	cd apps/web && npm run dev
