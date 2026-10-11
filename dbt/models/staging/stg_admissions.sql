-- Staging: clean, typed and de-duplicated inpatient admissions

with source as (

    select * from {{ source('raw', 'adt_admissions') }}

),

deduplicated as (

    select
        *,
        row_number() over (partition by message_id order by source_file) as row_num
    from source

)

select
    message_id,
    visit_number,
    patient_mrn,
    hospital_service,
    split_part(ward_location, '^', 1) as ward,
    split_part(ward_location, '^', 2) as room,
    split_part(ward_location, '^', 3) as bed,
    to_timestamp(admit_datetime, 'YYYYMMDDHH24MISS') as admitted_at,
    source_file
from deduplicated
where row_num = 1