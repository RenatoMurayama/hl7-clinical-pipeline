-- Staging: clean, typed and de-duplicated lab results (1 row per result)

with source as (

    select * from {{ source('raw', 'oru_lab_results') }}

),

deduplicated as (

    -- the hospital may re-send the same message: keep only the first copy
    select
        *,
        row_number() over (
            partition by message_id, obx_set_id
            order by source_file
        ) as row_num
    from source

)

select
    message_id,
    patient_mrn,
    order_id,
    loinc_code,
    test_name,
    to_timestamp(collected_datetime, 'YYYYMMDDHH24MISS') as collected_at,
    -- NULL when the value is missing or not a valid number
    case
        when result_value ~ '^-?[0-9]+(\.[0-9]+)?$' then result_value::numeric
    end as result_value,
    units,
    split_part(reference_range, '-', 1)::numeric as reference_low,
    split_part(reference_range, '-', 2)::numeric as reference_high,
    abnormal_flag,
    result_status,
    source_file
from deduplicated
where row_num = 1