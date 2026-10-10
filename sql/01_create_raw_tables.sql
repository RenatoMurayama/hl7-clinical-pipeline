-- Raw layer (Bronze): data lands exactly as received from the hospital.
-- All columns are TEXT on purpose: typing and cleaning happen later in dbt.

CREATE SCHEMA IF NOT EXISTS raw;

-- ADT^A01: inpatient admissions
CREATE TABLE IF NOT EXISTS raw.adt_admissions (
    source_file       TEXT,
    message_id        TEXT,
    message_datetime  TEXT,
    patient_mrn       TEXT,
    family_name       TEXT,
    given_name        TEXT,
    birth_date        TEXT,
    sex               TEXT,
    ward_location     TEXT,
    hospital_service  TEXT,
    visit_number      TEXT,
    admit_datetime    TEXT,
    loaded_at         TIMESTAMPTZ DEFAULT now()
);

-- SIU^S12: outpatient appointments
CREATE TABLE IF NOT EXISTS raw.siu_appointments (
    source_file        TEXT,
    message_id         TEXT,
    message_datetime   TEXT,
    patient_mrn        TEXT,
    family_name        TEXT,
    given_name         TEXT,
    birth_date         TEXT,
    sex                TEXT,
    appointment_id     TEXT,
    appointment_reason TEXT,
    duration_minutes   TEXT,
    appointment_start  TEXT,
    appointment_status TEXT,
    department         TEXT,
    loaded_at          TIMESTAMPTZ DEFAULT now()
);

-- ORU^R01: lab results (one row per OBX segment)
CREATE TABLE IF NOT EXISTS raw.oru_lab_results (
    source_file        TEXT,
    message_id         TEXT,
    message_datetime   TEXT,
    patient_mrn        TEXT,
    family_name        TEXT,
    given_name         TEXT,
    birth_date         TEXT,
    sex                TEXT,
    order_id           TEXT,
    collected_datetime TEXT,
    obx_set_id         TEXT,
    loinc_code         TEXT,
    test_name          TEXT,
    result_value       TEXT,
    units              TEXT,
    reference_range    TEXT,
    abnormal_flag      TEXT,
    result_status      TEXT,
    loaded_at          TIMESTAMPTZ DEFAULT now()
);
