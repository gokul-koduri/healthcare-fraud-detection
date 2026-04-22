"""
Alerting System for High-Risk Healthcare Claims
Sends real-time alerts when critical fraud is detected
"""
import os
import json
import boto3
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger
import yaml


class AlertManager:
    """
    Manages alerts for high-risk claims detection.
    
    Features:
    - Real-time alerts for critical claims
    - Digest summaries for batch processing
    - Multi-channel notifications (Email, Slack, PagerDuty)
    - Alert aggregation and deduplication
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the alert manager."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize AWS SNS for notifications
        self.sns_client = boto3.client('sns', region_name=self.config['aws']['region'])
        
        # Alert thresholds
        self.thresholds = {
            'critical': self.config['thresholds']['high_risk'],
            'high': self.config['thresholds']['medium_risk'],
            'medium': self.config['thresholds']['low_risk']
        }
        
        logger.info("AlertManager initialized")
    
    def send_critical_alert(self, claim_data: Dict) -> bool:
        """
        Send immediate alert for critical fraud detection.
        
        Args:
            claim_data: Dictionary with claim information
            
        Returns:
            True if alert sent successfully
        """
        try:
            # Format alert message
            message = self._format_alert_message(claim_data, level='critical')
            
            # Send SNS notification
            topic_arn = os.environ.get('CRITICAL_ALERT_TOPIC_ARN')
            if topic_arn:
                response = self.sns_client.publish(
                    TopicArn=topic_arn,
                    Message=message,
                    Subject=f"🚨 CRITICAL: Fraud Detected - Claim {claim_data['claim_id']}"
                )
                logger.info(f"Critical alert sent: {response['MessageId']}")
                return True
            
            # Fallback: Log alert
            logger.critical(f"CRITICAL FRAUD ALERT: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send critical alert: {e}")
            return False
    
    def send_digest_alert(self, 
                         high_risk_claims: List[Dict],
                         period: str = "Last 24 Hours") -> bool:
        """
        Send digest summary of high-risk claims.
        
        Args:
            high_risk_claims: List of high-risk claim dictionaries
            period: Time period for the digest
            
        Returns:
            True if alert sent successfully
        """
        try:
            # Format digest message
            message = self._format_digest_message(high_risk_claims, period)
            
            # Send email via SES
            ses_client = boto3.client('ses', region_name=self.config['aws']['region'])
            
            recipients = os.environ.get('ALERT_RECIPIENTS', '').split(',')
            
            response = ses_client.send_email(
                Source='fraud-alerts@company.com',
                Destination={'ToAddresses': recipients},
                Message={
                    'Subject': {'Data': f'📊 Fraud Detection Digest - {period}'},
                    'Body': {
                        'Text': {'Data': message},
                        'Html': {'Data': self._format_digest_html(high_risk_claims, period)}
                    }
                }
            )
            
            logger.info(f"Digest alert sent: {response['MessageId']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send digest alert: {e}")
            return False
    
    def send_slack_alert(self, 
                        claim_data: Dict,
                        webhook_url: Optional[str] = None) -> bool:
        """
        Send alert to Slack channel.
        
        Args:
            claim_data: Dictionary with claim information
            webhook_url: Slack webhook URL
            
        Returns:
            True if alert sent successfully
        """
        try:
            import requests
            
            webhook_url = webhook_url or os.environ.get('SLACK_WEBHOOK_URL')
            if not webhook_url:
                logger.warning("Slack webhook URL not configured")
                return False
            
            # Format Slack message
            color = 'danger' if claim_data.get('risk_level') == 'Critical' else 'warning'
            
            slack_message = {
                "attachments": [{
                    "color": color,
                    "title": f"⚠️ Fraud Alert: Claim {claim_data['claim_id']}",
                    "fields": [
                        {"title": "Provider", "value": claim_data.get('provider_id', 'N/A'), "short": True},
                        {"title": "Amount", "value": f"${claim_data.get('claim_amount', 0):,.2f}", "short": True},
                        {"title": "Risk Level", "value": claim_data.get('risk_level', 'Unknown'), "short": True},
                        {"title": "Probability", "value": f"{claim_data.get('fraud_probability', 0):.1%}", "short": True},
                        {"title": "Service Date", "value": claim_data.get('service_date', 'N/A'), "short": True},
                    ],
                    "footer": "Healthcare Fraud Detection System",
                    "ts": int(datetime.now().timestamp())
                }]
            }
            
            response = requests.post(webhook_url, json=slack_message)
            response.raise_for_status()
            
            logger.info("Slack alert sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    def trigger_pagerduty(self, 
                         claim_data: Dict,
                         severity: str = 'error') -> bool:
        """
        Trigger PagerDuty alert for critical incidents.
        
        Args:
            claim_data: Dictionary with claim information
            severity: Alert severity (critical, error, warning, info)
            
        Returns:
            True if alert triggered successfully
        """
        try:
            import requests
            
            pagerduty_api_key = os.environ.get('PAGERDUTY_API_KEY')
            pagerduty_integration_key = os.environ.get('PAGERDUTY_INTEGRATION_KEY')
            
            if not pagerduty_api_key or not pagerduty_integration_key:
                logger.warning("PagerDuty not configured")
                return False
            
            # Create PagerDuty event
            event = {
                "routing_key": pagerduty_integration_key,
                "event_action": "trigger",
                "payload": {
                    "summary": f"Critical Fraud Detected - Claim {claim_data['claim_id']}",
                    "severity": severity,
                    "source": "healthcare-fraud-detection",
                    "custom_details": claim_data
                },
                "dedup_key": claim_data['claim_id']  # Prevent duplicate alerts
            }
            
            response = requests.post(
                'https://events.pagerduty.com/v2/enqueue',
                json=event,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            
            logger.info("PagerDuty alert triggered")
            return True
            
        except Exception as e:
            logger.error(f"Failed to trigger PagerDuty: {e}")
            return False
    
    def _format_alert_message(self, claim_data: Dict, level: str = 'critical') -> str:
        """Format alert message for notifications."""
        emoji = "🚨" if level == 'critical' else "⚠️"
        
        message = f"""
{emoji} HEALTHCARE CLAIMS FRAUD ALERT {emoji.upper()}

CLAIM DETAILS:
  Claim ID: {claim_data.get('claim_id', 'N/A')}
  Provider: {claim_data.get('provider_id', 'N/A')}
  Patient: {claim_data.get('patient_id', 'N/A')}
  Service Date: {claim_data.get('service_date', 'N/A')}
  Claim Amount: ${claim_data.get('claim_amount', 0):,.2f}

FRAUD ANALYSIS:
  Risk Level: {claim_data.get('risk_level', 'Unknown')}
  Fraud Probability: {claim_data.get('fraud_probability', 0):.2%}
  Confidence: High

KEY RISK FACTORS:
"""
        # Add risk factors
        if claim_data.get('high_amount_flag'):
            message += "  • High claim amount ($5,000+)\n"
        if claim_data.get('high_service_flag'):
            message += "  • High service count (10+)\n"
        if claim_data.get('provider_claim_frequency', 0) > 3:
            message += "  • High provider claim frequency\n"
        if claim_data.get('amount_vs_provider_avg', 0) > 1000:
            message += "  • Amount significantly above provider average\n"
        
        message += f"""
IMMEDIATE ACTION REQUIRED:
  → Review claim documentation
  → Verify medical necessity
  → Contact provider for clarification
  → Consider referral to SIU

Alert generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return message
    
    def _format_digest_message(self, claims: List[Dict], period: str) -> str:
        """Format digest message for email notifications."""
        total_claims = len(claims)
        total_amount = sum(c.get('claim_amount', 0) for c in claims)
        critical_count = sum(1 for c in claims if c.get('risk_level') == 'Critical')
        high_count = sum(1 for c in claims if c.get('risk_level') == 'High')
        
        message = f"""
HEALTHCARE CLAIMS FRAUD DETECTION DIGEST
Period: {period}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
  Total High-Risk Claims: {total_claims}
  Total Amount at Risk: ${total_amount:,.2f}
  Critical Risk: {critical_count}
  High Risk: {high_count}

TOP 5 HIGH-RISK CLAIMS:
"""
        
        for i, claim in enumerate(sorted(claims, key=lambda x: x.get('fraud_probability', 0), reverse=True)[:5], 1):
            message += f"""
{i}. Claim {claim.get('claim_id', 'N/A')}
   Provider: {claim.get('provider_id', 'N/A')}
   Amount: ${claim.get('claim_amount', 0):,.2f}
   Risk: {claim.get('risk_level', 'Unknown')} ({claim.get('fraud_probability', 0):.1%})
   Date: {claim.get('service_date', 'N/A')}
"""
        
        message += """
RECOMMENDED ACTIONS:
  → Prioritize Critical and High-risk claims for review
  → Schedule provider audits for repeat offenders
  → Update fraud detection patterns
  → Review compliance with CMS guidelines

This is an automated message from the Healthcare Fraud Detection System.
"""
        return message
    
    def _format_digest_html(self, claims: List[Dict], period: str) -> str:
        """Format digest message as HTML."""
        total_claims = len(claims)
        total_amount = sum(c.get('claim_amount', 0) for c in claims)
        
        html = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: #e74c3c; color: white; padding: 20px; text-align: center; }}
        .summary {{ background: #f8f9fa; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #3498db; color: white; padding: 10px; text-align: left; }}
        td {{ border: 1px solid #ddd; padding: 10px; }}
        .critical {{ color: #e74c3c; font-weight: bold; }}
        .high {{ color: #e67e22; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>⚠️ Healthcare Claims Fraud Detection Digest</h1>
        <p>Period: {period} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total High-Risk Claims:</strong> {total_claims:,}</p>
        <p><strong>Total Amount at Risk:</strong> ${total_amount:,.2f}</p>
        <p><strong>Critical Risk:</strong> {sum(1 for c in claims if c.get('risk_level') == 'Critical')}</p>
        <p><strong>High Risk:</strong> {sum(1 for c in claims if c.get('risk_level') == 'High')}</p>
    </div>
    
    <h2>Top 10 High-Risk Claims</h2>
    <table>
        <tr>
            <th>Claim ID</th>
            <th>Provider</th>
            <th>Amount</th>
            <th>Risk Level</th>
            <th>Probability</th>
            <th>Service Date</th>
        </tr>
"""
        
        for claim in sorted(claims, key=lambda x: x.get('fraud_probability', 0), reverse=True)[:10]:
            risk_class = claim.get('risk_level', '').lower()
            html += f"""
        <tr>
            <td>{claim.get('claim_id', 'N/A')}</td>
            <td>{claim.get('provider_id', 'N/A')}</td>
            <td>${claim.get('claim_amount', 0):,.2f}</td>
            <td class="{risk_class}">{claim.get('risk_level', 'Unknown')}</td>
            <td>{claim.get('fraud_probability', 0):.1%}</td>
            <td>{claim.get('service_date', 'N/A')}</td>
        </tr>"""
        
        html += """
    </table>
    
    <p><em>This is an automated message from the Healthcare Fraud Detection System.</em></p>
</body>
</html>
"""
        return html
    
    def check_and_alert(self, predictions: pd.DataFrame) -> Dict[str, int]:
        """
        Check predictions and send alerts as needed.
        
        Args:
            predictions: DataFrame with prediction results
            
        Returns:
            Dictionary with alert counts by level
        """
        alert_counts = {'critical': 0, 'high': 0, 'medium': 0}
        
        # Check for critical claims
        critical_claims = predictions[predictions['risk_level'] == 'Critical']
        if len(critical_claims) > 0:
            for _, claim in critical_claims.iterrows():
                self.send_critical_alert(claim.to_dict())
                self.send_slack_alert(claim.to_dict())
                if claim.get('fraud_probability', 0) > 0.9:
                    self.trigger_pagerduty(claim.to_dict(), severity='critical')
            alert_counts['critical'] = len(critical_claims)
        
        # Check for high-risk claims
        high_claims = predictions[predictions['risk_level'] == 'High']
        if len(high_claims) > 0:
            for _, claim in high_claims.head(5).iterrows():  # Limit to 5 for batch
                self.send_slack_alert(claim.to_dict())
            alert_counts['high'] = len(high_claims)
        
        # Send digest if significant volume
        total_high_risk = len(critical_claims) + len(high_claims)
        if total_high_risk >= 10:
            high_risk_data = pd.concat([critical_claims, high_claims]).to_dict('records')
            self.send_digest_alert(high_risk_data)
        
        return alert_counts


if __name__ == "__main__":
    # Example usage
    alert_manager = AlertManager()
    
    # Test critical alert
    test_claim = {
        'claim_id': 'CLM-TEST-001',
        'provider_id': 'PROV-TEST',
        'patient_id': 'PAT-TEST',
        'service_date': '2024-01-15',
        'claim_amount': 15000.00,
        'fraud_probability': 0.92,
        'risk_level': 'Critical',
        'high_amount_flag': True,
        'high_service_flag': True,
        'provider_claim_frequency': 4.5
    }
    
    # Send alert
    alert_manager.send_critical_alert(test_claim)
    print("Critical alert sent")
