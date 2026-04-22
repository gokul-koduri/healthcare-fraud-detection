"""
Provider Network Analysis
Analyzes provider networks to detect fraud rings and anomalous patterns
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import networkx as nx
from collections import Counter
from datetime import datetime, timedelta
from loguru import logger
import yaml


class ProviderNetworkAnalyzer:
    """
    Analyzes healthcare provider networks to detect fraud rings.
    
    Features:
    - Provider-patient network analysis
    - Referral pattern detection
    - Unusual clustering identification
    - Circular billing detection
    - Provider risk scoring
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the network analyzer."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        logger.info("ProviderNetworkAnalyzer initialized")
    
    def build_provider_patient_network(self, 
                                       claims_df: pd.DataFrame) -> nx.Graph:
        """
        Build a bipartite graph of providers and patients.
        
        Args:
            claims_df: DataFrame with claims data
            
        Returns:
            NetworkX Graph object
        """
        G = nx.Graph()
        
        # Add nodes with attributes
        for _, claim in claims_df.iterrows():
            provider_id = claim['provider_id']
            patient_id = claim['patient_id']
            claim_amount = claim['claim_amount']
            
            # Add provider node
            if not G.has_node(provider_id):
                G.add_node(
                    provider_id,
                    node_type='provider',
                    total_claims=0,
                    total_amount=0,
                    specialty=claim.get('specialty', 'Unknown')
                )
            
            # Add patient node
            if not G.has_node(patient_id):
                G.add_node(
                    patient_id,
                    node_type='patient',
                    total_claims=0,
                    total_amount=0
                )
            
            # Update node attributes
            G.nodes[provider_id]['total_claims'] += 1
            G.nodes[provider_id]['total_amount'] += claim_amount
            G.nodes[patient_id]['total_claims'] += 1
            G.nodes[patient_id]['total_amount'] += claim_amount
            
            # Add edge
            if G.has_edge(provider_id, patient_id):
                G[provider_id][patient_id]['claims'] += 1
                G[provider_id][patient_id]['total_amount'] += claim_amount
            else:
                G.add_edge(
                    provider_id,
                    patient_id,
                    claims=1,
                    total_amount=claim_amount,
                    service_date=claim['service_date']
                )
        
        logger.info(f"Built network with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        return G
    
    def detect_suspicious_clusters(self, 
                                   G: nx.Graph,
                                   min_cluster_size: int = 3,
                                   max_patient_ratio: float = 0.5) -> List[Dict]:
        """
        Detect suspicious provider clusters.
        
        Args:
            G: Network graph
            min_cluster_size: Minimum cluster size to flag
            max_patient_ratio: Maximum patient-to-provider ratio
            
        Returns:
            List of suspicious clusters
        """
        suspicious_clusters = []
        
        # Find connected components
        components = [c for c in nx.connected_components(G) if len(c) >= min_cluster_size]
        
        for component in components:
            subgraph = G.subgraph(component)
            
            # Count providers and patients
            providers = [n for n, d in subgraph.nodes(data=True) if d.get('node_type') == 'provider']
            patients = [n for n, d in subgraph.nodes(data=True) if d.get('node_type') == 'patient']
            
            patient_ratio = len(patients) / len(providers) if len(providers) > 0 else 0
            
            # Calculate cluster metrics
            total_amount = sum(
                subgraph.nodes[n]['total_amount'] 
                for n in providers
            )
            avg_claims_per_provider = np.mean([
                subgraph.nodes[n]['total_claims'] 
                for n in providers
            ])
            
            # Flag suspicious clusters
            flags = []
            if patient_ratio < max_patient_ratio:
                flags.append("Low patient-to-provider ratio (possible shell providers)")
            
            if avg_claims_per_provider > 50:
                flags.append(f"High claim volume per provider: {avg_claims_per_provider:.0f}")
            
            if total_amount > 100000:
                flags.append(f"High total amount: ${total_amount:,.0f}")
            
            # Check for high interconnectivity
            density = nx.density(subgraph)
            if density > 0.8:
                flags.append(f"High network density: {density:.2f} (possible fraud ring)")
            
            if flags:
                suspicious_clusters.append({
                    'cluster_id': f"CLUSTER-{len(suspicious_clusters) + 1}",
                    'num_providers': len(providers),
                    'num_patients': len(patients),
                    'patient_ratio': patient_ratio,
                    'total_amount': total_amount,
                    'avg_claims_per_provider': avg_claims_per_provider,
                    'density': density,
                    'flags': flags,
                    'providers': providers
                })
        
        logger.info(f"Detected {len(suspicious_clusters)} suspicious clusters")
        return suspicious_clusters
    
    def detect_circular_billing(self, 
                               claims_df: pd.DataFrame,
                               max_cycle_length: int = 5) -> List[Dict]:
        """
        Detect circular billing patterns (providers referring to each other).
        
        Args:
            claims_df: DataFrame with claims data
            max_cycle_length: Maximum cycle length to detect
            
        Returns:
            List of circular billing patterns
        """
        # Build provider network
        provider_graph = nx.DiGraph()
        
        # Find provider-patient-provider patterns
        for patient_id, patient_claims in claims_df.groupby('patient_id'):
            providers = patient_claims['provider_id'].unique()
            
            # Create edges between providers who see the same patient
            for i, provider1 in enumerate(providers):
                for provider2 in providers[i+1:]:
                    if provider_graph.has_edge(provider1, provider2):
                        provider_graph[provider1][provider2]['weight'] += 1
                        provider_graph[provider1][provider2]['shared_patients'].add(patient_id)
                    else:
                        provider_graph.add_edge(
                            provider1, provider2,
                            weight=1,
                            shared_patients={patient_id}
                        )
        
        # Find cycles
        circular_patterns = []
        
        try:
            cycles = list(nx.simple_cycles(provider_graph))
            cycles = [c for c in cycles if len(c) <= max_cycle_length]
            
            for cycle in cycles:
                # Calculate cycle metrics
                total_weight = 0
                shared_patient_count = 0
                
                for i in range(len(cycle)):
                    provider1 = cycle[i]
                    provider2 = cycle[(i + 1) % len(cycle)]
                    
                    if provider_graph.has_edge(provider1, provider2):
                        total_weight += provider_graph[provider1][provider2]['weight']
                        shared_patient_count += len(
                            provider_graph[provider1][provider2]['shared_patients']
                        )
                
                if total_weight >= 5:  # Minimum threshold
                    circular_patterns.append({
                        'cycle': cycle,
                        'cycle_length': len(cycle),
                        'total_shared_patients': shared_patient_count,
                        'avg_connections': total_weight / len(cycle),
                        'risk_score': min(100, total_weight * 10)
                    })
        
        except Exception as e:
            logger.error(f"Error detecting circular billing: {e}")
        
        logger.info(f"Detected {len(circular_patterns)} circular billing patterns")
        return circular_patterns
    
    def calculate_provider_centrality(self, 
                                     G: nx.Graph) -> pd.DataFrame:
        """
        Calculate centrality metrics for providers.
        
        Args:
            G: Network graph
            
        Returns:
            DataFrame with provider centrality metrics
        """
        # Get provider nodes
        providers = [
            n for n, d in G.nodes(data=True) 
            if d.get('node_type') == 'provider'
        ]
        
        # Create subgraph with only providers
        provider_subgraph = G.subgraph(providers)
        
        # Calculate centrality metrics
        metrics = []
        
        for provider in providers:
            degree = G.degree(provider)
            claims = G.nodes[provider]['total_claims']
            amount = G.nodes[provider]['total_amount']
            
            metrics.append({
                'provider_id': provider,
                'degree': degree,
                'claims': claims,
                'total_amount': amount,
                'avg_amount_per_claim': amount / claims if claims > 0 else 0,
                'specialty': G.nodes[provider].get('specialty', 'Unknown')
            })
        
        df = pd.DataFrame(metrics)
        
        # Calculate risk scores
        df['risk_score'] = (
            (df['degree'] / df['degree'].max() * 0.3 +
             df['claims'] / df['claims'].max() * 0.3 +
             df['total_amount'] / df['total_amount'].max() * 0.4) * 100
        )
        
        return df.sort_values('risk_score', ascending=False)
    
    def analyze_referral_patterns(self, 
                                 claims_df: pd.DataFrame) -> Dict:
        """
        Analyze referral patterns between providers.
        
        Args:
            claims_df: DataFrame with claims data
            
        Returns:
            Dictionary with referral pattern analysis
        """
        # Build provider adjacency
        provider_pairs = []
        
        for patient_id, patient_claims in claims_df.groupby('patient_id'):
            providers = patient_claims['provider_id'].unique()
            
            # Count provider pairs
            for i, provider1 in enumerate(providers):
                for provider2 in providers[i+1:]:
                    provider_pairs.append((provider1, provider2))
        
        # Count pair frequencies
        pair_counts = Counter(provider_pairs)
        
        # Find unusual patterns
        total_pairs = len(provider_pairs)
        unique_providers = claims_df['provider_id'].nunique()
        
        analysis = {
            'total_pairs': total_pairs,
            'unique_providers': unique_providers,
            'avg_pairs_per_provider': total_pairs / unique_providers if unique_providers > 0 else 0,
            'top_pairs': pair_counts.most_common(10),
            'unusual_patterns': []
        }
        
        # Flag patterns with very high frequency
        for (provider1, provider2), count in pair_counts.most_common(20):
            if count > 50:  # Threshold
                analysis['unusual_patterns'].append({
                    'providers': [provider1, provider2],
                    'shared_patients': count,
                    'reason': f"Unusually high shared patient count"
                })
        
        return analysis
    
    def generate_network_report(self, 
                               claims_df: pd.DataFrame,
                               output_path: str = "reports/network_analysis.txt") -> str:
        """
        Generate comprehensive network analysis report.
        
        Args:
            claims_df: DataFrame with claims data
            output_path: Path to save the report
            
        Returns:
            Report content as string
        """
        # Build network
        G = self.build_provider_patient_network(claims_df)
        
        # Run analyses
        suspicious_clusters = self.detect_suspicious_clusters(G)
        circular_patterns = self.detect_circular_billing(claims_df)
        provider_centrality = self.calculate_provider_centrality(G)
        referral_analysis = self.analyze_referral_patterns(claims_df)
        
        # Generate report
        report = f"""
{'='*80}
HEALTHCARE PROVIDER NETWORK ANALYSIS REPORT
{'='*80}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Analysis Period: Last {claims_df['service_date'].nunique()} unique dates

NETWORK OVERVIEW
{'-'*80}
Total Nodes: {G.number_of_nodes()}
  - Providers: {sum(1 for n, d in G.nodes(data=True) if d.get('node_type') == 'provider')}
  - Patients: {sum(1 for n, d in G.nodes(data=True) if d.get('node_type') == 'patient')}
Total Edges: {G.number_of_edges()}
Network Density: {nx.density(G):.4f}

SUSPICIOUS CLUSTERS DETECTED
{'-'*80}
"""
        
        if suspicious_clusters:
            for cluster in suspicious_clusters:
                report += f"""
{cluster['cluster_id']}
  Providers: {cluster['num_providers']}
  Patients: {cluster['num_patients']}
  Patient Ratio: {cluster['patient_ratio']:.2f}
  Total Amount: ${cluster['total_amount']:,.2f}
  Density: {cluster['density']:.2f}
  Flags:
"""
                for flag in cluster['flags']:
                    report += f"    - {flag}\n"
        else:
            report += "No suspicious clusters detected.\n"
        
        report += f"""
CIRCULAR BILLING PATTERNS
{'-'*80}
"""
        
        if circular_patterns:
            report += f"Detected {len(circular_patterns)} circular patterns:\n\n"
            for pattern in circular_patterns[:5]:  # Top 5
                report += f"""
Cycle: {' -> '.join(pattern['cycle'])}
  Length: {pattern['cycle_length']}
  Shared Patients: {pattern['total_shared_patients']}
  Risk Score: {pattern['risk_score']:.0f}
"""
        else:
            report += "No circular billing patterns detected.\n"
        
        report += f"""
HIGH-RISK PROVIDERS (Top 10)
{'-'*80}
"""
        
        for _, provider in provider_centrality.head(10).iterrows():
            report += f"""
Provider: {provider['provider_id']}
  Risk Score: {provider['risk_score']:.0f}
  Claims: {provider['claims']}
  Total Amount: ${provider['total_amount']:,.2f}
  Connections: {provider['degree']}
"""
        
        report += f"""
REFERRAL PATTERN ANALYSIS
{'-'*80}
Total Provider Pairs: {referral_analysis['total_pairs']}
Unique Providers: {referral_analysis['unique_providers']}
Avg Pairs per Provider: {referral_analysis['avg_pairs_per_provider']:.1f}

Unusual Patterns Detected: {len(referral_analysis['unusual_patterns'])}
"""
        
        # Save report
        with open(output_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Network analysis report saved to {output_path}")
        
        return report


if __name__ == "__main__":
    # Example usage
    analyzer = ProviderNetworkAnalyzer()
    
    # Create sample data
    sample_claims = pd.DataFrame({
        'claim_id': [f'CLM-{i}' for i in range(1000)],
        'provider_id': [f'PROV-{i % 50}' for i in range(1000)],
        'patient_id': [f'PAT-{i % 200}' for i in range(1000)],
        'service_date': ['2024-01-15'] * 1000,
        'claim_amount': np.random.uniform(100, 10000, 1000),
        'specialty': np.random.choice(['Cardiology', 'Orthopedics', 'General'], 1000)
    })
    
    # Generate report
    report = analyzer.generate_network_report(sample_claims)
    print(report)
