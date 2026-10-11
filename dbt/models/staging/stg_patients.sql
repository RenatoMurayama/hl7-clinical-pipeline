-- Staging: one row per patient, built from the PID segment of every message type

with all_pid as (

    select patient_mrn, family_name, given_name, birth_date, sex
    from {{ source('raw', 'adt_admissions') }}

    union all

    select patient_mrn, family_name, given_name, birth_date, sex
    from {{ source('raw', 'siu_appointments') }}

    union all

    select patient_mrn, family_name, given_name, birth_date, sex
    from {{ source('raw', 'oru_lab_results') }}

)

-- max() ignores NULLs: a birth date missing in one message
-- is recovered from the other messages of the same patient
select
    patient_mrn,
    max(family_name)                     as family_name,
    max(given_name)                      as given_name,
    to_date(max(birth_date), 'YYYYMMDD') as birth_date,
    max(sex)                             as sex
from all_pid
group by patient_mrn