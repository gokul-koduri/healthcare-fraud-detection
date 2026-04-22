-- Provider dimension table with risk metrics
{{ config(
    materialized='table',
    tags=['marts']
) }}

WITH provider_claims AS (
    SELECT * FROM {{ ref('stg_claims') }}
),

provider_metrics AS (
    SELECT
        provider_id,
        provider_type,
        specialty,
        
        -- Basic metrics
        COUNT(*) as total_claims,
        SUM(claim_amount) as total_claim_amount,
        AVG(claim_amount) as avg_claim_amount,
        STDDEV(claim_amount) as stddev_claim_amount,
        
        -- Service metrics
        AVG(service_count) as avg_service_count,
        AVG(diagnosis_code_count) as avg_diagnosis_count,
        AVG(procedure_code_count) as avg_procedure_count,
        
        -- Patient metrics
        COUNT(DISTINCT patient_id) as unique_patients,
        
        -- Date range
        MIN(service_date) as first_claim_date,
        MAX(service_date) as last_claim_date,
        
        -- Risk indicators
        SUM(CASE WHEN claim_amount > 5000 THEN 1 ELSE 0 END) as high_value_claims,
        SUM(CASE WHEN service_count > 10 THEN 1 ELSE 0 END) as high_service_claims
        
    FROM provider_claims
    GROUP BY provider_id, provider_type, specialty
),

provider_risk_score AS (
    SELECT
        *,
        -- Calculate risk score based on multiple factors
        (
            -- High claim volume weight
            CASE 
                WHEN total_claims > 1000 THEN 30
                WHEN total_claims > 500 THEN 20
                WHEN total_claims > 100 THEN 10
                ELSE 0
            END +
            -- High amount ratio
            (high_value_claims::FLOAT / NULLIF(total_claims, 0) * 100 * 0.3) +
            -- High service ratio
            (high_service_claims::FLOAT / NULLIF(total_claims, 0) * 100 * 0.2) +
            -- Patient-to-claim ratio (low ratio = potential clustering)
            CASE
                WHEN unique_patients::FLOAT / NULLIF(total_claims, 0) < 0.5 THEN 20
                WHEN unique_patients::FLOAT / NULLIF(total_claims, 0) < 0.7 THEN 10
                ELSE 0
            END
        ) as provider_risk_score
        
    FROM provider_metrics
)

SELECT
    *,
    CASE
        WHEN provider_risk_score >= 70 THEN 'Critical'
        WHEN provider_risk_score >= 50 THEN 'High'
        WHEN provider_risk_score >= 30 THEN 'Medium'
        ELSE 'Low'
    END as risk_category
FROM provider_risk_score
