-- Staging model for raw claims data
{{ config(
    materialized='view',
    tags=['staging']
) }}

SELECT
    claim_id,
    patient_id,
    provider_id,
    service_date,
    claim_amount,
    service_count,
    patient_age,
    provider_claim_frequency,
    diagnosis_code_count,
    procedure_code_count,
    provider_type,
    specialty,
    place_of_service,
    diagnosis_codes,
    procedure_codes,
    created_at,
    updated_at
FROM {{ source('raw', 'claims') }}

-- Filter out invalid records
WHERE claim_amount >= 0
  AND service_date IS NOT NULL
  AND claim_id IS NOT NULL
