"""
Main script to predict fraud on claims data.
"""
import os
import sys
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger
import yaml
import json

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from anomaly_detection.ensemble_detector import EnsembleDetector
from data_pipeline.pipeline import DataPipeline


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main prediction function."""
    parser = argparse.ArgumentParser(description='Predict fraud on healthcare claims')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--input', type=str, required=True,
                       help='Input data path (CSV, Parquet, or S3 URI)')
    parser.add_argument('--model', type=str, required=True,
                       help='Path to trained model (base path, without suffix)')
    parser.add_argument('--output', type=str, required=True,
                       help='Output path for predictions (CSV or Parquet)')
    parser.add_argument('--batch-size', type=int, default=10000,
                       help='Batch size for processing')
    parser.add_argument('--generate-reports', action='store_true',
                       help='Generate individual audit reports for high-risk claims')
    parser.add_argument('--threshold', type=float, default=None,
                       help='Custom fraud probability threshold')
    
    args = parser.parse_args()
    
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/predict_fraud.log", rotation="10 MB")
    
    logger.info("Starting fraud prediction pipeline")
    logger.info(f"Input: {args.input}")
    logger.info(f"Model: {args.model}")
    logger.info(f"Output: {args.output}")
    
    # Load configuration
    config = load_config(args.config)
    
    # Load input data
    logger.info("Loading input data...")
    
    if args.input.startswith('s3://'):
        # Load from S3
        pipeline = DataPipeline(args.config)
        pipeline.connect_s3()
        # Simplified - in production, use proper S3 download
        df = pd.read_parquet(args.input.replace('s3://', '/tmp/'))
    else:
        # Load from local file
        if args.input.endswith('.csv'):
            df = pd.read_csv(args.input)
        elif args.input.endswith('.parquet'):
            df = pd.read_parquet(args.input)
        else:
            raise ValueError("Unsupported file format. Use CSV or Parquet.")
    
    logger.info(f"Input data shape: {df.shape}")
    
    # Initialize detector and load model
    detector = EnsembleDetector(args.config)
    detector.load_models(args.model)
    logger.info("Model loaded successfully")
    
    # Make predictions
    logger.info("Making predictions...")
    results = detector.predict_batch(df, batch_size=args.batch_size)
    
    # Apply custom threshold if specified
    if args.threshold is not None:
        results['is_fraud'] = results['ensemble_fraud_probability'] > args.threshold
        logger.info(f"Using custom threshold: {args.threshold}")
    
    # Summary statistics
    fraud_count = results['is_fraud'].sum()
    fraud_rate = fraud_count / len(results) * 100
    
    logger.info(f"Prediction completed!")
    logger.info(f"Total claims: {len(results)}")
    logger.info(f"Fraudulent claims: {fraud_count} ({fraud_rate:.2f}%)")
    
    # Risk distribution
    risk_counts = results['risk_level'].value_counts()
    logger.info("Risk distribution:")
    for risk, count in risk_counts.items():
        logger.info(f"  {risk}: {count} ({count/len(results)*100:.2f}%)")
    
    # Save predictions
    logger.info(f"Saving predictions to {args.output}...")
    if args.output.endswith('.csv'):
        results.to_csv(args.output, index=False)
    elif args.output.endswith('.parquet'):
        results.to_parquet(args.output, index=False)
    else:
        raise ValueError("Unsupported output format. Use CSV or Parquet.")
    
    # Generate individual reports for high-risk claims if requested
    if args.generate_reports:
        logger.info("Generating audit reports for high-risk claims...")
        
        from genai.audit_assistant import AuditAssistant
        
        high_risk_claims = results[results['risk_level'].isin(['High', 'Critical'])]
        
        if len(high_risk_claims) > 0:
            assistant = AuditAssistant(args.config)
            reports_dir = args.output.rsplit('.', 1)[0] + '_reports'
            os.makedirs(reports_dir, exist_ok=True)
            
            for idx, row in high_risk_claims.head(10).iterrows():
                claim_data = {
                    'claim_id': row.get('claim_id', idx),
                    'patient_id': row.get('patient_id', 'N/A'),
                    'provider_id': row.get('provider_id', 'N/A'),
                    'service_date': str(row.get('service_date', 'N/A')),
                    'claim_amount': row.get('claim_amount', 0),
                    'services': row.get('services', 'N/A'),
                    'fraud_probability': row.get('ensemble_fraud_probability', 0),
                    'risk_level': row.get('risk_level', 'N/A'),
                    'anomalies': row.get('anomalies', 'None'),
                    'diagnosis_codes': row.get('diagnosis_codes', 'N/A'),
                    'procedure_codes': row.get('procedure_codes', 'N/A')
                }
                
                try:
                    report = assistant.generate_investigation_summary(claim_data)
                    
                    report_path = f"{reports_dir}/report_{claim_data['claim_id']}.txt"
                    with open(report_path, 'w') as f:
                        f.write(f"CLAIM INVESTIGATION REPORT\n")
                        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"{'='*80}\n\n")
                        f.write(report)
                    
                    logger.info(f"Report generated: {report_path}")
                except Exception as e:
                    logger.error(f"Failed to generate report for claim {claim_data['claim_id']}: {e}")
    
    # Save prediction metadata
    metadata = {
        'input_path': args.input,
        'output_path': args.output,
        'model_path': args.model,
        'total_claims': int(len(results)),
        'fraudulent_claims': int(fraud_count),
        'fraud_rate': float(fraud_rate),
        'risk_distribution': risk_counts.to_dict(),
        'timestamp': datetime.now().isoformat()
    }
    
    metadata_path = args.output.rsplit('.', 1)[0] + '_metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)
    
    logger.info(f"Metadata saved to {metadata_path}")
    logger.info("Prediction pipeline completed successfully!")
    
    # Print summary
    print(f"\n{'='*80}")
    print("PREDICTION SUMMARY")
    print(f"{'='*80}")
    print(f"Total Claims Processed: {len(results):,}")
    print(f"Fraudulent Claims: {fraud_count:,} ({fraud_rate:.2f}%)")
    print(f"Risk Distribution:")
    for risk, count in risk_counts.items():
        print(f"  - {risk}: {count:,} ({count/len(results)*100:.2f}%)")
    print(f"\nResults saved to: {args.output}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
