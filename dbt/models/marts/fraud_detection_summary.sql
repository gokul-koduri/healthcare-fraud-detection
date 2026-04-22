-- Summary table for fraud detection metrics
{{ config(
    materialized='table',
    tags=['marts']
) }}

WITH claims AS (
    SELECT * FROM {{ ref('fact_claims_enriched') }}
),

daily_metrics AS (
    SELECT
        DATE_TRUNC('day', service_date) as report_date,
        
        -- Volume metrics
        COUNT(*) as total_claims,
        SUM(claim_amount) as total_amount,
        AVG(claim_amount) as avg_claim_amount,
        
        -- Risk distribution
        SUM(CASE WHEN amount_z_score > 3 THEN 1 ELSE 0 END) as statistical_outliers,
        SUM(CASE WHEN high_amount_flag = 1 THEN 1 ELSE 0 END) as high_value_claims,
        SUM(CASE WHEN high_service_flag = 1 THEN 1 ELSE 0 END) as high_service_claims,
        
        -- Provider metrics
        COUNT(DISTINCT provider_id) as active_providers,
        COUNT(DISTINCT patient_id) as unique_patients
        
    FROM claims
    WHERE service_date >= DATEADD(day, -30, CURRENT_DATE())
    GROUP BY DATE_TRUNC('day', service_date)
)

SELECT
    *,
    (statistical_outliers::FLOAT / NULLIF(total_claims, 0)) as outlier_rate
FROM daily_metrics
ORDER BY report_date DESC
