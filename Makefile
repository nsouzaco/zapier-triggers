.PHONY: help install test lint format clean run worker migrate docker-up docker-down test-api test-api-local

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements-dev.txt

test: ## Run tests
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-fast: ## Run tests without coverage
	pytest tests/ -v

lint: ## Run linters
	flake8 app tests
	mypy app

format: ## Format code
	black app tests
	isort app tests

clean: ## Clean up generated files
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

run: ## Run the development server
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-port: ## Run the development server on a custom port (usage: make run-port PORT=8001)
	uvicorn app.main:app --reload --host 0.0.0.0 --port $(or $(PORT),8001)

stop: ## Stop any running uvicorn process on port 8000
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || echo "No process found on port 8000"

worker: ## Run the SQS worker
	python scripts/worker.py

migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create a new migration
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

docker-up: ## Start Docker services
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

test-api: ## Test deployed API endpoints
	./scripts/test-api.sh

test-api-local: ## Test local API (requires docker-up)
	./scripts/test-api.sh http://localhost:8000

api-key-create: ## Create a new API key (usage: make api-key-create NAME="Customer Name" EMAIL="email@example.com")
	python scripts/manage-api-keys.py create --name "$(NAME)" --email "$(EMAIL)"

api-key-list: ## List all API keys
	python scripts/manage-api-keys.py list

api-key-show: ## Show API key details (usage: make api-key-show CUSTOMER_ID="...")
	python scripts/manage-api-keys.py show $(CUSTOMER_ID)

docker-logs: ## View Docker logs
	docker-compose logs -f

terraform-init: ## Initialize Terraform
	cd terraform && terraform init

terraform-plan: ## Plan Terraform changes
	cd terraform && terraform plan

terraform-apply: ## Apply Terraform changes
	cd terraform && terraform apply

terraform-destroy: ## Destroy Terraform infrastructure
	cd terraform && terraform destroy

terraform-output: ## Show Terraform outputs
	cd terraform && terraform output

aws-setup: ## Set up AWS infrastructure
	./scripts/setup-aws.sh

aws-outputs: ## Get AWS infrastructure outputs
	./scripts/get-aws-outputs.sh

update-env: ## Update .env file from Terraform outputs
	./scripts/update-env-from-terraform.sh

setup-dynamodb: ## Set up DynamoDB Local table
	python scripts/setup-dynamodb-local.py

setup: install docker-up setup-dynamodb migrate ## Initial setup (install deps, start services, run migrations)

# Deployment targets
deploy: ## Deploy to AWS (default: Lambda)
	./scripts/deploy.sh --type lambda

deploy-lambda: ## Deploy to AWS Lambda
	./scripts/deploy.sh --type lambda

deploy-docker: ## Build Docker image for deployment
	./scripts/deploy.sh --type docker

docker-build: ## Build Docker image
	docker build -t zapier-triggers-api:latest .

docker-run: ## Run Docker container locally
	docker run -p 8000:8000 --env-file .env zapier-triggers-api:latest

