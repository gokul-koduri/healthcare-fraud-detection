"""
Data Pipeline for Healthcare Claims Fraud Detection
Integrates Snowflake, Databricks (PySpark), and AWS Lambda
"""
import os
import pandas as pd
import numpy as np
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, count, sum as spark_sum
from pyspark.sql.types import StructType, StructField, StringType, FloatType, IntegerType, DateType
import snowflake.connector
from sqlalchemy import create_engine
import boto3
from loguru import logger
from typing import Dict, List, Optional
import yaml
from datetime import datetime, timedelta


class DataPipeline:
    """
    Unified data pipeline for healthcare claims processing.
    
    Integrates:
    - Snowflake for data warehousing
    - Databricks PySpark for big data processing
    - AWS Lambda for serverless processing
    - S3 for data storage
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the data pipeline."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.db_config = self.config['database']
        self.databricks_config = self.config['databricks']
        self.aws_config = self.config['aws']
        
        # Initialize connections
        self.snowflake_conn = None
        self.spark = None
        self.s3_client = None
        
        logger.info("DataPipeline initialized")
    
    def connect_snowflake(self) -> None:
        """Establish connection to Snowflake."""
        try:
            self.snowflake_conn = snowflake.connector.connect(
                user=self.db_config['user'],
                password=self.db_config['password'],
                account=self.db_config['account'],
                warehouse=self.db_config['warehouse'],
                database=self.db_config['database'],
                schema=self.db_config['schema']
            )
            logger.info("Connected to Snowflake")
        except Exception as e:
            logger.error(f"Snowflake connection failed: {e}")
            raise
    
    def connect_databricks(self) -> None:
        """Initialize Databricks Spark session."""
        try:
            # Build Spark configuration for Databricks
            spark_conf = {
                'spark.databricks.service.address': self.databricks_config['host'],
                'spark.databricks.service.token': self.databricks_config['token'],
                'spark.databricks.service.clusterId': self.databricks_config['cluster_id']
            }
            
            self.spark = SparkSession.builder \
                .appName("healthcare_fraud_detection") \
                .config(spark_conf) \
                .getOrCreate()
            
            logger.info("Connected to Databricks")
        except Exception as e:
            logger.error(f"Databricks connection failed: {e}")
            raise
    
    def connect_s3(self) -> None:
        """Initialize AWS S3 client."""
        try:
            session = boto3.Session(region_name=self.aws_config['region'])
            self.s3_client = session.client('s3')
            logger.info("Connected to S3")
        except Exception as e:
            logger.error(f"S3 connection failed: {e}")
            raise
    
    def fetch_claims_from_snowflake(self, 
                                    start_date: str,
                                    end_date: str,
                                    limit: Optional[int] = None) -> pd.DataFrame:
        """
        Fetch claims data from Snowflake.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum number of records to fetch
            
        Returns:
            DataFrame with claims data
        """
        if not self.snowflake_conn:
            self.connect_snowflake()
        
        query = f"""
        SELECT 
            claim_id,
            patient_id,
            provider_id,
            service_date,
            claim_amount,
            service_count,
            patient_age,
            provider_claim_frequency,
            diagnosis_code_count,
            procedure_code_count,
            provider_type,
            specialty,
            place_of_service,
            diagnosis_codes,
            procedure_codes,
            created_at
        FROM {self.db_config['database']}.{self.db_config['schema']}.claims
        WHERE service_date BETWEEN '{start_date}' AND '{end_date}'
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            df = pd.read_sql(query, self.snowflake_conn)
            logger.info(f"Fetched {len(df)} claims from Snowflake")
            return df
        except Exception as e:
            logger.error(f"Failed to fetch claims: {e}")
            raise
    
    def process_claims_with_pyspark(self, 
                                   s3_path: str,
                                   features_only: bool = False) -> pd.DataFrame:
        """
        Process claims data using PySpark on Databricks.
        
        Args:
            s3_path: S3 path to raw claims data
            features_only: Whether to return only engineered features
            
        Returns:
            Processed DataFrame
        """
        if not self.spark:
            self.connect_databricks()
        
        try:
            # Read data from S3
            spark_df = self.spark.read.parquet(s3_path)
            
            # Define schema for claims data
            claims_schema = StructType([
                StructField("claim_id", StringType(), True),
                StructField("patient_id", StringType(), True),
                StructField("provider_id", StringType(), True),
                StructField("service_date", DateType(), True),
                StructField("claim_amount", FloatType(), True),
                StructField("service_count", IntegerType(), True),
                StructField("patient_age", IntegerType(), True),
                StructField("provider_claim_frequency", FloatType(), True),
                StructField("diagnosis_code_count", IntegerType(), True),
                StructField("procedure_code_count", IntegerType(), True),
                StructField("provider_type", StringType(), True),
                StructField("specialty", StringType(), True),
                StructField("place_of_service", StringType(), True),
                StructField("diagnosis_codes", StringType(), True),
                StructField("procedure_codes", StringType(), True)
            ])
            
            # Feature Engineering with PySpark
            processed_df = spark_df \
                .withColumn("amount_per_service", 
                           col("claim_amount") / col("service_count")) \
                .withColumn("claim_frequency_ratio", 
                           col("provider_claim_frequency") / 100) \
                .withColumn("high_amount_flag",
                           when(col("claim_amount") > 5000, 1).otherwise(0)) \
                .withColumn("high_service_flag",
                           when(col("service_count") > 10, 1).otherwise(0))
            
            # Provider-level aggregations
            provider_stats = spark_df.groupBy("provider_id").agg(
                count("claim_id").alias("total_claims"),
                spark_sum("claim_amount").alias("total_amount"),
                spark_sum("service_count").alias("total_services")
            )
            
            # Join provider stats
            processed_df = processed_df.join(
                provider_stats, 
                on="provider_id", 
                how="left"
            )
            
            # Calculate derived features
            processed_df = processed_df \
                .withColumn("avg_claim_amount_per_provider",
                           col("total_amount") / col("total_claims")) \
                .withColumn("claim_amount_vs_avg",
                           col("claim_amount") - col("avg_claim_amount_per_provider"))
            
            if features_only:
                feature_cols = [
                    "claim_id", "amount_per_service", "claim_frequency_ratio",
                    "high_amount_flag", "high_service_flag",
                    "avg_claim_amount_per_provider", "claim_amount_vs_avg"
                ]
                processed_df = processed_df.select(*feature_cols)
            
            # Convert to Pandas
            result_df = processed_df.toPandas()
            
            logger.info(f"Processed {len(result_df)} claims with PySpark")
            
            return result_df
            
        except Exception as e:
            logger.error(f"PySpark processing failed: {e}")
            raise
    
    def upload_to_s3(self, df: pd.DataFrame, 
                    key: str,
                    file_format: str = "parquet") -> str:
        """
        Upload processed data to S3.
        
        Args:
            df: DataFrame to upload
            key: S3 key (path)
            file_format: File format ('parquet' or 'csv')
            
        Returns:
            S3 URI
        """
        if not self.s3_client:
            self.connect_s3()
        
        bucket = self.aws_config['s3']['bucket']
        
        try:
            # Local temp file
            temp_path = f"/tmp/{key.replace('/', '_')}"
            
            if file_format == "parquet":
                df.to_parquet(temp_path, index=False)
                content_type = "application/octet-stream"
            else:
                df.to_csv(temp_path, index=False)
                content_type = "text/csv"
            
            # Upload to S3
            s3_key = f"{self.aws_config['s3']['processed_prefix']}{key}"
            self.s3_client.upload_file(
                temp_path, 
                bucket, 
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )
            
            # Clean up temp file
            os.remove(temp_path)
            
            s3_uri = f"s3://{bucket}/{s3_key}"
            logger.info(f"Uploaded data to {s3_uri}")
            
            return s3_uri
            
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise
    
    def trigger_lambda_processing(self, 
                                 s3_uri: str,
                                 lambda_function: Optional[str] = None) -> Dict:
        """
        Trigger AWS Lambda for processing.
        
        Args:
            s3_uri: S3 URI to process
            lambda_function: Lambda function name (optional)
            
        Returns:
            Lambda response
        """
        lambda_client = boto3.client('lambda', region_name=self.aws_config['region'])
        
        function_name = lambda_function or self.aws_config['lambda']['function_name']
        
        try:
            payload = {
                "s3_uri": s3_uri,
                "timestamp": datetime.now().isoformat(),
                "action": "process_fraud_detection"
            }
            
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='Event',  # Async
                Payload=str(payload)
            )
            
            logger.info(f"Triggered Lambda function: {function_name}")
            return response
            
        except Exception as e:
            logger.error(f"Lambda trigger failed: {e}")
            raise
    
    def run_batch_processing(self, 
                            start_date: str,
                            end_date: str,
                            batch_size: int = 100000) -> List[str]:
        """
        Run complete batch processing pipeline.
        
        Args:
            start_date: Start date
            end_date: End date
            batch_size: Batch size for processing
            
        Returns:
            List of S3 URIs for processed batches
        """
        logger.info(f"Starting batch processing: {start_date} to {end_date}")
        
        processed_uris = []
        
        # Fetch data in batches
        offset = 0
        while True:
            df = self.fetch_claims_from_snowflake(
                start_date, 
                end_date, 
                limit=batch_size
            )
            
            if len(df) == 0:
                break
            
            # Process features
            # In production, use PySpark for large datasets
            processed_df = self.engineer_features(df)
            
            # Upload to S3
            date_str = datetime.now().strftime("%Y%m%d")
            key = f"batch_{date_str}_{offset}.parquet"
            s3_uri = self.upload_to_s3(processed_df, key)
            processed_uris.append(s3_uri)
            
            # Trigger Lambda for processing
            self.trigger_lambda_processing(s3_uri)
            
            offset += batch_size
            logger.info(f"Processed batch: {offset} records")
            
            if len(df) < batch_size:
                break
        
        logger.info(f"Batch processing completed. Processed {len(processed_uris)} batches")
        
        return processed_uris
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer fraud detection features.
        
        Args:
            df: Input claims dataframe
            
        Returns:
            DataFrame with engineered features
        """
        df = df.copy()
        
        # Numerical features
        df['amount_per_service'] = df['claim_amount'] / (df['service_count'] + 1)
        df['claim_frequency_ratio'] = df['provider_claim_frequency'] / 100
        df['diagnosis_per_service'] = df['diagnosis_code_count'] / (df['service_count'] + 1)
        df['procedure_per_service'] = df['procedure_code_count'] / (df['service_count'] + 1)
        
        # Ratio features
        df['amount_vs_age'] = df['claim_amount'] / (df['patient_age'] + 1)
        df['service_vs_diagnosis'] = df['service_count'] / (df['diagnosis_code_count'] + 1)
        
        # Flag features
        df['high_amount_flag'] = (df['claim_amount'] > 5000).astype(int)
        df['high_service_flag'] = (df['service_count'] > 10).astype(int)
        df['high_diagnosis_flag'] = (df['diagnosis_code_count'] > 5).astype(int)
        
        # Provider patterns (simplified - in production, use window functions)
        provider_stats = df.groupby('provider_id').agg({
            'claim_amount': ['mean', 'std'],
            'service_count': 'mean'
        }).reset_index()
        provider_stats.columns = ['provider_id', 'provider_avg_amount', 
                                  'provider_std_amount', 'provider_avg_services']
        
        df = df.merge(provider_stats, on='provider_id', how='left')
        df['amount_vs_provider_avg'] = df['claim_amount'] - df['provider_avg_amount']
        df['amount_z_score'] = (df['claim_amount'] - df['provider_avg_amount']) / (df['provider_std_amount'] + 1)
        
        return df
    
    def get_summary_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Calculate summary statistics for reporting.
        
        Args:
            df: Claims dataframe
            
        Returns:
            Dictionary with summary statistics
        """
        return {
            'total_claims': len(df),
            'total_amount': float(df['claim_amount'].sum()),
            'avg_claim_amount': float(df['claim_amount'].mean()),
            'avg_service_count': float(df['service_count'].mean()),
            'unique_providers': df['provider_id'].nunique(),
            'unique_patients': df['patient_id'].nunique(),
            'high_value_claims': int((df['claim_amount'] > 5000).sum()),
            'high_service_claims': int((df['service_count'] > 10).sum())
        }
    
    def close_connections(self) -> None:
        """Close all database connections."""
        if self.snowflake_conn:
            self.snowflake_conn.close()
            logger.info("Snowflake connection closed")
        
        if self.spark:
            self.spark.stop()
            logger.info("Spark session stopped")


if __name__ == "__main__":
    # Example usage
    pipeline = DataPipeline()
    
    # Sample data
    sample_data = pd.DataFrame({
        'claim_id': [f'CLM-{i:06d}' for i in range(1000)],
        'patient_id': [f'PAT-{i%500:04d}' for i in range(1000)],
        'provider_id': [f'PROV-{i%50:04d}' for i in range(1000)],
        'service_date': ['2024-01-15'] * 1000,
        'claim_amount': np.random.uniform(100, 10000, 1000),
        'service_count': np.random.randint(1, 20, 1000),
        'patient_age': np.random.randint(18, 90, 1000),
        'provider_claim_frequency': np.random.uniform(0.1, 5.0, 1000),
        'diagnosis_code_count': np.random.randint(1, 8, 1000),
        'procedure_code_count': np.random.randint(1, 10, 1000),
        'provider_type': np.random.choice(['Hospital', 'Clinic', 'Individual'], 1000),
        'specialty': np.random.choice(['Cardiology', 'Orthopedics', 'General'], 1000),
        'place_of_service': np.random.choice(['Office', 'Hospital', 'Urgent Care'], 1000),
        'diagnosis_codes': ['M54.5'] * 1000,
        'procedure_codes': ['99203'] * 1000
    })
    
    # Engineer features
    processed_df = pipeline.engineer_features(sample_data)
    print(f"Processed features: {processed_df.shape}")
    print(f"Features: {list(processed_df.columns)}")
    
    # Get summary statistics
    stats = pipeline.get_summary_statistics(sample_data)
    print(f"\nSummary Statistics:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
