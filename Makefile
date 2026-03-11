.PHONY: help setup scaffold dev test clean

help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Setup: create venv and install deps
	uv venv --python 3.13
	uv sync
	@echo ""
	@echo "Setup complete!"

scaffold: ## Create a new agent from this boilerplate
	python scripts/create_agent.py

dev: ## Start agent
	uv sync
	uv run uvicorn app.main:app --host 0.0.0.0 --port 9201

test: ## Run tests
	uv run --extra dev pytest tests/ -v

clean: ## Clean caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
