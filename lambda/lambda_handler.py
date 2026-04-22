"""
AWS Lambda handler for healthcare claims fraud detection.
Processes claims data serverlessly using S3 events.
"""
import json
import os
import sys
import boto3
import pandas as pd
import numpy as np
from io import StringIO
import tempfile

# Add src to path for imports
sys.path.append('/opt/python')

from anomaly_detection.ensemble_detector import EnsembleDetector
from data_pipeline.pipeline import DataPipeline


def lambda_handler(event, context):
    """
    AWS Lambda handler for processing claims data.
    
    Expected event structure:
    {
        "s3_uri": "s3://bucket/path/to/data.parquet",
        "action": "process_fraud_detection",
        "model_path": "s3://models-path/ensemble_model_20240101"
    }
    
    Also handles S3 event notifications:
    {
        "Records": [{
            "s3": {
                "bucket": {"name": "bucket"},
                "object": {"key": "path/to/data.parquet"}
            }
        }]
    }
    """
    
    print(f"Lambda invocation: {context.function_name}")
    print(f"Event: {json.dumps(event, default=str)[:500]}")
    
    try:
        # Parse input
        s3_uri = None
        action = "process_fraud_detection"
        model_path = os.environ.get('MODEL_PATH', 'models/ensemble_model_latest')
        
        # Check if direct invocation or S3 event
        if 's3_uri' in event:
            s3_uri = event['s3_uri']
            action = event.get('action', action)
            model_path = event.get('model_path', model_path)
        elif 'Records' in event:
            # S3 event notification
            record = event['Records'][0]
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            s3_uri = f"s3://{bucket}/{key}"
        
        if not s3_uri:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No S3 URI provided'})
            }
        
        print(f"Processing: {s3_uri}")
        
        # Process based on action
        if action == "process_fraud_detection":
            result = process_fraud_detection(s3_uri, model_path)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Processing completed successfully',
                's3_uri': s3_uri,
                'result': result
            }, default=str)
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'type': type(e).__name__
            })
        }


def process_fraud_detection(s3_uri: str, model_path: str) -> dict:
    """Process claims data for fraud detection."""
    
    # Parse S3 URI
    parts = s3_uri.replace('s3://', '').split('/')
    bucket = parts[0]
    key = '/'.join(parts[1:])
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    # Download data to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
        s3_client.download_file(bucket, key, tmp.name)
        
        # Read data
        df = pd.read_parquet(tmp.name)
        print(f"Loaded {len(df)} claims")
        
        # Remove temp file
        os.unlink(tmp.name)
    
    # Initialize detector
    # Note: In production, download model from S3 first
    config_path = os.environ.get('CONFIG_PATH', 'config/config.yaml')
    detector = EnsembleDetector(config_path)
    
    # Download model from S3 if needed
    if model_path.startswith('s3://'):
        model_parts = model_path.replace('s3://', '').split('/')
        model_bucket = model_parts[0]
        model_key = '/'.join(model_parts[1:])
        
        # Download model files to /tmp
        local_model_path = '/tmp/model'
        os.makedirs(local_model_path, exist_ok=True)
        
        for suffix in ['_isolation_forest.pkl', '_autoencoder_model.keras', '_autoencoder_metadata.pkl']:
            try:
                obj_key = f"{model_key}{suffix}"
                local_path = f"{local_model_path}/{suffix}"
                
                # Try to download
                s3_client.download_file(model_bucket, obj_key, local_path)
                print(f"Downloaded: {suffix}")
            except Exception as e:
                print(f"Warning: Could not download {suffix}: {e}")
        
        model_path = local_model_path
    
    # Load model
    detector.load_models(model_path)
    
    # Make predictions
    results = detector.predict_batch(df, batch_size=5000)
    
    # Calculate metrics
    fraud_count = results['is_fraud'].sum()
    fraud_rate = fraud_count / len(results) * 100
    
    # Save results to S3
    output_key = key.replace('.parquet', '_predictions.parquet')
    output_key = output_key.replace('/raw/', '/processed/')
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
        results.to_parquet(tmp.name, index=False)
        
        # Upload to S3
        s3_client.upload_file(tmp.name, bucket, output_key)
        os.unlink(tmp.name)
    
    print(f"Uploaded results to: s3://{bucket}/{output_key}")
    
    return {
        'total_claims': int(len(results)),
        'fraudulent_claims': int(fraud_count),
        'fraud_rate': float(fraud_rate),
        'output_uri': f"s3://{bucket}/{output_key}",
        'risk_distribution': results['risk_level'].value_counts().to_dict()
    }


def warm_up_handler(event, context):
    """
    Lambda@Edge / warm-up handler to keep functions warm.
    """
    return {
        'statusCode': 200,
        'body': json.dumps({'status': 'warm'})
    }


# Local testing
if __name__ == "__main__":
    # Test event structure
    test_event = {
        "s3_uri": "s3://healthcare-claims-data/raw/claims_batch.parquet",
        "action": "process_fraud_detection",
        "model_path": "models/ensemble_model_20240101"
    }
    
    # Mock context
    class MockContext:
        function_name = "claims-processor"
    
    result = lambda_handler(test_event, MockContext())
    print(f"Result: {json.dumps(result, indent=2)}")
