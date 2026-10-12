"""Unit tests for the HL7 generator and parser (no database needed)."""

from generate_hl7 import segment
from ingest_hl7 import get, parse_message, parse_oru

# A small, hand-written HL7 message: one normal result and one missing result
SAMPLE_ORU = (
    "MSH|^~\\&|LIS|HOSP_BRAGA|CLINICAL_DW|DATA_PLATFORM|20261006093000||ORU^R01|MSG000001|P|2.5\r"
    "PID|1||123456^^^HOSP_BRAGA^MR||Conceição^João||19580312|M\r"
    "OBR|1||LAB789|ROUTINE^Routine bloods^L|||20261006080000\r"
    "OBX|1|NM|2345-7^Glucose^LN||126|mg/dL|70-99|H|||F\r"
    "OBX|2|NM|2160-0^Creatinine^LN|||mg/dL|0.7-1.3||||F\r"
)


def test_segment_builder_places_fields_by_position():
    assert segment("PID", {1: "1", 3: "123"}) == "PID|1||123"
    assert segment("MSH", {2: "^~\\&", 3: "LIS"}) == "MSH|^~\\&|LIS"


def test_msh_fields_follow_hl7_numbering():
    msh = parse_message(SAMPLE_ORU)["MSH"][0]
    assert get(msh, 9) == "ORU^R01"
    assert get(msh, 10) == "MSG000001"


def test_components_are_split_on_caret():
    pid = parse_message(SAMPLE_ORU)["PID"][0]
    assert get(pid, 3, 1) == "123456"
    assert get(pid, 5, 1) == "Conceição"
    assert get(pid, 5, 2) == "João"


def test_missing_field_returns_none():
    pid = parse_message(SAMPLE_ORU)["PID"][0]
    assert get(pid, 30) is None


def test_oru_creates_one_row_per_obx():
    rows = parse_oru("sample.hl7", parse_message(SAMPLE_ORU))
    assert len(rows) == 2
    assert rows[0]["loinc_code"] == "2345-7"
    assert rows[0]["result_value"] == "126"
    assert rows[0]["abnormal_flag"] == "H"


def test_missing_result_value_becomes_none():
    rows = parse_oru("sample.hl7", parse_message(SAMPLE_ORU))
    assert rows[1]["result_value"] is None