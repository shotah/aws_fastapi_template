.SILENT: # Disable echo of commands
ifneq ("$(wildcard .env)", "")
# Import .env file if it exists
# MAKE SURE THIS IS SPACES AND NOT A TAB
    include .env
endif

SHELL := /bin/bash
export

PIPENV_IGNORE_VIRTUALENVS=1
export AWS_SAM_STACK_NAME=template-app
INTEGRATION_DIR = ./integration_tests

.DEFAULT_GOAL := help

PHONY: help
help: ## Show this help message
	@echo ""
	@echo "AWS Lambda SAM Template - Available Commands"
	@echo "============================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install-dev     Install all dependencies (including dev)"
	@echo "  make install         Install production dependencies only"
	@echo "  make hooks           Install git pre-commit hooks"
	@echo "  make env             Create local env.json from example"
	@echo "  make sync-dev        Sync all dependencies from Pipfile.lock"
	@echo ""
	@echo "Development:"
	@echo "  make lint            Run all linters (black, isort, flake8)"
	@echo "  make test            Run all tests with coverage"
	@echo "  make test-failed     Re-run only failed tests"
	@echo ""
	@echo "Local Testing:"
	@echo "  make build           Build SAM application in container"
	@echo "  make start           Start local API Gateway (requires Docker)"
	@echo "  make invoke          Invoke Lambda function locally"
	@echo ""
	@echo "AWS Deployment:"
	@echo "  make aws-check       Check AWS credentials configuration"
	@echo "  make deploy          Deploy to AWS (interactive)"
	@echo "  make deploy-ci       Deploy to AWS (non-interactive, for CI/CD)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean           Clean build artifacts and virtual env"
	@echo "  make all             Run full setup (hooks, install, lint, test)"
	@echo ""
	@echo "Quick Start:"
	@echo "  1. make install-dev"
	@echo "  2. make env          (optional, for local environment variables)"
	@echo "  3. make test"
	@echo "  4. make start"
	@echo ""

PHONY: all
all: hooks install-dev lint test ## Run full setup: hooks, install, lint, and test

PHONY: aws-check
aws-check: ## Check AWS credentials configuration
	@echo "Checking AWS credentials..."
	@aws sts get-caller-identity > /dev/null 2>&1 && \
		echo "✓ AWS credentials configured" && \
		aws sts get-caller-identity || \
		(echo "✗ AWS credentials not configured" && \
		 echo "" && \
		 echo "To configure AWS credentials, run:" && \
		 echo "  aws configure" && \
		 echo "" && \
		 echo "Or set environment variables:" && \
		 echo "  export AWS_ACCESS_KEY_ID=your_access_key" && \
		 echo "  export AWS_SECRET_ACCESS_KEY=your_secret_key" && \
		 echo "  export AWS_DEFAULT_REGION=us-east-1" && \
		 exit 1)

PHONY: clean
clean: ## Clean build artifacts and remove virtual environment
	rm -rf .aws-sam
	pipenv run python -c "import os; os.remove('requirements.txt')" || echo "no requirements.txt to remove"
	pipenv run python -c "import os; os.remove('Pipfile.lock')" || echo "no lock file to remove"
	pipenv --rm || echo "no environment found to remove"

PHONY: hooks
hooks: ## Install git pre-commit hooks
	pip install pre-commit
	pre-commit install || echo "pre-commit hooks already installed"

PHONY: env
env: ## Create local env.json from example (if not exists)
	@if not exist env.json (copy env.json.example env.json && echo "Created env.json from example. Edit it with your local values.") else (echo "env.json already exists. Use env.json.example as reference.")

PHONY: install
install: ## Install production dependencies only
	pipenv install

PHONY: install-dev
install-dev: ## Install all dependencies (including dev)
	pipenv install --dev

PHONY: sync
sync: ## Sync production dependencies from Pipfile.lock
	pipenv sync

PHONY: sync-dev
sync-dev: ## Sync all dependencies from Pipfile.lock (including dev)
	pipenv sync --dev

PHONY: lint
lint: ## Run all linters (black, isort, flake8, etc)
	pre-commit run --all-files

PHONY: test
test: ## Run all tests with coverage
	pipenv run pytest --new-first

PHONY: test-failed
test-failed: ## Re-run only failed tests
	pipenv run pytest --last-failed --exitfirst

PHONY: build
build: ## Build SAM application in container
	pipenv run pip freeze > requirements.txt
	sam build -c --use-container

PHONY: start
start: build ## Start local API Gateway (requires Docker)
	@test -f env.json && sam local start-api --env-vars env.json || sam local start-api

PHONY: invoke
invoke: build ## Invoke Lambda function locally with test event (Broken in Make, but works in CLI)
	sam local invoke --event events/hello.json HelloWorldFunction

PHONY: deploy
deploy: build aws-check ## Deploy to AWS (requires AWS credentials)
	sam deploy --guided

PHONY: deploy-ci
deploy-ci: build ## Deploy to AWS without prompts (for CI/CD)
	sam deploy --no-confirm-changeset --no-fail-on-empty-changeset
