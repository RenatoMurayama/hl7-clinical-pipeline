-- Gold: lab results fact table (one row per result), ready for analysis

with results as (

    select * from {{ ref('stg_lab_results') }}

),

patients as (

    select * from {{ ref('dim_patient') }}

)

select
    r.message_id || '-' || r.loinc_code as lab_result_id,
    r.patient_mrn,
    p.sex,
    p.age_group,
    r.order_id,
    r.loinc_code,
    r.test_name,
    r.collected_at,
    r.collected_at::date as collected_date,
    r.result_value,
    r.units,
    r.reference_low,
    r.reference_high,
    r.abnormal_flag,
    case
        when r.result_value is null then 'Missing'
        when r.result_value < r.reference_low then 'Low'
        when r.result_value > r.reference_high then 'High'
        else 'Normal'
    end as result_category
from results as r
left join patients as p
    on r.patient_mrn = p.patient_mrn