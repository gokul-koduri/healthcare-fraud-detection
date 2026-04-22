"""
Monitoring and Metrics Collection for Healthcare Fraud Detection
Tracks system performance, model accuracy, and operational metrics
"""
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import pandas as pd
import numpy as np
from loguru import logger
import yaml


class MetricsCollector:
    """
    Collects and tracks metrics for the fraud detection system.
    
    Features:
    - Prometheus metrics integration
    - Performance monitoring
    - Model accuracy tracking
    - Operational metrics
    - Alerting on threshold breaches
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the metrics collector."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Prometheus metrics
        self._init_prometheus_metrics()
        
        # In-memory metrics storage
        self.metrics_history = []
        
        logger.info("MetricsCollector initialized")
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics."""
        # Prediction metrics
        self.predictions_total = Counter(
            'fraud_detection_predictions_total',
            'Total number of predictions made',
            ['model_type', 'risk_level']
        )
        
        self.prediction_duration = Histogram(
            'fraud_detection_prediction_duration_seconds',
            'Time spent making predictions',
            buckets=[0.001, 0.01, 0.1, 1.0, 10.0]
        )
        
        # Model performance metrics
        self.false_positive_rate = Gauge(
            'fraud_detection_false_positive_rate',
            'Current false positive rate'
        )
        
        self.false_negative_rate = Gauge(
            'fraud_detection_false_negative_rate',
            'Current false negative rate'
        )
        
        self.detection_accuracy = Gauge(
            'fraud_detection_detection_accuracy',
            'Model detection accuracy'
        )
        
        # System metrics
        self.active_claims = Gauge(
            'fraud_detection_active_claims',
            'Number of claims currently being processed'
        )
        
        self.high_risk_claims = Gauge(
            'fraud_detection_high_risk_claims',
            'Number of high-risk claims detected'
        )
        
        self.estimated_savings = Gauge(
            'fraud_detection_estimated_savings_dollars',
            'Estimated savings from fraud detection'
        )
        
        # Database metrics
        self.db_query_duration = Histogram(
            'fraud_detection_db_query_duration_seconds',
            'Database query duration',
            ['query_type']
        )
        
        self.api_request_duration = Histogram(
            'fraud_detection_api_request_duration_seconds',
            'API request duration',
            ['endpoint']
        )
        
        # GenAI metrics
        self.genai_requests_total = Counter(
            'fraud_detection_genai_requests_total',
            'Total GenAI API requests',
            ['request_type']
        )
        
        self.genai_token_usage = Counter(
            'fraud_detection_genai_tokens_total',
            'Total GenAI tokens used',
            ['model']
        )
    
    def record_prediction(self, 
                         prediction_time: float,
                         num_predictions: int,
                         risk_levels: Dict[str, int]):
        """
        Record prediction metrics.
        
        Args:
            prediction_time: Time taken for predictions
            num_predictions: Number of predictions made
            risk_levels: Dictionary of risk level counts
        """
        self.prediction_duration.observe(prediction_time)
        
        for risk_level, count in risk_levels.items():
            self.predictions_total.labels(
                model_type='ensemble',
                risk_level=risk_level
            ).inc(count)
        
        # Record in history
        self.metrics_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'prediction',
            'duration': prediction_time,
            'count': num_predictions,
            'risk_levels': risk_levels
        })
        
        logger.debug(f"Recorded prediction metrics: {num_predictions} predictions in {prediction_time:.2f}s")
    
    def update_model_performance(self, 
                                accuracy: float,
                                false_positive_rate: float,
                                false_negative_rate: float):
        """
        Update model performance metrics.
        
        Args:
            accuracy: Model accuracy
            false_positive_rate: False positive rate
            false_negative_rate: False negative rate
        """
        self.detection_accuracy.set(accuracy)
        self.false_positive_rate.set(false_positive_rate)
        self.false_negative_rate.set(false_negative_rate)
        
        logger.info(f"Model performance - Accuracy: {accuracy:.3f}, "
                   f"FPR: {false_positive_rate:.3f}, FNR: {false_negative_rate:.3f}")
    
    def update_claim_metrics(self, 
                           active_claims: int,
                           high_risk_claims: int,
                           estimated_savings: float):
        """
        Update claim-related metrics.
        
        Args:
            active_claims: Number of active claims
            high_risk_claims: Number of high-risk claims
            estimated_savings: Estimated dollar savings
        """
        self.active_claims.set(active_claims)
        self.high_risk_claims.set(high_risk_claims)
        self.estimated_savings.set(estimated_savings)
        
        logger.debug(f"Claims - Active: {active_claims}, High-risk: {high_risk_claims}, "
                    f"Savings: ${estimated_savings:,.0f}")
    
    def record_db_query(self, query_type: str, duration: float):
        """Record database query metrics."""
        self.db_query_duration.labels(query_type=query_type).observe(duration)
    
    def record_api_request(self, endpoint: str, duration: float):
        """Record API request metrics."""
        self.api_request_duration.labels(endpoint=endpoint).observe(duration)
    
    def record_genai_request(self, request_type: str, tokens: int):
        """Record GenAI API usage."""
        self.genai_requests_total.labels(request_type=request_type).inc()
        self.genai_token_usage.labels(model='gpt-4').inc(tokens)
    
    def get_metrics_summary(self, hours: int = 24) -> Dict:
        """
        Get summary of metrics for the last N hours.
        
        Args:
            hours: Number of hours to summarize
            
        Returns:
            Dictionary with metrics summary
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m['timestamp']) > cutoff_time
        ]
        
        # Calculate summary statistics
        summary = {
            'period_hours': hours,
            'total_predictions': 0,
            'avg_prediction_time': 0,
            'risk_level_distribution': {},
            'metrics_count': len(recent_metrics)
        }
        
        if recent_metrics:
            prediction_metrics = [m for m in recent_metrics if m['type'] == 'prediction']
            
            if prediction_metrics:
                summary['total_predictions'] = sum(m['count'] for m in prediction_metrics)
                summary['avg_prediction_time'] = np.mean([m['duration'] for m in prediction_metrics])
                
                # Aggregate risk levels
                for m in prediction_metrics:
                    for risk_level, count in m['risk_levels'].items():
                        summary['risk_level_distribution'][risk_level] = \
                            summary['risk_level_distribution'].get(risk_level, 0) + count
        
        return summary
    
    def start_prometheus_server(self, port: int = 8000):
        """
        Start Prometheus HTTP server.
        
        Args:
            port: Port to listen on
        """
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")


class PerformanceMonitor:
    """
    Monitors system performance and generates alerts.
    
    Features:
    - Latency tracking
    - Throughput monitoring
    - Error rate tracking
    - Resource usage monitoring
    """
    
    def __init__(self):
        """Initialize the performance monitor."""
        self.latency_samples = []
        self.error_count = 0
        self.request_count = 0
        self.start_time = time.time()
    
    def record_request(self, latency: float, success: bool):
        """
        Record a request.
        
        Args:
            latency: Request latency in seconds
            success: Whether the request was successful
        """
        self.latency_samples.append(latency)
        self.request_count += 1
        
        if not success:
            self.error_count += 1
    
    def get_performance_metrics(self) -> Dict:
        """
        Get current performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        uptime = time.time() - self.start_time
        
        return {
            'uptime_seconds': uptime,
            'total_requests': self.request_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / self.request_count if self.request_count > 0 else 0,
            'requests_per_second': self.request_count / uptime if uptime > 0 else 0,
            'avg_latency': np.mean(self.latency_samples) if self.latency_samples else 0,
            'p50_latency': np.percentile(self.latency_samples, 50) if self.latency_samples else 0,
            'p95_latency': np.percentile(self.latency_samples, 95) if self.latency_samples else 0,
            'p99_latency': np.percentile(self.latency_samples, 99) if self.latency_samples else 0
        }
    
    def check_thresholds(self, 
                        max_error_rate: float = 0.05,
                        max_p95_latency: float = 1.0) -> Dict[str, bool]:
        """
        Check if performance thresholds are breached.
        
        Args:
            max_error_rate: Maximum acceptable error rate
            max_p95_latency: Maximum acceptable P95 latency
            
        Returns:
            Dictionary with threshold check results
        """
        metrics = self.get_performance_metrics()
        
        return {
            'error_rate_ok': metrics['error_rate'] <= max_error_rate,
            'latency_ok': metrics['p95_latency'] <= max_p95_latency,
            'overall_ok': (metrics['error_rate'] <= max_error_rate and 
                          metrics['p95_latency'] <= max_p95_latency)
        }


if __name__ == "__main__":
    # Example usage
    metrics = MetricsCollector()
    
    # Start Prometheus server
    metrics.start_prometheus_server(port=8000)
    
    # Simulate some predictions
    for i in range(100):
        prediction_time = np.random.uniform(0.01, 0.5)
        risk_levels = {
            'Low': np.random.randint(80, 95),
            'Medium': np.random.randint(5, 15),
            'High': np.random.randint(1, 5),
            'Critical': np.random.randint(0, 2)
        }
        
        metrics.record_prediction(prediction_time, 100, risk_levels)
    
    # Get summary
    summary = metrics.get_metrics_summary(hours=1)
    print(f"Metrics Summary: {summary}")
    
    # Performance monitor
    perf_monitor = PerformanceMonitor()
    
    for i in range(1000):
        latency = np.random.uniform(0.01, 2.0)
        success = np.random.random() > 0.02  # 2% error rate
        perf_monitor.record_request(latency, success)
    
    perf_metrics = perf_monitor.get_performance_metrics()
    print(f"\nPerformance Metrics: {perf_metrics}")
    
    threshold_check = perf_monitor.check_thresholds()
    print(f"\nThreshold Check: {threshold_check}")
