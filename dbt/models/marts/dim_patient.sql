-- Gold: patient dimension
-- No names on purpose: analytics does not need them (GDPR data minimisation)

with patients as (

    select * from {{ ref('stg_patients') }}

)

select
    patient_mrn,
    sex,
    birth_date,
    date_part('year', age(current_date, birth_date))::int as age,
    case
        when birth_date is null then 'Unknown'
        when date_part('year', age(current_date, birth_date)) < 40 then '18-39'
        when date_part('year', age(current_date, birth_date)) < 65 then '40-64'
        else '65+'
    end as age_group
from patients