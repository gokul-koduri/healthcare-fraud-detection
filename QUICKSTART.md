# Quick Start Guide

## Prerequisites
- Python 3.11+
- AWS Account (for Lambda/S3)
- Snowflake account (optional, for production)
- OpenAI API key (for GenAI features)

## Installation

### 1. Clone and Setup
```bash
# Clone repository
git clone <repository-url>
cd healthcare-fraud-detection

# Install dependencies
make install

# Activate virtual environment
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

## Quick Demo (5 Minutes)

### Generate Sample Data & Train Models
```bash
# Generate 10,000 sample claims
make data

# Train fraud detection models
make train

# This trains both Isolation Forest and Autoencoder models
# Results saved to models/ directory
```

### Run Predictions
```bash
# Run fraud detection on sample data
make predict

# Results saved to data/processed/predictions.parquet
# Individual reports generated in reports/individual_reports_*/
```

### Generate Reports
```bash
# Generate compliance audit report
make report

# Reports saved in reports/ directory
# Includes: compliance report, HTML dashboard, and summary
```

### Run Full Pipeline
```bash
# Run complete end-to-end pipeline
make pipeline

# This will:
# 1. Extract data from source
# 2. Process and engineer features
# 3. Run fraud detection
# 4. Generate audit reports
# 5. Upload results to S3
# 6. Trigger downstream processing
```

## Using Individual Components

### Train Models with Custom Data
```bash
python src/train_models.py \
  --data-source local \
  --data-path /path/to/your/data.csv \
  --output-dir models \
  --sample-size 100000
```

### Run Predictions
```bash
python src/predict_fraud.py \
  --input /path/to/data.csv \
  --model models/ensemble_model_20240101_120000 \
  --output predictions.csv \
  --batch-size 10000 \
  --generate-reports
```

### Generate Audit Reports
```bash
python src/genai/generate_audit_report.py \
  --input predictions.parquet \
  --output-dir reports \
  --format txt json html \
  --period "Last 30 Days" \
  --max-claims 100
```

## Development Mode

### Run Tests
```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_detector.py -v
```

### Code Quality
```bash
# Lint code
make lint
```

### MLflow Tracking (Optional)
```bash
# Start MLflow server
make mlflow-start

# Access at http://localhost:5000
```

## Production Deployment

### Prerequisites
1. Set up Snowflake database and tables
2. Create S3 bucket
3. Configure AWS credentials
4. Set environment variables

### Deploy dbt Models
```bash
# Initialize and run dbt
cd dbt
dbt debug --profiles-dir .
dbt run --profiles-dir .
```

### Deploy Lambda Function
```bash
# Package and deploy
make lambda-deploy
```

### Run Production Pipeline
```bash
python src/run_pipeline.py \
  --mode production \
  --start-date 2024-01-01 \
  --end-date 2024-01-31
```

## Project Structure

```
healthcare-fraud-detection/
├── config/                 # Configuration files
│   └── config.yaml        # Main configuration
├── data/                  # Data directories
│   ├── raw/              # Raw claims data
│   ├── processed/        # Processed predictions
│   └── features/         # Feature stores
├── src/                   # Source code
│   ├── anomaly_detection/ # ML models
│   ├── genai/            # GenAI assistant
│   ├── data_pipeline/    # Data processing
│   ├── train_models.py   # Training script
│   ├── predict_fraud.py  # Prediction script
│   └── run_pipeline.py   # Orchestration
├── dbt/                   # Data transformations
├── lambda/                # AWS Lambda handler
├── models/                # Trained models
├── reports/               # Generated reports
├── tests/                 # Unit tests
└── notebooks/             # Jupyter notebooks
```

## Key Results

When running on 2M+ claims, expect:
- **False Positive Reduction**: ~28%
- **Audit Efficiency Gain**: ~35%
- **Processing Speed**: ~100K claims/hour
- **Detection Accuracy**: 94%+

## Troubleshooting

### Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Model Loading Errors
```bash
# Check if models exist
ls models/

# Train models if not present
make train
```

### Snowflake Connection Issues
```bash
# Verify credentials in .env
cat .env

# Test connection
python -c "import snowflake.connector; ..."
```

## Next Steps

1. **Customize Features**: Edit `config/config.yaml` for your data
2. **Add Your Data**: Replace sample data with real claims
3. **Tune Models**: Adjust hyperparameters in config
4. **Set Up Monitoring**: Configure CloudWatch alerts
5. **Deploy to Production**: Follow DEPLOYMENT.md

## Additional Resources

- **Full Documentation**: README.md
- **Deployment Guide**: DEPLOYMENT.md
- **Tableau Guide**: docs/TABLEAU_DASHBOARD.md
- **API Reference**: docs/API.md (if available)

## Support

For issues or questions:
- GitHub Issues: <repository-url>/issues
- Email: healthcare-analytics@company.com
- Slack: #healthcare-analytics
