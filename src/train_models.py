"""
Main script to train fraud detection models.
"""
import os
import sys
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger
import yaml

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from anomaly_detection.ensemble_detector import EnsembleDetector
from data_pipeline.pipeline import DataPipeline


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description='Train fraud detection models')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--data-source', type=str, default='snowflake',
                       choices=['snowflake', 's3', 'local'],
                       help='Data source')
    parser.add_argument('--data-path', type=str, default=None,
                       help='Path to local data file')
    parser.add_argument('--output-dir', type=str, default='models',
                       help='Output directory for trained models')
    parser.add_argument('--start-date', type=str, default=None,
                       help='Start date for data fetch (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None,
                       help='End date for data fetch (YYYY-MM-DD)')
    parser.add_argument('--sample-size', type=int, default=None,
                       help='Sample size for training (for testing)')
    
    args = parser.parse_args()
    
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/train_models.log", rotation="10 MB")
    
    logger.info("Starting model training pipeline")
    logger.info(f"Configuration: {args.config}")
    
    # Load configuration
    config = load_config(args.config)
    
    # Initialize data pipeline
    pipeline = DataPipeline(args.config)
    
    # Load training data
    logger.info("Loading training data...")
    
    if args.data_source == 'local' and args.data_path:
        # Load from local file
        if args.data_path.endswith('.csv'):
            train_df = pd.read_csv(args.data_path)
        elif args.data_path.endswith('.parquet'):
            train_df = pd.read_parquet(args.data_path)
        else:
            raise ValueError("Unsupported file format. Use CSV or Parquet.")
    
    elif args.data_source == 'snowflake':
        # Fetch from Snowflake
        start_date = args.start_date or '2023-01-01'
        end_date = args.end_date or datetime.now().strftime('%Y-%m-%d')
        train_df = pipeline.fetch_claims_from_snowflake(start_date, end_date)
    
    else:
        raise ValueError(f"Unsupported data source: {args.data_source}")
    
    # Sample data if specified
    if args.sample_size:
        train_df = train_df.sample(n=min(args.sample_size, len(train_df)), random_state=42)
        logger.info(f"Sampled {len(train_df)} records for training")
    
    logger.info(f"Training data shape: {train_df.shape}")
    
    # Split into train and validation
    val_split = 0.2
    val_size = int(len(train_df) * val_split)
    
    train_df_shuffled = train_df.sample(frac=1, random_state=42).reset_index(drop=True)
    val_df = train_df_shuffled.iloc[:val_size]
    train_df = train_df_shuffled.iloc[val_size:]
    
    logger.info(f"Train set: {len(train_df)}, Validation set: {len(val_df)}")
    
    # Initialize ensemble detector
    detector = EnsembleDetector(args.config)
    
    # Train models
    logger.info("Training ensemble models...")
    metrics = detector.train(train_df, val_df)
    
    logger.info("Training completed!")
    logger.info(f"Metrics: {metrics}")
    
    # Save models
    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = f"{args.output_dir}/ensemble_model_{timestamp}"
    
    detector.save_models(model_path)
    logger.info(f"Models saved to {model_path}")
    
    # Save training metadata
    metadata = {
        'model_path': model_path,
        'train_size': len(train_df),
        'val_size': len(val_df),
        'metrics': metrics,
        'timestamp': timestamp,
        'config': config
    }
    
    import json
    with open(f"{args.output_dir}/training_metadata_{timestamp}.json", 'w') as f:
        json.dump(metadata, f, indent=2, default=str)
    
    logger.info("Training pipeline completed successfully!")


if __name__ == "__main__":
    main()
