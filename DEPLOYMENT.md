# Deployment Guide - Healthcare Claims Fraud Detection System

## Prerequisites

### Infrastructure
- **Snowflake**: Data warehouse for claims storage
- **Databricks**: Cluster for big data processing
- **AWS Account**: For Lambda, S3, and serverless processing
- **OpenAI API**: For GenAI audit assistant
- **MLflow Server**: For model tracking (optional)

### Software
- Python 3.11+
- AWS CLI configured
- Snowflake CLI
- Databricks CLI
- dbt CLI

## Environment Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd healthcare-fraud-detection
```

### 2. Install Dependencies
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt
```

### 3. Configure Environment Variables
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required environment variables:
```bash
# Snowflake
SNOWFLAKE_HOST=your_account.snowflakecomputing.com
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_WAREHOUSE=compute_wh
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password

# Databricks
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your_token
DATABRICKS_CLUSTER_ID=your_cluster_id

# AWS
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# OpenAI
OPENAI_API_KEY=your_openai_key
```

## Deployment Steps

### Phase 1: Data Infrastructure Setup

#### 1.1 Snowflake Setup
```sql
-- Create database
CREATE DATABASE IF NOT EXISTS healthcare_claims;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS healthcare_claims.raw;
CREATE SCHEMA IF NOT EXISTS healthcare_claims.fraud_detection;
CREATE SCHEMA IF NOT EXISTS healthcare_claims.analytics;

-- Grant permissions
GRANT USAGE ON DATABASE healthcare_claims TO ROLE transform_role;
GRANT USAGE ON SCHEMA healthcare_claims.fraud_detection TO ROLE transform_role;
```

#### 1.2 S3 Bucket Setup
```bash
# Create S3 bucket
aws s3 mb s3://healthcare-claims-data --region us-east-1

# Create folder structure
aws s3api put-object --bucket healthcare-claims-data --key raw/
aws s3api put-object --bucket healthcare-claims-data --key processed/
aws s3api put-object --bucket healthcare-claims-data --key models/
```

#### 1.3 dbt Setup
```bash
# Initialize dbt
cd dbt
dbt debug --profiles-dir .
dbt seed --profiles-dir .
dbt run --profiles-dir .
```

### Phase 2: Model Training

#### 2.1 Generate/Load Training Data
```bash
# Option A: Generate sample data
python src/generate_sample_data.py --samples 100000 --output data/raw/train_data.parquet

# Option B: Load from Snowflake
python src/train_models.py \
  --data-source snowflake \
  --start-date 2023-01-01 \
  --end-date 2023-12-31 \
  --output-dir models
```

#### 2.2 Train Models
```bash
# Train ensemble model
python src/train_models.py \
  --data-source local \
  --data-path data/raw/train_data.parquet \
  --output-dir models \
  --sample-size 100000
```

#### 2.3 Start MLflow (Optional)
```bash
# Start MLflow server
mlflow server --backend-store-uri mlflow/ --default-artifact-root mlflow/artifacts --host 0.0.0.0 --port 5000
```

### Phase 3: AWS Lambda Deployment

#### 3.1 Package Lambda Function
```bash
# Create deployment package
cd lambda
pip install -r ../../requirements.txt --target ./package
cd package
zip -r ../lambda_deployment.zip .
cd ..
zip -g lambda_deployment.zip lambda_handler.py
```

#### 3.2 Deploy Lambda Function
```bash
# Create Lambda function
aws lambda create-function \
  --function-name claims-processor \
  --runtime python3.11 \
  --role arn:aws:iam::<account-id>:role/LambdaExecutionRole \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://lambda_deployment.zip \
  --timeout 300 \
  --memory-size 512 \
  --environment Variables={CONFIG_PATH=config/config.yaml,MODEL_PATH=models/ensemble_model_latest}

# Update function code (for updates)
aws lambda update-function-code \
  --function-name claims-processor \
  --zip-file fileb://lambda_deployment.zip
```

#### 3.3 Create S3 Event Trigger
```bash
# Add S3 trigger to Lambda
aws s3api put-bucket-notification-configuration \
  --bucket healthcare-claims-data \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [{
      "Id": "claimsProcessor",
      "LambdaFunctionArn": "arn:aws:lambda:us-east-1:<account-id>:function:claims-processor",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [{"Name": "prefix", "Value": "raw/"}]
        }
      }
    }]
  }'
```

### Phase 4: Production Pipeline

#### 4.1 Run Full Pipeline
```bash
# Production mode
python src/run_pipeline.py \
  --mode production \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --model-path models/ensemble_model_20240101_120000

# Batch mode
python src/run_pipeline.py \
  --mode batch \
  --start-date 2024-01-01 \
  --end-date 2024-01-31
```

#### 4.2 Generate Reports
```bash
python src/genai/generate_audit_report.py \
  --input data/processed/predictions_production_20240101.parquet \
  --output-dir reports \
  --format txt json html \
  --include-charts
```

### Phase 5: Monitoring & Alerting

#### 5.1 Set Up CloudWatch Alarms
```bash
# Create alarm for Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name claims-processor-errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=claims-processor
```

#### 5.2 Set Up Scheduled Execution
```bash
# Using AWS EventBridge (CloudWatch Events)
aws events put-rule \
  --name daily-fraud-detection \
  --schedule-expression "cron(0 2 * * ? *)"

aws lambda add-permission \
  --function-name claims-processor \
  --statement-id daily-schedule \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn <rule-arn>
```

## Validation & Testing

### Run Tests
```bash
# Unit tests
pytest tests/ -v

# Integration test with sample data
python src/generate_sample_data.py --samples 1000 --output data/raw/test_data.parquet
python src/predict_fraud.py \
  --input data/raw/test_data.parquet \
  --model models/ensemble_model_latest \
  --output data/processed/test_predictions.parquet
```

### Performance Validation
- Verify false positive reduction (~28%)
- Check audit time improvement (~35%)
- Validate processing speed (2M+ claims)

## Troubleshooting

### Common Issues

1. **Snowflake Connection Failed**
   - Verify credentials in .env
   - Check network connectivity
   - Validate warehouse is running

2. **Lambda Memory Issues**
   - Increase memory size in configuration
   - Reduce batch size
   - Use larger Lambda instance

3. **Model Loading Errors**
   - Verify model files exist
   - Check model compatibility
   - Validate S3 permissions

4. **OpenAI API Rate Limits**
   - Implement exponential backoff
   - Use batching for reports
   - Consider caching

## Maintenance

### Regular Tasks
- Weekly: Review CloudWatch metrics
- Monthly: Retrain models with new data
- Quarterly: Update feature engineering
- Annually: Review and update compliance rules

### Model Retraining
```bash
# Schedule monthly retraining
python src/train_models.py \
  --data-source snowflake \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --output-dir models

# Update Lambda with new model
aws s3 cp models/ensemble_model_* s3://healthcare-claims-data/models/
# Update MODEL_PATH environment variable
```

## Security Considerations

1. **Data Encryption**
   - Enable Snowflake encryption
   - Use S3 server-side encryption
   - Encrypt model artifacts

2. **Access Control**
   - Use IAM roles for Lambda
   - Implement Snowflake row-level security
   - Rotate API keys regularly

3. **Compliance**
   - Follow HIPAA guidelines
   - Maintain audit logs
   - Regular security assessments

## Scaling Considerations

### Horizontal Scaling
- Use Databricks for large-scale processing
- Deploy multiple Lambda instances
- Implement queue-based processing with SQS

### Performance Optimization
- Cache frequently accessed data
- Use read replicas for queries
- Implement batch prediction
- Optimize dbt models

## Contact & Support

For issues or questions:
- GitHub Issues: <repository-url>/issues
- Documentation: /docs
- Team: healthcare-analytics@company.com
