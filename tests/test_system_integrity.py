"""
Pruebas Unitarias para las 13 Reglas de Validación de Integridad de Datos.
"""

import pytest
from ingestion.models import CDMRecord, AuditEntry
from pipeline.integrity import SystemIntegrityValidator
from pipeline.normalization import UnitNormalizer, PlausibilityChecker
from pipeline.temporal import TemporalProcessor
from pipeline.contextualizer import Contextualizer


def test_ir_01_invalid_or_inactive_patient():
    patients_dict = {
        "PAT-0001": {"patient_id": "PAT-0001", "active": True},
        "PAT-0002": {"patient_id": "PAT-0002", "active": False}
    }
    validator = SystemIntegrityValidator(patients_dict=patients_dict)
    audit_log = []

    rec_unknown = CDMRecord(record_id="R1", source_file="vital_signs.csv", patient_id="PAT-9999", plausibility_status="VALID")
    rec_inactive = CDMRecord(record_id="R2", source_file="vital_signs.csv", patient_id="PAT-0002", plausibility_status="VALID")
    rec_valid = CDMRecord(record_id="R3", source_file="vital_signs.csv", patient_id="PAT-0001", plausibility_status="VALID")

    res = validator.validate([rec_unknown, rec_inactive, rec_valid], audit_log=audit_log)

    assert res[0].plausibility_status == "INVALID_PATIENT_ID"
    assert res[1].plausibility_status == "INACTIVE_PATIENT"
    assert res[2].plausibility_status == "VALID"
    assert len(audit_log) == 2


def test_ir_02_encounter_patient_mismatch():
    encounters_dict = {
        "ENC-0001": {"encounter_id": "ENC-0001", "patient_id": "PAT-0001"}
    }
    validator = SystemIntegrityValidator(encounters_dict=encounters_dict)
    audit_log = []

    rec_mismatch = CDMRecord(record_id="R1", source_file="vital_signs.csv", patient_id="PAT-0002", encounter_id="ENC-0001", plausibility_status="VALID")
    rec_valid = CDMRecord(record_id="R2", source_file="vital_signs.csv", patient_id="PAT-0001", encounter_id="ENC-0001", plausibility_status="VALID")

    res = validator.validate([rec_mismatch, rec_valid], audit_log=audit_log)

    assert res[0].plausibility_status == "ENCOUNTER_PATIENT_MISMATCH"
    assert res[1].plausibility_status == "VALID"


def test_ir_03_device_integrity():
    devices_dict = {
        "DEV-0001": {"device_id": "DEV-0001", "active": False, "assigned_patient_id": "PAT-0001"},
        "DEV-0002": {"device_id": "DEV-0002", "active": True, "assigned_patient_id": "PAT-0001"}
    }
    validator = SystemIntegrityValidator(devices_dict=devices_dict)
    audit_log = []

    rec_inactive = CDMRecord(record_id="R1", source_file="vital_signs.csv", patient_id="PAT-0001", device_id="DEV-0001", plausibility_status="VALID")
    rec_mismatch = CDMRecord(record_id="R2", source_file="vital_signs.csv", patient_id="PAT-0002", device_id="DEV-0002", plausibility_status="VALID")

    res = validator.validate([rec_inactive, rec_mismatch], audit_log=audit_log)

    assert res[0].plausibility_status == "INACTIVE_DEVICE"
    assert res[1].plausibility_status == "DEVICE_PATIENT_MISMATCH"


def test_tp_01_out_of_encounter_bounds():
    encounters_dict = {
        "ENC-0001": {"encounter_id": "ENC-0001", "start_datetime": "2026-07-10 00:00:00", "end_datetime": "2026-07-10 23:59:59"}
    }
    tp = TemporalProcessor(encounters_dict=encounters_dict)
    audit_log = []

    rec_outside = CDMRecord(record_id="R1", source_file="vital_signs.csv", patient_id="PAT-0001", encounter_id="ENC-0001", event_datetime="2026-07-11 12:00:00", plausibility_status="VALID")
    rec_inside = CDMRecord(record_id="R2", source_file="vital_signs.csv", patient_id="PAT-0001", encounter_id="ENC-0001", event_datetime="2026-07-10 12:00:00", plausibility_status="VALID")

    res = tp.process([rec_outside, rec_inside], audit_log=audit_log)

    assert res[0].plausibility_status == "OUT_OF_ENCOUNTER_BOUNDS"
    assert res[1].plausibility_status == "VALID"


def test_tp_02_temporal_leakage():
    tp = TemporalProcessor()
    audit_log = []

    rec_leakage = CDMRecord(record_id="R1", source_file="lab_results.csv", patient_id="PAT-0001", event_datetime="2026-07-10 12:00:00", available_datetime="2026-07-10 10:00:00", plausibility_status="VALID")
    rec_valid = CDMRecord(record_id="R2", source_file="lab_results.csv", patient_id="PAT-0001", event_datetime="2026-07-10 10:00:00", available_datetime="2026-07-10 12:00:00", plausibility_status="VALID")

    res = tp.process([rec_leakage, rec_valid], audit_log=audit_log)

    assert res[0].plausibility_status == "TEMPORAL_LEAKAGE"
    assert res[1].plausibility_status == "VALID"


def test_pl_02_medication_dose():
    checker = PlausibilityChecker()
    audit_log = []

    rec_invalid_dose = CDMRecord(record_id="ADM-01", source_file="medication_administrations.csv", patient_id="PAT-0001", header_fields={"dose_value": "0.0"}, plausibility_status="VALID")
    rec_valid_dose = CDMRecord(record_id="ADM-02", source_file="medication_administrations.csv", patient_id="PAT-0001", header_fields={"dose_value": "10.5"}, plausibility_status="VALID")

    res = checker.check([rec_invalid_dose, rec_valid_dose], audit_log=audit_log)

    assert res[0].plausibility_status == "INVALID_MEDICATION_DOSE"
    assert res[1].plausibility_status == "VALID"


def test_cx_03_suspicious_sleep_activity():
    patient_contexts = [
        {"patient_id": "PAT-0001", "start_datetime": "2026-07-10 00:00:00", "end_datetime": "2026-07-10 08:00:00", "context_value": "SLEEP"}
    ]
    ctx = Contextualizer(patient_contexts=patient_contexts)
    audit_log = []

    rec_high_hr = CDMRecord(record_id="R1", source_file="wearables.csv", patient_id="PAT-0001", variable_code="WEARABLE_HR", value_numeric=120.0, event_datetime="2026-07-10 03:00:00", plausibility_status="VALID")
    rec_normal_hr = CDMRecord(record_id="R2", source_file="wearables.csv", patient_id="PAT-0001", variable_code="WEARABLE_HR", value_numeric=65.0, event_datetime="2026-07-10 04:00:00", plausibility_status="VALID")

    res = ctx.contextualize([rec_high_hr, rec_normal_hr], audit_log=audit_log)

    assert res[0].plausibility_status == "SUSPICIOUS_SLEEP_ACTIVITY"
    assert res[1].plausibility_status == "VALID"


if __name__ == "__main__":
    pytest.main([__file__])
