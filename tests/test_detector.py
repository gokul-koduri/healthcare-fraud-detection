"""
Unit tests for fraud detection models.
"""
import pytest
import numpy as np
import pandas as pd
import os
import sys

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anomaly_detection.isolation_forest_detector import IsolationForestDetector
from anomaly_detection.autoencoder_detector import AutoencoderDetector
from anomaly_detection.ensemble_detector import EnsembleDetector


@pytest.fixture
def sample_data():
    """Generate sample data for testing."""
    np.random.seed(42)
    n_samples = 500
    n_features = 20
    
    # Normal data
    X_normal = np.random.randn(n_samples, n_features)
    
    # Fraud data (outliers)
    X_fraud = np.random.randn(30, n_features) * 3 + 5
    
    X = np.vstack([X_normal, X_fraud])
    
    # Create dataframe
    df = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(n_features)])
    df['provider_type'] = np.random.choice(['A', 'B', 'C'], len(X))
    df['specialty'] = np.random.choice(['X', 'Y', 'Z'], len(X))
    
    return df


class TestIsolationForestDetector:
    """Tests for Isolation Forest detector."""
    
    def test_initialization(self):
        """Test detector initialization."""
        detector = IsolationForestDetector()
        assert detector.model is None
        assert detector.scaler is not None
    
    def test_preprocessing(self, sample_data):
        """Test data preprocessing."""
        detector = IsolationForestDetector()
        X = detector.preprocess_data(sample_data, fit=True)
        
        assert X.shape[0] == len(sample_data)
        assert detector.feature_names is not None
    
    def test_training(self, sample_data):
        """Test model training."""
        detector = IsolationForestDetector()
        X = detector.preprocess_data(sample_data, fit=True)
        
        metrics = detector.train(X)
        
        assert detector.model is not None
        assert 'fraud_ratio' in metrics
        assert 0 <= metrics['fraud_ratio'] <= 1
    
    def test_prediction(self, sample_data):
        """Test prediction."""
        detector = IsolationForestDetector()
        X = detector.preprocess_data(sample_data, fit=True)
        detector.train(X)
        
        predictions, probabilities = detector.predict(X[:100])
        
        assert len(predictions) == 100
        assert len(probabilities) == 100
        assert all(p in [-1, 1] for p in predictions)
        assert all(0 <= prob <= 1 for prob in probabilities)


class TestAutoencoderDetector:
    """Tests for Autoencoder detector."""
    
    def test_initialization(self):
        """Test detector initialization."""
        detector = AutoencoderDetector()
        assert detector.model is None
        assert detector.scaler is not None
    
    def test_model_building(self):
        """Test model building."""
        detector = AutoencoderDetector()
        model = detector.build_model(input_dim=50)
        
        assert model is not None
        assert model.input_shape == (None, 50)
    
    def test_training(self, sample_data):
        """Test model training with reduced epochs."""
        detector = AutoencoderDetector()
        # Reduce epochs for testing
        detector.ae_config['epochs'] = 2
        
        X = detector.preprocess_data(sample_data, fit=True)
        
        metrics = detector.train(X)
        
        assert detector.model is not None
        assert detector.threshold is not None
        assert 'threshold' in metrics
    
    def test_prediction(self, sample_data):
        """Test prediction."""
        detector = AutoencoderDetector()
        detector.ae_config['epochs'] = 2
        
        X = detector.preprocess_data(sample_data, fit=True)
        detector.train(X)
        
        predictions, mse = detector.predict(X[:100])
        
        assert len(predictions) == 100
        assert len(mse) == 100
        assert all(p in [-1, 1] for p in predictions)


class TestEnsembleDetector:
    """Tests for Ensemble detector."""
    
    def test_initialization(self):
        """Test ensemble initialization."""
        detector = EnsembleDetector()
        assert not detector.is_trained
        assert detector.if_detector is not None
        assert detector.ae_detector is not None
    
    def test_training(self, sample_data):
        """Test ensemble training."""
        detector = EnsembleDetector()
        
        # Reduce epochs for testing
        detector.ae_detector.ae_config['epochs'] = 2
        
        metrics = detector.train(sample_data)
        
        assert detector.is_trained
        assert 'isolation_forest' in metrics
        assert 'autoencoder' in metrics
    
    def test_prediction(self, sample_data):
        """Test ensemble prediction."""
        detector = EnsembleDetector()
        detector.ae_detector.ae_config['epochs'] = 2
        
        detector.train(sample_data)
        results = detector.predict(sample_data[:100])
        
        assert 'is_fraud' in results.columns
        assert 'ensemble_fraud_probability' in results.columns
        assert 'risk_level' in results.columns
        assert len(results) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
