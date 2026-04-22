"""
FastAPI REST API Server for Healthcare Fraud Detection
Provides endpoints for real-time fraud prediction and audit assistance
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import pandas as pd
import numpy as np
from datetime import datetime
import asyncio
from loguru import logger
import yaml
import os

# Add src to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anomaly_detection.ensemble_detector import EnsembleDetector
from genai.audit_assistant import AuditAssistant


# Initialize FastAPI app
app = FastAPI(
    title="Healthcare Claims Fraud Detection API",
    description="API for detecting fraudulent healthcare claims and generating audit reports",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for models
detector = None
assistant = None
config = None


# Pydantic models for API
class ClaimData(BaseModel):
    """Individual claim data structure"""
    claim_id: str
    patient_id: str
    provider_id: str
    service_date: str
    claim_amount: float = Field(gt=0)
    service_count: int = Field(gt=0)
    patient_age: int = Field(ge=18, le=99)
    provider_claim_frequency: float = Field(ge=0)
    diagnosis_code_count: int = Field(ge=0)
    procedure_code_count: int = Field(ge=0)
    provider_type: str
    specialty: str
    place_of_service: str
    diagnosis_codes: str
    procedure_codes: str
    services: Optional[str] = "Standard services"


class BatchClaimData(BaseModel):
    """Batch of claims for prediction"""
    claims: List[ClaimData]
    priority: Optional[str] = "normal"  # normal, high, urgent


class PredictionResponse(BaseModel):
    """Prediction response structure"""
    claim_id: str
    is_fraud: bool
    fraud_probability: float
    risk_level: str
    confidence_interval: Optional[List[float]] = None
    key_factors: Optional[List[str]] = None
    processing_time_ms: float


class BatchPredictionResponse(BaseModel):
    """Batch prediction response"""
    total_claims: int
    fraudulent_claims: int
    fraud_rate: float
    predictions: List[PredictionResponse]
    processing_time_seconds: float
    timestamp: str


class AuditReportRequest(BaseModel):
    """Request for audit report generation"""
    claim_ids: List[str]
    include_recommendations: bool = True
    include_checklist: bool = True
    report_format: str = "detailed"  # brief, detailed, full


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    models_loaded: bool
    timestamp: str
    version: str


class ModelMetricsResponse(BaseModel):
    """Model performance metrics"""
    false_positive_reduction: float
    efficiency_gain: float
    avg_prediction_time_ms: float
    uptime_hours: float
    total_predictions: int


# Startup event
@app.on_event("startup")
async def startup_event():
    """Load models on startup"""
    global detector, assistant, config
    
    logger.info("Starting API server...")
    
    # Load configuration
    config_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize models
    try:
        model_path = os.environ.get("MODEL_PATH", "models/ensemble_model_latest")
        detector = EnsembleDetector(config_path)
        
        if os.path.exists(f"{model_path}_isolation_forest.pkl"):
            detector.load_models(model_path)
            logger.info("Models loaded successfully")
        else:
            logger.warning(f"Model files not found at {model_path}. API will return dummy predictions.")
            detector = None
        
        # Initialize GenAI assistant
        assistant = AuditAssistant(config_path)
        
    except Exception as e:
        logger.error(f"Error loading models: {e}")
        detector = None
        assistant = None
    
    logger.info("API server started successfully")


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if detector is not None else "degraded",
        models_loaded=detector is not None,
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


# Predict single claim
@app.post("/api/v1/predict", response_model=PredictionResponse)
async def predict_claim(claim: ClaimData, background_tasks: BackgroundTasks):
    """Predict fraud for a single claim"""
    if detector is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    start_time = datetime.now()
    
    try:
        # Convert to DataFrame
        claim_df = pd.DataFrame([claim.dict()])
        
        # Make prediction
        results = detector.predict(claim_df)
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Extract results
        row = results.iloc[0]
        
        # Identify key factors (simplified)
        key_factors = []
        if row['claim_amount'] > 5000:
            key_factors.append("High claim amount")
        if row['service_count'] > 10:
            key_factors.append("High service count")
        if row['provider_claim_frequency'] > 3:
            key_factors.append("High provider frequency")
        
        return PredictionResponse(
            claim_id=claim.claim_id,
            is_fraud=bool(row['is_fraud']),
            fraud_probability=float(row['ensemble_fraud_probability']),
            risk_level=str(row['risk_level']),
            confidence_interval=[
                max(0, float(row['ensemble_fraud_probability']) - 0.1),
                min(1, float(row['ensemble_fraud_probability']) + 0.1)
            ],
            key_factors=key_factors,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Predict batch of claims
@app.post("/api/v1/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch_claims(batch: BatchClaimData):
    """Predict fraud for a batch of claims"""
    if detector is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    start_time = datetime.now()
    
    try:
        # Convert to DataFrame
        claims_data = [claim.dict() for claim in batch.claims]
        claims_df = pd.DataFrame(claims_data)
        
        # Make predictions
        results = detector.predict_batch(claims_df, batch_size=1000)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Build response
        predictions = []
        for idx, row in results.iterrows():
            pred = PredictionResponse(
                claim_id=row['claim_id'],
                is_fraud=bool(row['is_fraud']),
                fraud_probability=float(row['ensemble_fraud_probability']),
                risk_level=str(row['risk_level']),
                processing_time_ms=processing_time / len(results) * 1000
            )
            predictions.append(pred)
        
        fraud_count = sum(1 for p in predictions if p.is_fraud)
        
        return BatchPredictionResponse(
            total_claims=len(predictions),
            fraudulent_claims=fraud_count,
            fraud_rate=fraud_count / len(predictions),
            predictions=predictions,
            processing_time_seconds=processing_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Generate audit report
@app.post("/api/v1/audit/report")
async def generate_audit_report(request: AuditReportRequest):
    """Generate audit report for specified claims"""
    if assistant is None:
        raise HTTPException(status_code=503, detail="GenAI assistant not loaded")
    
    try:
        # This is a simplified version - in production, fetch claim details from database
        reports = []
        
        for claim_id in request.claim_ids:
            # Mock claim data - replace with actual database fetch
            claim_data = {
                'claim_id': claim_id,
                'patient_id': 'PAT-12345',
                'provider_id': 'PROV-67890',
                'service_date': '2024-01-15',
                'claim_amount': 7500.00,
                'services': 'Multiple procedures',
                'fraud_probability': 0.85,
                'risk_level': 'High',
                'anomalies': 'High amount, unusual service combination',
                'diagnosis_codes': 'M54.5, M25.551',
                'procedure_codes': '99203, 97110, 97035'
            }
            
            # Generate summary
            summary = assistant.generate_investigation_summary(claim_data)
            
            # Generate checklist if requested
            checklist = []
            if request.include_checklist:
                checklist = assistant.generate_audit_checklist(claim_data)
            
            reports.append({
                'claim_id': claim_id,
                'summary': summary,
                'checklist': checklist,
                'generated_at': datetime.now().isoformat()
            })
        
        return {
            'total_reports': len(reports),
            'reports': reports,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Get model metrics
@app.get("/api/v1/metrics", response_model=ModelMetricsResponse)
async def get_model_metrics():
    """Get model performance metrics"""
    # In production, fetch from monitoring system
    return ModelMetricsResponse(
        false_positive_reduction=28.0,
        efficiency_gain=35.0,
        avg_prediction_time_ms=50.0,
        uptime_hours=720.0,  # 30 days
        total_predictions=2500000
    )


# Get high-risk claims
@app.get("/api/v1/claims/high-risk")
async def get_high_risk_claims(
    limit: int = 100,
    min_probability: float = 0.7,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get high-risk claims for review"""
    # In production, query from database
    return {
        'total_high_risk': 150,
        'claims': [
            {
                'claim_id': 'CLM-001',
                'provider_id': 'PROV-123',
                'claim_amount': 12500.00,
                'fraud_probability': 0.92,
                'risk_level': 'Critical',
                'service_date': '2024-01-15'
            }
        ],
        'timestamp': datetime.now().isoformat()
    }


# Provider risk analysis
@app.get("/api/v1/providers/{provider_id}/risk")
async def get_provider_risk_analysis(provider_id: str):
    """Get risk analysis for a specific provider"""
    # In production, query from database
    return {
        'provider_id': provider_id,
        'risk_score': 75.5,
        'risk_category': 'High',
        'total_claims': 1250,
        'fraud_rate': 0.08,
        'avg_claim_amount': 4500.00,
        'high_value_claims': 45,
        'risk_factors': [
            'High claim frequency',
            'Above-average claim amounts',
            'Unusual procedure combinations'
        ],
        'recommendation': 'Schedule detailed audit',
        'timestamp': datetime.now().isoformat()
    }


# Background task for retraining
@app.post("/api/v1/models/retrain")
async def trigger_retraining(background_tasks: BackgroundTasks):
    """Trigger model retraining in background"""
    def retrain_task():
        logger.info("Starting background model retraining...")
        # In production, this would call the training script
        import subprocess
        subprocess.run(["python", "src/train_models.py"], cwd="/app")
        logger.info("Model retraining completed")
    
    background_tasks.add_task(retrain_task)
    
    return {
        'message': 'Retraining initiated',
        'status': 'in_progress',
        'estimated_time_minutes': 30
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
