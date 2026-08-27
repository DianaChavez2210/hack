"""
Pruebas Unitarias para la Integridad de Evidencias y Señales (evidence/).
HealthSignal LATAM — RISA Data V1.0.
"""

import pytest
import csv
from pathlib import Path
from evidence.evidence_builder import EvidenceBuilder
from evidence.explanation_builder import ExplanationBuilder
from evidence.validator import SubmissionValidator
from ingestion.models import CDMRecord


def test_evidence_builder_and_validation(tmp_path):
    sig_csv = tmp_path / "signals.csv"
    ev_csv = tmp_path / "evidence.csv"

    builder = EvidenceBuilder(output_path=str(ev_csv))
    exp_builder = ExplanationBuilder()

    rec_primary = CDMRecord(
        record_id="OBS-101",
        patient_id="PAT-99",
        source_file="vital_signs.csv",
        variable_code="HR",
        value_numeric=135.0,
        converted_value=135.0,
        event_datetime="2026-07-10 11:00:00",
        available_datetime="2026-07-10 11:05:00"
    )

    t_dec = "2026-07-10 12:00:00"
    entries = builder.build_evidence(
        signal_id="SIG-000001",
        patient_id="PAT-99",
        decision_datetime=t_dec,
        records=[rec_primary],
        vitals_ranges={"HR": (60.0, 100.0)}
    )

    assert len(entries) > 0
    roles = [e["evidence_role"] for e in entries]
    assert "PRIMARY" in roles

    builder.save_evidence(entries, append=False)

    explanation = exp_builder.generate_explanation(
        patient_id="PAT-99",
        priority_level="HIGH",
        decision_datetime=t_dec,
        evidence_entries=entries,
        cdm_records=[rec_primary]
    )

    with open(sig_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "signal_id", "patient_id", "decision_datetime", "risk_score",
            "priority_level", "evidence_start", "evidence_end",
            "explanation", "model_version"
        ])
        writer.writeheader()
        writer.writerow({
            "signal_id": "SIG-000001",
            "patient_id": "PAT-99",
            "decision_datetime": t_dec,
            "risk_score": 0.75,
            "priority_level": "HIGH",
            "evidence_start": "2026-07-09 12:00:00",
            "evidence_end": t_dec,
            "explanation": explanation,
            "model_version": "v1.0.0"
        })

    validator = SubmissionValidator()
    is_valid, errors = validator.validate_files(str(sig_csv), str(ev_csv))
    assert is_valid, f"Errores de validación: {errors}"


if __name__ == "__main__":
    pytest.main([__file__])
