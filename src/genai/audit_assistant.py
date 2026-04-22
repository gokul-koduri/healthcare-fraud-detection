"""
GenAI-powered Audit Assistant for Healthcare Claims
"""
import os
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import yaml
from loguru import logger
from openai import OpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.schema import HumanMessage, SystemMessage
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory


class AuditAssistant:
    """
    GenAI-powered audit assistant for generating claim investigation 
    summaries and compliance reports.
    
    Features:
    - Automated investigation summaries
    - Compliance report generation
    - Chat-based audit assistance
    - Risk-based recommendations
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the audit assistant."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.openai_config = self.config['openai']
        self.langchain_config = self.config['langchain']
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.openai_config['api_key'])
        
        # Initialize LangChain components
        self.llm = ChatOpenAI(
            model=self.openai_config['model'],
            temperature=self.openai_config['temperature'],
            max_tokens=self.openai_config['max_tokens'],
            api_key=self.openai_config['api_key']
        )
        
        self.embeddings = OpenAIEmbeddings(
            model=self.langchain_config['embedding_model'],
            api_key=self.openai_config['api_key']
        )
        
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        logger.info("AuditAssistant initialized")
    
    def generate_investigation_summary(self, claim_data: Dict) -> str:
        """
        Generate an investigation summary for a specific claim.
        
        Args:
            claim_data: Dictionary containing claim information
            
        Returns:
            Generated investigation summary
        """
        prompt = self._create_investigation_prompt(claim_data)
        
        response = self.client.chat.completions.create(
            model=self.openai_config['model'],
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=self.openai_config['temperature'],
            max_tokens=self.openai_config['max_tokens']
        )
        
        summary = response.choices[0].message.content
        logger.info(f"Generated investigation summary for claim {claim_data.get('claim_id')}")
        
        return summary
    
    def _create_investigation_prompt(self, claim_data: Dict) -> str:
        """Create a prompt for investigation summary generation."""
        prompt = f"""
Generate a comprehensive investigation summary for the following healthcare claim:

CLAIM DETAILS:
- Claim ID: {claim_data.get('claim_id', 'N/A')}
- Patient ID: {claim_data.get('patient_id', 'N/A')}
- Provider ID: {claim_data.get('provider_id', 'N/A')}
- Service Date: {claim_data.get('service_date', 'N/A')}
- Claim Amount: ${claim_data.get('claim_amount', 0):,.2f}
- Services Provided: {claim_data.get('services', 'N/A')}

FRAUD ANALYSIS:
- Fraud Probability: {claim_data.get('fraud_probability', 0):.2%}
- Risk Level: {claim_data.get('risk_level', 'N/A')}
- Anomalies Detected: {claim_data.get('anomalies', 'None')}

DIAGNOSIS & PROCEDURE CODES:
- Diagnosis Codes: {claim_data.get('diagnosis_codes', 'N/A')}
- Procedure Codes: {claim_data.get('procedure_codes', 'N/A')}

Please provide:
1. Summary of potential issues identified
2. Risk factors contributing to fraud probability
3. Recommended investigation steps
4. Documentation requirements
5. Follow-up actions needed
"""
        return prompt
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the audit assistant."""
        return """
You are an expert healthcare fraud investigator and auditor with 20+ years of experience. 
Your role is to analyze healthcare claims for potential fraud, waste, and abuse.

Key guidelines:
- Focus on regulatory compliance (CMS, HIPAA, ACA)
- Identify billing irregularities and suspicious patterns
- Reference relevant healthcare regulations
- Provide actionable recommendations
- Maintain professional, objective tone
- Consider provider history and patterns
- Evaluate medical necessity and documentation

Your analysis should help auditors:
- Prioritize high-risk claims
- Understand potential fraud schemes
- Conduct efficient investigations
- Ensure compliance with regulations
"""
    
    def generate_compliance_report(self, 
                                   claims_data: List[Dict],
                                   summary_stats: Dict) -> str:
        """
        Generate a comprehensive compliance report.
        
        Args:
            claims_data: List of claim dictionaries
            summary_stats: Summary statistics for the period
            
        Returns:
            Generated compliance report
        """
        prompt = self._create_compliance_prompt(claims_data, summary_stats)
        
        response = self.client.chat.completions.create(
            model=self.openai_config['model'],
            messages=[
                {"role": "system", "content": self._get_compliance_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=self.openai_config['temperature'],
            max_tokens=4000
        )
        
        report = response.choices[0].message.content
        logger.info("Generated compliance report")
        
        return report
    
    def _create_compliance_prompt(self, claims_data: List[Dict], 
                                 summary_stats: Dict) -> str:
        """Create a prompt for compliance report generation."""
        high_risk_claims = [c for c in claims_data if c.get('risk_level') in ['High', 'Critical']]
        
        prompt = f"""
Generate a comprehensive compliance report for the audit period.

PERIOD OVERVIEW:
- Period: {summary_stats.get('period', 'N/A')}
- Total Claims Reviewed: {summary_stats.get('total_claims', 0):,}
- Total Claim Amount: ${summary_stats.get('total_amount', 0):,.2f}
- Fraud Detection Rate: {summary_stats.get('fraud_rate', 0):.2%}

RISK DISTRIBUTION:
- Critical Risk: {summary_stats.get('critical_count', 0):,} claims
- High Risk: {summary_stats.get('high_count', 0):,} claims
- Medium Risk: {summary_stats.get('medium_count', 0):,} claims
- Low Risk: {summary_stats.get('low_count', 0):,} claims

KEY FINDINGS:
- False Positive Reduction: {summary_stats.get('fp_reduction', 0):.1f}%
- Audit Efficiency Improvement: {summary_stats.get('efficiency_gain', 0):.1f}%
- Estimated Savings: ${summary_stats.get('estimated_savings', 0):,.2f}

TOP FRAUD PATTERNS IDENTIFIED:
{self._format_fraud_patterns(summary_stats.get('fraud_patterns', []))}

HIGH-RISK CLAIMS SAMPLE:
{self._format_claims_sample(high_risk_claims[:5])}

Please provide a structured report including:
1. Executive Summary
2. Risk Analysis
3. Fraud Pattern Analysis
4. Compliance Recommendations
5. Action Items
6. Metrics & Performance
7. Next Steps
"""
        return prompt
    
    def _get_compliance_system_prompt(self) -> str:
        """Get the system prompt for compliance reporting."""
        return """
You are a senior healthcare compliance officer specializing in fraud detection and audit automation.
Generate professional, actionable compliance reports for healthcare organizations.

Your reports should:
- Follow healthcare compliance best practices
- Reference relevant regulations (CMS, HIPAA, False Claims Act)
- Provide data-driven insights
- Include actionable recommendations
- Highlight areas for improvement
- Track performance metrics
- Support decision-making processes
"""
    
    def _format_fraud_patterns(self, patterns: List[Dict]) -> str:
        """Format fraud patterns for the prompt."""
        if not patterns:
            return "No specific patterns identified"
        
        formatted = []
        for pattern in patterns[:5]:
            formatted.append(f"- {pattern.get('pattern', 'Unknown')}: "
                           f"{pattern.get('count', 0)} occurrences, "
                           f"${pattern.get('amount', 0):,.2f} involved")
        
        return "\n".join(formatted)
    
    def _format_claims_sample(self, claims: List[Dict]) -> str:
        """Format a sample of claims for the prompt."""
        if not claims:
            return "No high-risk claims to display"
        
        formatted = []
        for claim in claims:
            formatted.append(
                f"- Claim {claim.get('claim_id', 'N/A')}: "
                f"${claim.get('claim_amount', 0):,.2f}, "
                f"Risk: {claim.get('risk_level', 'N/A')}, "
                f"Provider: {claim.get('provider_id', 'N/A')}"
            )
        
        return "\n".join(formatted)
    
    def chat_assistant(self, query: str, context: Optional[str] = None) -> str:
        """
        Interactive chat assistant for audit questions.
        
        Args:
            query: User's question
            context: Optional context information
            
        Returns:
            Assistant's response
        """
        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=self._create_chat_query(query, context))
        ]
        
        response = self.llm(messages)
        return response.content
    
    def _create_chat_query(self, query: str, context: Optional[str]) -> str:
        """Create a formatted chat query."""
        if context:
            return f"""CONTEXT:
{context}

QUESTION:
{query}

Please provide a detailed, actionable response based on your expertise in healthcare fraud investigation."""
        return query
    
    def generate_audit_checklist(self, claim_data: Dict) -> List[str]:
        """
        Generate a customized audit checklist for a claim.
        
        Args:
            claim_data: Claim information
            
        Returns:
            List of audit checklist items
        """
        prompt = f"""
Generate a comprehensive audit checklist for reviewing the following claim:

Claim Amount: ${claim_data.get('claim_amount', 0):,.2f}
Services: {claim_data.get('services', 'N/A')}
Risk Level: {claim_data.get('risk_level', 'N/A')}
Fraud Probability: {claim_data.get('fraud_probability', 0):.2%}

Provide a numbered checklist of specific items to verify during the audit.
Focus on: documentation, medical necessity, billing compliance, and authorization.
"""
        
        response = self.client.chat.completions.create(
            model=self.openai_config['model'],
            messages=[
                {"role": "system", "content": "You are a healthcare audit expert. Generate specific, actionable audit checklists."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        checklist_text = response.choices[0].message.content
        
        # Parse checklist items
        items = [line.strip() for line in checklist_text.split('\n') 
                if line.strip() and (line[0].isdigit() or line.strip('-').startswith('-'))]
        
        return items


if __name__ == "__main__":
    # Example usage
    assistant = AuditAssistant()
    
    # Sample claim data
    claim_data = {
        'claim_id': 'CLM-2024-001234',
        'patient_id': 'PAT-12345',
        'provider_id': 'PROV-67890',
        'service_date': '2024-01-15',
        'claim_amount': 15000.00,
        'services': 'Comprehensive evaluation, multiple procedures',
        'fraud_probability': 0.85,
        'risk_level': 'High',
        'anomalies': 'High claim amount, unusual service combination',
        'diagnosis_codes': ['M54.5', 'M25.551'],
        'procedure_codes': ['99203', '97110', '97035']
    }
    
    # Generate investigation summary
    summary = assistant.generate_investigation_summary(claim_data)
    print("Investigation Summary:")
    print(summary)
    print("\n" + "="*80 + "\n")
    
    # Generate audit checklist
    checklist = assistant.generate_audit_checklist(claim_data)
    print("Audit Checklist:")
    for item in checklist:
        print(f"  {item}")
