.PHONY: help install test train predict report clean deploy lint

help:
	@echo "Healthcare Claims Fraud Detection System"
	@echo ""
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make test         - Run tests"
	@echo "  make data         - Generate sample data"
	@echo "  make train        - Train models"
	@echo "  make predict      - Run predictions"
	@echo "  make report       - Generate audit reports"
	@echo "  make pipeline     - Run full pipeline"
	@echo "  make dbt          - Run dbt transformations"
	@echo "  make lambda       - Package and deploy Lambda"
	@echo "  make lint         - Run code linting"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make deploy       - Deploy to production"

install:
	@echo "Installing dependencies..."
	python -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	@echo "Dependencies installed successfully"

test:
	@echo "Running tests..."
	. venv/bin/activate && pytest tests/ -v --cov=src --cov-report=html
	@echo "Tests completed"

data:
	@echo "Generating sample data..."
	. venv/bin/activate && python src/generate_sample_data.py --samples 10000 --output data/raw/sample_claims.parquet
	@echo "Sample data generated"

train:
	@echo "Training models..."
	. venv/bin/activate && python src/train_models.py \
		--data-source local \
		--data-path data/raw/sample_claims.parquet \
		--output-dir models \
		--sample-size 10000
	@echo "Model training completed"

predict:
	@echo "Running predictions..."
	. venv/bin/activate && python src/predict_fraud.py \
		--input data/raw/sample_claims.parquet \
		--model models/ensemble_model_20240101_120000 \
		--output data/processed/predictions.parquet \
		--generate-reports
	@echo "Predictions completed"

report:
	@echo "Generating audit reports..."
	. venv/bin/activate && python src/genai/generate_audit_report.py \
		--input data/processed/predictions.parquet \
		--output-dir reports \
		--format txt json html \
		--include-charts
	@echo "Reports generated"

pipeline:
	@echo "Running full pipeline..."
	. venv/bin/activate && python src/run_pipeline.py \
		--mode production \
		--generate-reports
	@echo "Pipeline completed"

dbt-init:
	@echo "Initializing dbt..."
	cd dbt && dbt init --profiles-dir .

dbt-run:
	@echo "Running dbt transformations..."
	cd dbt && dbt run --profiles-dir .

dbt-test:
	@echo "Testing dbt models..."
	cd dbt && dbt test --profiles-dir .

lambda-package:
	@echo "Packaging Lambda function..."
	@mkdir -p lambda/package
	@. venv/bin/activate && pip install -r requirements.txt --target lambda/package
	@cd lambda/package && zip -r ../lambda_deployment.zip .
	@cd lambda && zip -g lambda_deployment.zip lambda_handler.py
	@echo "Lambda package created: lambda/lambda_deployment.zip"

lambda-deploy: lambda-package
	@echo "Deploying Lambda function..."
	aws lambda update-function-code \
		--function-name claims-processor \
		--zip-file fileb://lambda/lambda_deployment.zip
	@echo "Lambda deployed"

lint:
	@echo "Running code linting..."
	. venv/bin/activate && flake8 src/ tests/ --max-line-length=100
	. venv/bin/activate && black src/ tests/ --check
	@echo "Linting completed"

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache/ htmlcov/ .coverage
	rm -rf lambda/package lambda/*.zip
	@echo "Clean completed"

deploy:
	@echo "Deploying to production..."
	@echo "This will:"
	@echo "1. Run dbt migrations"
	@echo "2. Deploy Lambda function"
	@echo "3. Start pipeline processing"
	@read -p "Continue? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		make dbt-run; \
		make lambda-deploy; \
		echo "Production deployment completed"; \
	else \
		echo "Deployment cancelled"; \
	fi

mlflow-start:
	@echo "Starting MLflow server..."
	. venv/bin/activate && mlflow server --backend-store-uri mlflow/ --default-artifact-root mlflow/artifacts --host 0.0.0.0 --port 5000

dev-setup: install data
	@echo "Development environment setup complete"
	@echo "Run 'source venv/bin/activate' to activate the virtual environment"
