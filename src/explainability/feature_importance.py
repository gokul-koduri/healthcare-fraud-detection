"""
Feature Importance and Explainability Module
Provides SHAP values, feature importance, and model explanations
"""
import numpy as np
import pandas as pd
import shap
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Tuple
import joblib
import yaml
from loguru import logger


class Explainer:
    """
    Model explainer for fraud detection predictions.
    
    Features:
    - SHAP values for local and global explanations
    - Feature importance ranking
    - Partial dependence plots
    - Individual prediction explanations
    """
    
    def __init__(self, model_path: str, config_path: str = "config/config.yaml"):
        """Initialize the explainer."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.model_path = model_path
        self.model = None
        self.explainer = None
        self.feature_names = None
        
        # Load model
        self._load_model()
        
        logger.info("Explainer initialized")
    
    def _load_model(self):
        """Load the trained model."""
        try:
            model_data = joblib.load(f"{self.model_path}_isolation_forest.pkl")
            self.model = model_data['model']
            self.feature_names = model_data['feature_names']
            
            # Initialize SHAP explainer
            # For tree-based models, use TreeExplainer
            self.explainer = shap.TreeExplainer(self.model)
            
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def get_feature_importance(self, 
                               X: pd.DataFrame,
                               n_top_features: int = 20) -> pd.DataFrame:
        """
        Get global feature importance.
        
        Args:
            X: Input features
            n_top_features: Number of top features to return
            
        Returns:
            DataFrame with feature importance scores
        """
        # Calculate SHAP values
        shap_values = self.explainer.shap_values(X)
        
        # Calculate mean absolute SHAP values for each feature
        if len(shap_values.shape) == 3:
            # Handle multi-class output
            mean_shap = np.mean(np.abs(shap_values), axis=(0, 2))
        else:
            mean_shap = np.mean(np.abs(shap_values), axis=0)
        
        # Create importance DataFrame
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': mean_shap
        }).sort_values('importance', ascending=False)
        
        return importance_df.head(n_top_features)
    
    def explain_prediction(self, 
                          X: pd.DataFrame,
                          sample_idx: int = 0) -> Dict:
        """
        Explain a single prediction.
        
        Args:
            X: Input features
            sample_idx: Index of the sample to explain
            
        Returns:
            Dictionary with explanation details
        """
        # Get SHAP values for the sample
        shap_values = self.explainer.shap_values(X.iloc[[sample_idx]])
        
        # Get base value (expected value)
        expected_value = self.explainer.expected_value
        
        # Get prediction
        prediction = self.model.predict(X.iloc[[sample_idx]])[0]
        prediction_proba = None
        if hasattr(self.model, 'predict_proba'):
            prediction_proba = self.model.predict_proba(X.iloc[[sample_idx]])[0]
        
        # Get feature contributions
        if len(shap_values.shape) == 3:
            shap_values_sample = shap_values[0, sample_idx, :]
        else:
            shap_values_sample = shap_values[sample_idx, :]
        
        # Create explanation
        explanation = {
            'prediction': int(prediction),
            'prediction_proba': float(prediction_proba[1]) if prediction_proba is not None else None,
            'expected_value': float(expected_value) if not isinstance(expected_value, np.ndarray) else float(expected_value[0]),
            'feature_contributions': []
        }
        
        # Sort features by absolute contribution
        for idx, (feature, value) in enumerate(zip(self.feature_names, shap_values_sample)):
            explanation['feature_contributions'].append({
                'feature': feature,
                'contribution': float(value),
                'feature_value': float(X.iloc[sample_idx, idx])
            })
        
        # Sort by absolute contribution
        explanation['feature_contributions'].sort(
            key=lambda x: abs(x['contribution']), 
            reverse=True
        )
        
        return explanation
    
    def plot_feature_importance(self, 
                                X: pd.DataFrame,
                                save_path: Optional[str] = None,
                                n_top_features: int = 20):
        """
        Plot feature importance.
        
        Args:
            X: Input features
            save_path: Path to save the plot
            n_top_features: Number of top features to show
        """
        importance_df = self.get_feature_importance(X, n_top_features)
        
        plt.figure(figsize=(12, 8))
        sns.barplot(
            data=importance_df.head(n_top_features),
            x='importance',
            y='feature',
            palette='viridis'
        )
        plt.title('Feature Importance (SHAP Values)', fontsize=16, fontweight='bold')
        plt.xlabel('Mean Absolute SHAP Value', fontsize=12)
        plt.ylabel('Feature', fontsize=12)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Feature importance plot saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_shap_summary(self, 
                         X: pd.DataFrame,
                         save_path: Optional[str] = None,
                         max_features: int = 50):
        """
        Plot SHAP summary plot.
        
        Args:
            X: Input features
            save_path: Path to save the plot
            max_features: Maximum number of features to show
        """
        shap_values = self.explainer.shap_values(X[:1000])  # Limit for performance
        
        plt.figure(figsize=(12, 10))
        shap.summary_plot(
            shap_values, 
            X[:1000],
            feature_names=self.feature_names,
            max_display=max_features,
            show=False
        )
        plt.title('SHAP Summary Plot', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"SHAP summary plot saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_shap_waterfall(self, 
                           X: pd.DataFrame,
                           sample_idx: int = 0,
                           save_path: Optional[str] = None):
        """
        Plot SHAP waterfall plot for a single prediction.
        
        Args:
            X: Input features
            sample_idx: Index of the sample to explain
            save_path: Path to save the plot
        """
        shap_values = self.explainer.shap_values(X.iloc[[sample_idx]])
        
        plt.figure(figsize=(12, 8))
        shap.waterfall_plot(
            shap.Explanation(
                values=shap_values[0, sample_idx] if len(shap_values.shape) == 2 else shap_values[0, sample_idx, 0],
                base_values=self.explainer.expected_value[0] if isinstance(self.explainer.expected_value, np.ndarray) else self.explainer.expected_value,
                data=X.iloc[sample_idx],
                feature_names=self.feature_names
            ),
            show=False
        )
        plt.title(f'SHAP Waterfall Plot - Claim {X.index[sample_idx]}', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"SHAP waterfall plot saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def get_explanation_summary(self, 
                                X: pd.DataFrame,
                                claim_ids: List[str]) -> pd.DataFrame:
        """
        Get explanation summary for multiple claims.
        
        Args:
            X: Input features
            claim_ids: List of claim IDs
            
        Returns:
            DataFrame with explanation summary
        """
        explanations = []
        
        for i, claim_id in enumerate(claim_ids):
            if i >= len(X):
                break
            
            explanation = self.explain_prediction(X, i)
            
            # Get top contributing features
            top_features = explanation['feature_contributions'][:5]
            
            explanations.append({
                'claim_id': claim_id,
                'prediction': explanation['prediction'],
                'probability': explanation['prediction_proba'],
                'top_factor_1': top_features[0]['feature'] if len(top_features) > 0 else None,
                'top_factor_2': top_features[1]['feature'] if len(top_features) > 1 else None,
                'top_factor_3': top_features[2]['feature'] if len(top_features) > 2 else None,
            })
        
        return pd.DataFrame(explanations)
    
    def create_explanation_report(self,
                                  X: pd.DataFrame,
                                  claim_ids: List[str],
                                  output_path: str = "reports/explanation_report.html"):
        """
        Create a comprehensive explanation report.
        
        Args:
            X: Input features
            claim_ids: List of claim IDs
            output_path: Path to save the report
        """
        # Get feature importance
        importance_df = self.get_feature_importance(X)
        
        # Get explanations for claims
        explanation_df = self.get_explanation_summary(X, claim_ids)
        
        # Create HTML report
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Fraud Detection Explanation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .fraud {{ color: #e74c3c; font-weight: bold; }}
        .legitimate {{ color: #27ae60; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Healthcare Claims Fraud Detection - Explanation Report</h1>
    <p><strong>Generated:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>Feature Importance (Global)</h2>
    <table>
        <tr><th>Rank</th><th>Feature</th><th>Importance</th></tr>
"""
        
        for idx, row in importance_df.iterrows():
            html_content += f"""
        <tr>
            <td>{idx + 1}</td>
            <td>{row['feature']}</td>
            <td>{row['importance']:.4f}</td>
        </tr>"""
        
        html_content += """
    </table>
    
    <h2>Individual Claim Explanations</h2>
    <table>
        <tr><th>Claim ID</th><th>Prediction</th><th>Top Factors</th></tr>
"""
        
        for _, row in explanation_df.iterrows():
            prediction_class = 'fraud' if row['prediction'] == 1 else 'legitimate'
            top_factors = ', '.join(filter(None, [
                row['top_factor_1'], row['top_factor_2'], row['top_factor_3']
            ]))
            
            html_content += f"""
        <tr>
            <td>{row['claim_id']}</td>
            <td class="{prediction_class}">{prediction_class.upper()}</td>
            <td>{top_factors}</td>
        </tr>"""
        
        html_content += """
    </table>
</body>
</html>
"""
        
        # Save report
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Explanation report saved to {output_path}")
        
        return output_path


if __name__ == "__main__":
    # Example usage
    explainer = Explainer("models/ensemble_model_20240101")
    
    # Create sample data
    sample_data = pd.DataFrame({
        'claim_amount': [5000, 12000, 3000],
        'service_count': [3, 15, 2],
        'patient_age': [45, 67, 34],
        'amount_per_service': [1666.67, 800.0, 1500.0],
        'provider_claim_frequency': [1.5, 4.2, 0.8],
        'diagnosis_per_service': [1.0, 0.67, 1.5],
        'procedure_per_service': [1.33, 1.0, 1.0]
    })
    
    # Get feature importance
    importance = explainer.get_feature_importance(sample_data)
    print("Feature Importance:")
    print(importance)
    
    # Explain a prediction
    explanation = explainer.explain_prediction(sample_data, 1)
    print(f"\nExplanation for claim 1:")
    print(explanation)
