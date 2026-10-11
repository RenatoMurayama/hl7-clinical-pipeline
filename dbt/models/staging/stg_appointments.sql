-- Staging: clean, typed and de-duplicated outpatient appointments

with source as (

    select * from {{ source('raw', 'siu_appointments') }}

),

deduplicated as (

    select
        *,
        row_number() over (partition by message_id order by source_file) as row_num
    from source

)

select
    message_id,
    appointment_id,
    patient_mrn,
    department,
    appointment_reason,
    appointment_status,
    to_timestamp(appointment_start, 'YYYYMMDDHH24MISS') as appointment_start_at,
    duration_minutes::integer as duration_minutes,
    source_file
from deduplicated
where row_num = 1