# Portable for Git Bash / WSL / macOS / Linux (CI). Windows users: run the
# underlying commands from the README quickstart (PowerShell) instead of make.

PY        ?= python3
VENV_BIN  := $(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts,.venv/bin)

.PHONY: install seed reset-demo api web dev test lint docker-build docker-up tf-plan

install:
	$(PY) -m venv .venv
	$(VENV_BIN)/python -m pip install --upgrade pip
	$(VENV_BIN)/pip install -r app/requirements.txt
	cd web && npm install

seed:
	$(VENV_BIN)/python scripts/seed_demo.py

reset-demo:
	$(VENV_BIN)/python scripts/reset_demo.py

api:
	$(VENV_BIN)/uvicorn app.main:app --reload --port 8000

web:
	cd web && npm run dev

# Prefer two terminals (make api / make web); -j2 works in Git Bash/WSL.
dev:
	$(MAKE) -j2 api web

test:
	$(VENV_BIN)/python -m pytest tests/ -q

lint:
	$(VENV_BIN)/python -m ruff check app tests scripts

docker-build:
	docker build -f Dockerfile.api -t prometheus-api .
	docker build -f Dockerfile.web -t prometheus-web .

docker-up:
	docker compose up -d --build

tf-plan:
	@command -v terraform >/dev/null 2>&1 || { echo "terraform not found. Install via https://developer.hashicorp.com/terraform/downloads or 'choco install terraform'."; exit 1; }
	cd infra && terraform fmt -check && terraform validate && terraform plan -var enable_aws=false
