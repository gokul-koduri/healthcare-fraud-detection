"""
Generate sample healthcare claims data for testing and development.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse


def generate_sample_claims(n_samples: int = 10000, 
                          fraud_ratio: float = 0.05,
                          random_seed: int = 42) -> pd.DataFrame:
    """
    Generate sample healthcare claims data.
    
    Args:
        n_samples: Number of claims to generate
        fraud_ratio: Ratio of fraudulent claims
        random_seed: Random seed for reproducibility
        
    Returns:
        DataFrame with sample claims
    """
    np.random.seed(random_seed)
    
    # Generate base data
    n_fraud = int(n_samples * fraud_ratio)
    n_normal = n_samples - n_fraud
    
    # Normal claims
    normal_data = {
        'claim_id': [f'CLM-{i:06d}' for i in range(n_normal)],
        'patient_id': [f'PAT-{np.random.randint(1, 5000):05d}' for _ in range(n_normal)],
        'provider_id': [f'PROV-{np.random.randint(1, 500):04d}' for _ in range(n_normal)],
        'service_date': [datetime.now() - timedelta(days=np.random.randint(0, 365)) for _ in range(n_normal)],
        'claim_amount': np.random.lognormal(7, 0.5, n_normal),
        'service_count': np.random.poisson(3, n_normal) + 1,
        'patient_age': np.random.normal(50, 15, n_normal),
        'provider_claim_frequency': np.random.uniform(0.1, 3.0, n_normal),
        'diagnosis_code_count': np.random.poisson(2, n_normal) + 1,
        'procedure_code_count': np.random.poisson(3, n_normal) + 1,
    }
    
    # Fraudulent claims (with different patterns)
    fraud_data = {
        'claim_id': [f'CLM-{i:06d}' for i in range(n_normal, n_samples)],
        'patient_id': [f'PAT-{np.random.randint(1, 5000):05d}' for _ in range(n_fraud)],
        'provider_id': [f'PROV-{np.random.randint(1, 500):04d}' for _ in range(n_fraud)],
        'service_date': [datetime.now() - timedelta(days=np.random.randint(0, 365)) for _ in range(n_fraud)],
        'claim_amount': np.random.lognormal(9, 1.0, n_fraud),  # Higher amounts
        'service_count': np.random.poisson(8, n_fraud) + 1,  # More services
        'patient_age': np.random.normal(50, 15, n_fraud),
        'provider_claim_frequency': np.random.uniform(1.0, 5.0, n_fraud),  # Higher frequency
        'diagnosis_code_count': np.random.poisson(5, n_fraud) + 1,  # More codes
        'procedure_code_count': np.random.poisson(7, n_fraud) + 1,
    }
    
    # Combine data
    all_data = {k: np.concatenate([normal_data[k], fraud_data[k]]) for k in normal_data.keys()}
    
    df = pd.DataFrame(all_data)
    
    # Add categorical features
    provider_types = ['Hospital', 'Clinic', 'Individual', 'Lab', 'Imaging Center']
    specialties = ['Cardiology', 'Orthopedics', 'General Practice', 'Internal Medicine', 
                   'Radiology', 'Pathology', 'Surgery', 'Emergency Medicine']
    places_of_service = ['Office', 'Hospital', 'Urgent Care', 'Emergency Room', 'Ambulatory Center']
    
    df['provider_type'] = np.random.choice(provider_types, n_samples)
    df['specialty'] = np.random.choice(specialties, n_samples)
    df['place_of_service'] = np.random.choice(places_of_service, n_samples)
    
    # Generate diagnosis and procedure codes
    diagnosis_codes = ['M54.5', 'I10', 'J06.9', 'R05', 'M25.551', 'G89.1', 'E11.9', 'F32.9', 'Z00.00', 'R07.9']
    procedure_codes = ['99203', '99213', '99214', '80053', '85025', '84443', '71020', '93000', '97110', '97035']
    
    df['diagnosis_codes'] = [', '.join(np.random.choice(diagnosis_codes, np.random.randint(1, 4))) 
                            for _ in range(n_samples)]
    df['procedure_codes'] = [', '.join(np.random.choice(procedure_codes, np.random.randint(1, 5))) 
                            for _ in range(n_samples)]
    
    # Add label for evaluation
    df['is_fraud'] = [False] * n_normal + [True] * n_fraud
    
    # Shuffle
    df = df.sample(frac=1, random_state=random_seed).reset_index(drop=True)
    
    # Clean up data types
    df['service_date'] = pd.to_datetime(df['service_date'])
    df['claim_amount'] = df['claim_amount'].round(2)
    df['patient_age'] = df['patient_age'].clip(18, 99).astype(int)
    df['service_count'] = df['service_count'].astype(int)
    df['diagnosis_code_count'] = df['diagnosis_code_count'].astype(int)
    df['procedure_code_count'] = df['procedure_code_count'].astype(int)
    
    return df


def main():
    parser = argparse.ArgumentParser(description='Generate sample healthcare claims data')
    parser.add_argument('--samples', type=int, default=10000,
                       help='Number of samples to generate')
    parser.add_argument('--fraud-ratio', type=float, default=0.05,
                       help='Ratio of fraudulent claims (0.0-1.0)')
    parser.add_argument('--output', type=str, default='data/raw/sample_claims.parquet',
                       help='Output file path')
    parser.add_argument('--format', type=str, default='parquet',
                       choices=['csv', 'parquet'],
                       help='Output file format')
    
    args = parser.parse_args()
    
    print(f"Generating {args.samples} sample claims with {args.fraud_ratio*100}% fraud rate...")
    
    df = generate_sample_claims(
        n_samples=args.samples,
        fraud_ratio=args.fraud_ratio
    )
    
    # Create output directory
    import os
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Save data
    if args.format == 'csv':
        df.to_csv(args.output, index=False)
    else:
        df.to_parquet(args.output, index=False)
    
    print(f"Sample data saved to: {args.output}")
    print(f"Shape: {df.shape}")
    print(f"Fraudulent claims: {df['is_fraud'].sum()} ({df['is_fraud'].sum()/len(df)*100:.2f}%)")
    print(f"Columns: {list(df.columns)}")


if __name__ == "__main__":
    main()
