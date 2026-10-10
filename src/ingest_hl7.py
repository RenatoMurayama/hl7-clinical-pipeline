"""
HL7 v2 ingestion: Extract & Load into the raw (Bronze) layer.

Reads every .hl7 file in data/raw, extracts the relevant fields
and loads them, unchanged, into PostgreSQL raw.* tables.
Full refresh: raw tables are emptied and reloaded on every run.
"""

import logging
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DDL_FILE = PROJECT_ROOT / "sql" / "01_create_raw_tables.sql"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("ingest")


# --- Lightweight HL7 v2 parser -----------------------------------------------
def parse_message(text):
    """Split an HL7 message into {segment_name: [segments]}.

    Each segment is a list of fields indexed like the HL7 spec
    (field 1 at index 1), so PID-3 is pid[3].
    """
    segments = {}
    for line in text.split("\r"):
        if not line.strip():
            continue
        fields = line.split("|")
        if fields[0] == "MSH":
            fields.insert(1, "|")  # MSH-1 is the separator itself
        segments.setdefault(fields[0], []).append(fields)
    return segments


def get(segment, field, component=None):
    """Return a field (or one ^component of it), or None if empty/missing."""
    if segment is None or field >= len(segment):
        return None
    value = segment[field]
    if component is not None:
        parts = value.split("^")
        value = parts[component - 1] if component <= len(parts) else ""
    return value or None


# --- One function per message type ------------------------------------------
def common_fields(source_file, seg):
    msh, pid = seg["MSH"][0], seg["PID"][0]
    return {
        "source_file": source_file,
        "message_id": get(msh, 10),
        "message_datetime": get(msh, 7),
        "patient_mrn": get(pid, 3, 1),
        "family_name": get(pid, 5, 1),
        "given_name": get(pid, 5, 2),
        "birth_date": get(pid, 7),
        "sex": get(pid, 8),
    }


def parse_adt(source_file, seg):
    pv1 = seg["PV1"][0]
    return {
        **common_fields(source_file, seg),
        "ward_location": get(pv1, 3),
        "hospital_service": get(pv1, 10),
        "visit_number": get(pv1, 19),
        "admit_datetime": get(pv1, 44),
    }


def parse_siu(source_file, seg):
    sch, ail = seg["SCH"][0], seg["AIL"][0]
    return {
        **common_fields(source_file, seg),
        "appointment_id": get(sch, 1),
        "appointment_reason": get(sch, 7, 2),
        "duration_minutes": get(sch, 11, 3),
        "appointment_start": get(sch, 11, 4),
        "appointment_status": get(sch, 25),
        "department": get(ail, 3),
    }


def parse_oru(source_file, seg):
    """One row per OBX (one row per lab result)."""
    obr = seg["OBR"][0]
    base = {
        **common_fields(source_file, seg),
        "order_id": get(obr, 3),
        "collected_datetime": get(obr, 7),
    }
    return [
        {
            **base,
            "obx_set_id": get(obx, 1),
            "loinc_code": get(obx, 3, 1),
            "test_name": get(obx, 3, 2),
            "result_value": get(obx, 5),
            "units": get(obx, 6),
            "reference_range": get(obx, 7),
            "abnormal_flag": get(obx, 8),
            "result_status": get(obx, 11),
        }
        for obx in seg.get("OBX", [])
    ]


# --- Load ---------------------------------------------------------------------
def insert_rows(cur, table, rows):
    if not rows:
        return
    columns = list(rows[0].keys())
    sql = f"INSERT INTO raw.{table} ({', '.join(columns)}) VALUES %s"
    execute_values(cur, sql, [tuple(row[c] for c in columns) for row in rows])


def main():
    load_dotenv(PROJECT_ROOT / ".env")
    files = sorted(RAW_DIR.glob("*.hl7"))
    log.info("Found %d HL7 files in %s", len(files), RAW_DIR)

    rows = {"adt_admissions": [], "siu_appointments": [], "oru_lab_results": []}
    failed = 0

    for path in files:
        with path.open(encoding="utf-8", newline="") as f:  # keep \r intact
            text = f.read()
        try:
            seg = parse_message(text)
            msg_type = get(seg["MSH"][0], 9)
            if msg_type == "ADT^A01":
                rows["adt_admissions"].append(parse_adt(path.name, seg))
            elif msg_type == "SIU^S12":
                rows["siu_appointments"].append(parse_siu(path.name, seg))
            elif msg_type == "ORU^R01":
                rows["oru_lab_results"].extend(parse_oru(path.name, seg))
            else:
                log.warning("Unsupported message type %s in %s", msg_type, path.name)
        except (KeyError, IndexError) as exc:
            failed += 1
            log.warning("Could not parse %s: %s", path.name, exc)

    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )
    with conn:  # one transaction: commit if all OK, rollback if anything fails
        with conn.cursor() as cur:
            cur.execute(DDL_FILE.read_text(encoding="utf-8"))
            cur.execute("TRUNCATE raw.adt_admissions, raw.siu_appointments, raw.oru_lab_results")
            for table, table_rows in rows.items():
                insert_rows(cur, table, table_rows)
                log.info("Loaded %d rows into raw.%s", len(table_rows), table)
    conn.close()
    log.info("Ingestion finished. Files that failed to parse: %d", failed)


if __name__ == "__main__":
    main()