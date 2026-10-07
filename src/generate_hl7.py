"""
Synthetic HL7 v2 message generator.

Simulates a hospital (HOSP_BRAGA) sending three message types:
  - ADT^A01 : inpatient admissions
  - SIU^S12 : outpatient appointment bookings
  - ORU^R01 : laboratory results (coded with LOINC)

All data is fake (Faker). No real patient data is used.
A small % of messages contains deliberate data quality issues,
so the pipeline's tests have something real to catch.
"""

import random
from datetime import datetime, time, timedelta
from itertools import count
from pathlib import Path

from faker import Faker

# --- Configuration ----------------------------------------------------------
SEED = 42
N_PATIENTS = 50
DAYS_BACK = 7
ISSUE_RATE = 0.05  # 5% chance of a data quality issue

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw"
FACILITY = "HOSP_BRAGA"

fake = Faker("pt_PT")
Faker.seed(SEED)
random.seed(SEED)

# (LOINC code, name, unit, ref_low, ref_high, mean, std_dev)
LAB_TESTS = [
    ("2345-7", "Glucose", "mg/dL", 70, 99, 100, 25),
    ("2160-0", "Creatinine", "mg/dL", 0.7, 1.3, 1.0, 0.3),
    ("2823-3", "Potassium", "mmol/L", 3.5, 5.1, 4.3, 0.5),
    ("718-7", "Hemoglobin", "g/dL", 12.0, 17.5, 14.0, 1.8),
    ("2093-3", "Cholesterol", "mg/dL", 0, 199, 190, 35),
]

SERVICES = ["Cardiologia", "Ortopedia", "Medicina Interna", "Medicina Física e Reabilitação"]

_msg_ids = count(1)


# --- Helpers ----------------------------------------------------------------
def next_msg_id():
    return f"MSG{next(_msg_ids):06d}"


def hl7_ts(dt):
    """HL7 timestamp format: YYYYMMDDHHMMSS."""
    return dt.strftime("%Y%m%d%H%M%S")


def segment(name, fields):
    """Build one HL7 segment from {field_number: value}.

    Empty positions are filled automatically,
    so we never have to count pipes by hand.
    """
    values = [""] * max(fields)
    for position, value in fields.items():
        values[position - 1] = str(value)
    if name == "MSH":
        # HL7 quirk: in MSH, field 1 IS the "|" separator itself
        values = values[1:]
    return name + "|" + "|".join(values)


def msh(app, msg_type, msg_id, when):
    return segment("MSH", {
        2: "^~\\&", 3: app, 4: FACILITY, 5: "KNOK", 6: "KNOK",
        7: hl7_ts(when), 9: msg_type, 10: msg_id, 11: "P", 12: "2.5",
        18: "UNICODE UTF-8",
    })


def pid(patient, drop_dob=False):
    return segment("PID", {
        1: "1",
        3: f"{patient['mrn']}^^^{FACILITY}^MR",
        5: f"{patient['family']}^{patient['given']}",
        7: "" if drop_dob else patient["dob"],  # issue: missing birth date
        8: patient["sex"],
    })


def new_patient():
    sex = random.choice(["M", "F"])
    return {
        "mrn": str(fake.unique.random_number(digits=7, fix_len=True)),
        "family": fake.last_name(),
        "given": fake.first_name_male() if sex == "M" else fake.first_name_female(),
        "dob": fake.date_of_birth(minimum_age=18, maximum_age=95).strftime("%Y%m%d"),
        "sex": sex,
    }


# --- Message builders -------------------------------------------------------
def adt_a01(patient, when):
    """Inpatient admission."""
    msg_id = next_msg_id()
    return msg_id, [
        msh("PAS", "ADT^A01", msg_id, when),
        segment("EVN", {1: "A01", 2: hl7_ts(when)}),
        pid(patient, drop_dob=random.random() < ISSUE_RATE),
        segment("PV1", {
            1: "1",
            2: "I",  # I = inpatient
            3: f"PISO{random.randint(1, 5)}^{random.randint(1, 30)}^{random.randint(1, 2)}",
            10: random.choice(SERVICES),
            19: f"V{fake.unique.random_number(digits=8, fix_len=True)}",
            44: hl7_ts(when),
        }),
    ]


def siu_s12(patient, when):
    """Outpatient appointment booking."""
    msg_id = next_msg_id()
    day = (when + timedelta(days=random.randint(1, 30))).date()
    start = datetime.combine(day, time(random.randint(8, 17), random.choice([0, 15, 30, 45])))
    return msg_id, [
        msh("SCHED", "SIU^S12", msg_id, when),
        segment("SCH", {
            1: f"APT{fake.unique.random_number(digits=7, fix_len=True)}",
            7: "^Consulta de seguimento",
            11: f"^^30^{hl7_ts(start)}",  # 30-minute slot at start time
            25: "Booked",
        }),
        pid(patient),
        segment("AIL", {1: "1", 3: random.choice(SERVICES)}),
    ]


def oru_r01(patient, when):
    """Laboratory results."""
    msg_id = next_msg_id()
    collected = when - timedelta(hours=random.randint(1, 4))
    segments = [
        msh("LIS", "ORU^R01", msg_id, when),
        pid(patient),
        segment("OBR", {
            1: "1",
            3: f"LAB{fake.unique.random_number(digits=7, fix_len=True)}",
            4: "ROUTINE^Routine bloods^L",
            7: hl7_ts(collected),
        }),
    ]
    tests = random.sample(LAB_TESTS, k=random.randint(2, len(LAB_TESTS)))
    for i, (code, name, unit, low, high, mean, sd) in enumerate(tests, start=1):
        value = round(max(random.gauss(mean, sd), 0.1), 1)
        flag = "H" if value > high else "L" if value < low else "N"
        if random.random() < ISSUE_RATE:
            value, flag = "", ""  # issue: result missing
        segments.append(segment("OBX", {
            1: i, 2: "NM", 3: f"{code}^{name}^LN", 5: value,
            6: unit, 7: f"{low}-{high}", 8: flag, 11: "F",
        }))
    return msg_id, segments


# --- Main -------------------------------------------------------------------
def write_message(msg_id, segments, suffix=""):
    """HL7 v2 separates segments with a carriage return (\\r)."""
    path = OUTPUT_DIR / f"{msg_id}{suffix}.hl7"
    path.write_text("\r".join(segments) + "\r", encoding="utf-8", newline="")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUTPUT_DIR.glob("*.hl7"):
        old.unlink()  # start clean on every run

    now = datetime.now().replace(microsecond=0)
    counts = {"ADT^A01": 0, "SIU^S12": 0, "ORU^R01": 0, "duplicates": 0}

    for _ in range(N_PATIENTS):
        patient = new_patient()
        events = []
        if random.random() < 0.3:
            events.append(("ADT^A01", adt_a01))
        if random.random() < 0.7:
            events.append(("SIU^S12", siu_s12))
        events += [("ORU^R01", oru_r01)] * random.randint(1, 3)

        for msg_type, build in events:
            when = now - timedelta(days=random.randint(0, DAYS_BACK - 1),
                                   minutes=random.randint(0, 1440))
            msg_id, segments = build(patient, when)
            write_message(msg_id, segments)
            counts[msg_type] += 1
            if random.random() < ISSUE_RATE:
                # issue: the sending system re-sends the same message
                write_message(msg_id, segments, suffix="_resent")
                counts["duplicates"] += 1

    print(f"Generated {sum(counts.values())} HL7 files in {OUTPUT_DIR}")
    for name, n in counts.items():
        print(f"  {name}: {n}")


if __name__ == "__main__":
    main()