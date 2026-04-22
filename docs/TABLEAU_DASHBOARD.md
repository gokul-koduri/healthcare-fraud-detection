# Tableau Dashboard Guide - Healthcare Claims Fraud Detection

## Overview

This document describes the Tableau dashboards for visualizing fraud detection results and audit metrics.

## Dashboard Structure

### 1. Executive Summary Dashboard
**Purpose**: High-level overview for stakeholders

**Key Metrics**:
- Total claims processed
- Fraud detection rate
- Estimated savings
- False positive reduction
- Audit efficiency gain

**Visualizations**:
- KPI cards with sparklines
- Fraud rate trend (line chart)
- Risk distribution (donut chart)
- Savings waterfall chart

**Data Sources**:
- `fraud_detection_summary` (dbt model)
- MLflow metrics

### 2. Risk Analysis Dashboard
**Purpose**: Detailed risk analysis for auditors

**Key Metrics**:
- Claims by risk level
- Provider risk scores
- High-risk claim trends
- Geographical hotspots

**Visualizations**:
- Risk level bar chart
- Provider risk heatmap
- Claim amount distribution (box plot)
- Geographic map of fraud hotspots
- Time series of high-risk claims

**Data Sources**:
- `fact_claims_enriched` (dbt model)
- `dim_providers` (dbt model)

### 3. Provider Analysis Dashboard
**Purpose**: Monitor provider-level patterns

**Key Metrics**:
- Provider fraud rate
- Claim frequency by provider
- Average claim amount vs. peers
- Provider specialty comparison

**Visualizations**:
- Provider ranking table
- Specialty comparison (treemap)
- Provider behavior scatter plot
- Claim amount distribution by provider

**Data Sources**:
- `dim_providers` (dbt model)
- `fact_claims_enriched` (dbt model)

### 4. Pattern Detection Dashboard
**Purpose**: Identify fraud patterns and trends

**Key Metrics**:
- Common fraud patterns
- Code combinations frequency
- Service utilization anomalies
- Billing irregularities

**Visualizations**:
- Pattern frequency bar chart
- Diagnosis/procedure code heatmap
- Network diagram of provider-patient relationships
- Anomaly timeline

**Data Sources**:
- `fact_claims_enriched` (dbt model)
- Prediction results from S3

## Tableau Data Connection Setup

### Snowflake Connection
```
Connection Type: Snowflake
Server: your_account.snowflakecomputing.com
Role: transform_role
Warehouse: transform_wh
Database: healthcare_claims
Schema: fraud_detection
Authentication: Username/Password
```

### S3 Connection (for prediction results)
```
Connection Type: Amazon S3
Access Key: AWS_ACCESS_KEY_ID
Secret Key: AWS_SECRET_ACCESS_KEY
Bucket: healthcare-claims-data
File Path: processed/*.parquet
```

## Dashboard Calculations

### Key Calculated Fields

**Fraud Rate**:
```
[SUM([is_fraud])] / [COUNT([claim_id])]
```

**Estimated Savings**:
```
[SUM(IIF([is_fraud] = TRUE, [claim_amount], 0))]
```

**False Positive Reduction**:
```
28.0  // From model metrics
```

**Risk Score**:
```
CASE [risk_level]
  WHEN 'Critical' THEN 4
  WHEN 'High' THEN 3
  WHEN 'Medium' THEN 2
  WHEN 'Low' THEN 1
END
```

**Provider Z-Score**:
```
([claim_amount] - [AVG claim amount by provider]) / [STDEV claim amount by provider]
```

### Sets for Filtering

**High-Risk Claims**:
```
IF [ensemble_fraud_probability] >= 0.7 THEN "High Risk"
ELSE "Normal Risk"
END
```

**Outlier Providers**:
```
IF ABS([Provider Z-Score]) > 3 THEN "Outlier"
ELSE "Normal"
END
```

## Dashboard Layout Examples

### Layout 1: Executive Summary
```
┌─────────────────────────────────────────────────────────────────┐
│  Title: Healthcare Claims Fraud Detection - Executive Summary    │
├─────────────┬─────────────┬─────────────┬─────────────────────┤
│ Total Claims│ Fraud Rate  │ Savings     │ FP Reduction        │
│ 2,450,123   │ 4.2%        │ $12.5M      │ 28%                 │
├─────────────┴─────────────┴─────────────┴─────────────────────┤
│                                                                   │
│  [Fraud Rate Trend - Line Chart - Last 90 Days]                  │
│                                                                   │
├─────────────────────────────────┬───────────────────────────────┤
│  [Risk Distribution - Donut]     │  [Top Fraud Patterns - Bar]   │
│                                   │                               │
└─────────────────────────────────┴───────────────────────────────┘
```

### Layout 2: Risk Analysis
```
┌─────────────────────────────────────────────────────────────────┐
│  Title: Risk Analysis Dashboard                                  │
├─────────────────────────────────────────────────────────────────┤
│  Filters: [Date Range] [Provider Type] [Specialty] [Risk Level] │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [Claims by Risk Level - Stacked Bar - by Date]                  │
│                                                                   │
├─────────────────────────────┬───────────────────────────────────┤
│  [Provider Risk Heatmap]     │  [Claim Amount Distribution]       │
│                              │  by Risk Level - Box Plot          │
├─────────────────────────────┴───────────────────────────────────┤
│                                                                   │
│  [Fraud Probability Distribution - Histogram]                     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Dashboard Interactivity

### Actions & Filters
- **Click on risk category**: Drills down to detailed claims view
- **Click on provider**: Filters to provider-specific analysis
- **Date range selector**: Updates all time-series charts
- **Specialty filter**: Compares fraud rates across specialties

### Tooltips
Hover over any element to see:
- Claim ID
- Provider details
- Patient demographics (sanitized)
- Fraud probability score
- Contributing risk factors

### Drill-Down Paths
1. Executive Summary → Risk Analysis → Individual Claims
2. Provider Analysis → Provider Details → Claim History
3. Pattern Detection → Specific Pattern → Affected Claims

## Refresh Schedule

### Data Refresh
- **Live Connection**: Snowflake tables (auto-refresh)
- **Extract Refresh**: Hourly for prediction results
- **Full Refresh**: Daily at 2 AM UTC

### Performance Optimization
- Use data extracts for large datasets
- Incremental refresh for S3 data
- Materialized views for aggregations

## Dashboard Permissions

### User Roles
- **Executive**: View-only access to Executive Summary
- **Auditor**: Full access to Risk Analysis and Provider dashboards
- **Analyst**: Full access to all dashboards + export rights
- **Admin**: Full access + edit permissions

### Row-Level Security
```
// Example: Restrict by region
[REGION] = [USERNAME Region]
```

## Published Dashboards

### Tableau Server/Online
- **Project**: Healthcare Analytics
- **Site**: Fraud Detection
- **URL**: tableau.company.com/views/healthcare-fraud

### Embedding Options
1. **Tableau Server Embed**: For internal applications
2. **Tableau Public Embed**: For external sharing (sanitized)
3. **API Integration**: For custom dashboards

## Mobile View

### Responsive Layouts
- Portrait: Single column, stacked charts
- Landscape: Optimized two-column layout
- Tablet: Touch-enabled filters

## Alerts & Subscriptions

### Scheduled Subscriptions
- **Daily**: Executive summary (7 AM)
- **Weekly**: Risk analysis report (Monday 9 AM)
- **Monthly**: Provider performance report (1st of month)

### Data-Driven Alerts
- Fraud rate > 5%: Immediate alert
- New critical risk claims: Hourly digest
- High provider risk score: Immediate notification

## Customization Guide

### Adding New Visualizations
1. Connect to data source
2. Create calculated field if needed
3. Build visualization
4. Add filters and actions
5. Test and validate

### Updating Branding
- Edit company logo in image placeholder
- Update color palette (company colors)
- Customize font settings
- Add/remove footer elements

## Performance Tips

1. **Use data extracts** for large datasets (>1M rows)
2. **Limit date ranges** in filters
3. **Use context filters** for dimension-heavy views
4. **Optimize calculations** (use FIXED instead of LOD where possible)
5. **Hide unused sheets** to improve load time

## Support & Maintenance

### Regular Maintenance
- Update data source connections
- Refresh extracts
- Monitor dashboard performance
- Review user feedback

### Contact
- Tableau Admin: tableau-admin@company.com
- Data Team: healthcare-analytics@company.com
- Documentation: Internal Confluence

## Appendix: Sample Calculations

### Fraud Detection Rate Trend
```
// Moving average of fraud rate
WINDOW_AVG(
  [SUM([is_fraud])] / [COUNT([claim_id])],
  -7, 0  // 7-day moving average
)
```

### Provider Performance Score
```
// Composite score for provider ranking
(
  [Fraud Rate Weight] * (1 - [Provider Fraud Rate]) +
  [Volume Weight] * [Normalized Claim Volume] +
  [Efficiency Weight] * [Audit Efficiency Score]
) * 100
```

### Claim Anomaly Index
```
// Overall anomaly score for a claim
(
  [Amount Z-Score] * 0.3 +
  [Service Count Z-Score] * 0.2 +
  [Frequency Ratio] * 0.2 +
  [Code Density Score] * 0.3
)
```
