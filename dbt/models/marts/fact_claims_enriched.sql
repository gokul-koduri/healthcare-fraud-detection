-- Enriched claims fact table with engineered features
{{ config(
    materialized='table',
    tags=['marts']
) }}

WITH claims AS (
    SELECT * FROM {{ ref('stg_claims') }}
),

provider_stats AS (
    SELECT
        provider_id,
        AVG(claim_amount) as avg_claim_amount,
        STDDEV(claim_amount) as stddev_claim_amount,
        COUNT(*) as total_claims,
        AVG(service_count) as avg_service_count
    FROM claims
    GROUP BY provider_id
),

claim_features AS (
    SELECT
        c.*,
        
        -- Amount-based features
        (c.claim_amount / NULLIF(c.service_count, 0)) as amount_per_service,
        
        -- Provider comparison features
        p.avg_claim_amount as provider_avg_amount,
        p.stddev_claim_amount as provider_stddev_amount,
        (c.claim_amount - p.avg_claim_amount) as amount_vs_provider_avg,
        ((c.claim_amount - p.avg_claim_amount) / NULLIF(p.stddev_claim_amount, 0)) as amount_z_score,
        
        -- Frequency features
        (c.provider_claim_frequency / 100.0) as claim_frequency_ratio,
        
        -- Code density features
        (c.diagnosis_code_count::FLOAT / NULLIF(c.service_count, 0)) as diagnosis_per_service,
        (c.procedure_code_count::FLOAT / NULLIF(c.service_count, 0)) as procedure_per_service,
        
        -- Flag features
        CASE WHEN c.claim_amount > 5000 THEN 1 ELSE 0 END as high_amount_flag,
        CASE WHEN c.service_count > 10 THEN 1 ELSE 0 END as high_service_flag,
        CASE WHEN c.diagnosis_code_count > 5 THEN 1 ELSE 0 END as high_diagnosis_flag,
        CASE WHEN c.procedure_code_count > 8 THEN 1 ELSE 0 END as high_procedure_flag,
        
        -- Age-based features
        (c.claim_amount::FLOAT / NULLIF(c.patient_age, 0)) as amount_vs_age
        
    FROM claims c
    LEFT JOIN provider_stats p
        ON c.provider_id = p.provider_id
)

SELECT * FROM claim_features
