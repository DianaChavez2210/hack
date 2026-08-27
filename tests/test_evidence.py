"""
Pruebas Unitarias para el Módulo de Evidencias, Linaje, Explicación y Validación (Fase 3).
"""

import sys
import os
import pytest
import csv
from pathlib import Path
from datetime import datetime

# Agregar la raíz al path de Python
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from ingestion.models import CDMRecord
from evidence.evidence_builder import EvidenceBuilder
from evidence.lineage import LineageTracker
from evidence.explanation_builder import ExplanationBuilder
from evidence.validator import SubmissionValidator


@pytest.fixture
def sample_records():
    """Retorna una lista de registros CDM simulados."""
    return [
        # Registro clínico alterado (SpO2 baja) -> PRIMARY
        CDMRecord(
            record_id="REC-001",
            patient_id="PAT-999",
            source_file="vital_signs.csv",
            variable_code="SpO2",
            value_numeric=88.5,
            original_unit="%",
            canonical_unit="%",
            converted_value=88.5,
            event_datetime="2026-07-10T10:00:00",
            available_datetime="2026-07-10T10:05:00",
            is_observed=True
        ),
        # Registro clínico normal -> SUPPORTING
        CDMRecord(
            record_id="REC-002",
            patient_id="PAT-999",
            source_file="vital_signs.csv",
            variable_code="HR",
            value_numeric=72.0,
            original_unit="bpm",
            canonical_unit="bpm",
            converted_value=72.0,
            event_datetime="2026-07-10T10:01:00",
            available_datetime="2026-07-10T10:06:00",
            is_observed=True
        ),
        # Registro de contexto -> CONTEXT
        CDMRecord(
            record_id="REC-003",
            patient_id="PAT-999",
            source_file="patient_context.csv",
            variable_code="",
            event_datetime="2026-07-10T09:30:00",
            available_datetime="2026-07-10T09:35:00",
            context_info={"patient_state": "SLEEP_STATE"}
        ),
        # Registro con baja calidad o error de red -> QUALITY
        CDMRecord(
            record_id="REC-004",
            patient_id="PAT-999",
            source_file="connectivity_events.csv",
            variable_code="",
            event_datetime="2026-07-10T10:02:00",
            available_datetime="2026-07-10T10:07:00",
            context_info={"network_status": "INTERMITTENT", "packet_loss": 15.5}
        ),
        # Registro futuro (para verificar el Leakage Guard) -> Debe ser filtrado
        CDMRecord(
            record_id="REC-FUTURE",
            patient_id="PAT-999",
            source_file="vital_signs.csv",
            variable_code="HR",
            value_numeric=110.0,
            original_unit="bpm",
            canonical_unit="bpm",
            converted_value=110.0,
            event_datetime="2026-07-10T11:00:00",
            available_datetime="2026-07-10T11:05:00",
            is_observed=True
        )
    ]


def test_evidence_builder(tmp_path, sample_records):
    csv_path = str(tmp_path / "evidence.csv")
    builder = EvidenceBuilder(output_path=csv_path)

    # Decisión a las 10:10 (el registro REC-FUTURE está a las 11:05 -> Filtrado)
    decision_time = "2026-07-10T10:10:00"
    
    entries = builder.build_evidence(
        signal_id="SIG-001",
        patient_id="PAT-999",
        decision_datetime=decision_time,
        records=sample_records
    )

    # Verificar que el registro futuro se filtró y quedan los otros 4
    assert len(entries) == 4
    
    # Comprobar roles asignados
    roles = {entry["record_id"]: entry["evidence_role"] for entry in entries}
    assert roles["REC-001"] == "PRIMARY"       # SpO2 < 95%
    assert roles["REC-002"] == "SUPPORTING"    # HR normal
    assert roles["REC-003"] == "CONTEXT"       # Contexto paciente
    assert roles["REC-004"] == "QUALITY"       # Intermitencia red

    # Guardar y validar escritura de cabecera y filas
    builder.save_evidence(entries, append=False)
    assert Path(csv_path).exists()

    with open(csv_path, "r", encoding="utf-8") as f:
        lines = list(csv.reader(f))
        assert len(lines) == 5  # Cabecera + 4 registros
        assert lines[0] == ["signal_id", "source_file", "record_id", "variable_code", "event_datetime", "available_datetime", "evidence_role", "contribution"]


def test_lineage_tracker(tmp_path):
    audit_csv = str(tmp_path / "lineage_audit.csv")
    tracker = LineageTracker(output_path=audit_csv)

    tracker.register_lineage("SIG-001", "mean_HR_30m", "REC-002", "vital_signs.csv")
    tracker.register_lineage("SIG-001", "hypoxia_detected", "REC-001", "vital_signs.csv")

    contributors = tracker.get_contributing_records("SIG-001")
    assert len(contributors) == 2
    assert ("REC-002", "vital_signs.csv", "mean_HR_30m") in contributors

    tracker.save_lineage(append=False)
    assert Path(audit_csv).exists()


def test_explanation_builder(sample_records):
    builder = ExplanationBuilder()
    
    # Crear evidencia simulada
    evidence_entries = [
        {"record_id": "REC-001", "evidence_role": "PRIMARY"},
        {"record_id": "REC-002", "evidence_role": "SUPPORTING"},
        {"record_id": "REC-003", "evidence_role": "CONTEXT"},
        {"record_id": "REC-004", "evidence_role": "QUALITY"}
    ]

    exp = builder.generate_explanation(
        patient_id="PAT-999",
        priority_level="CRITICAL",
        decision_datetime="2026-07-10T10:10:00",
        evidence_entries=evidence_entries,
        cdm_records=sample_records
    )

    # Verificar que el texto contiene la prioridad, el ID y las variables claves
    assert "Prioridad CRITICAL" in exp
    assert "Saturación de Oxígeno (SpO2) alterado (88.5 %)" in exp
    assert "Frecuencia Cardíaca: 72.0 bpm" in exp
    assert "estado SLEEP_STATE" in exp
    assert "red INTERMITTENT" in exp


def test_submission_validator(tmp_path):
    sig_csv = str(tmp_path / "signals.csv")
    ev_csv = str(tmp_path / "evidence.csv")

    # 1. Crear datos válidos
    with open(sig_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["signal_id", "patient_id", "decision_datetime", "risk_score", "priority_level", "confidence_score", "evidence_start", "evidence_end", "explanation", "model_version"])
        writer.writerow(["SIG-001", "PAT-001", "2026-07-10 12:00:00", "0.85", "HIGH", "0.9", "2026-07-10 11:00:00", "2026-07-10 11:59:00", "Explicacion valida", "v1.0"])

    with open(ev_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["signal_id", "source_file", "record_id", "variable_code", "event_datetime", "available_datetime", "evidence_role", "contribution"])
        # Evidencia disponible ANTES de la decisión (valido)
        writer.writerow(["SIG-001", "vital_signs.csv", "REC-001", "SpO2", "2026-07-10 11:15:00", "2026-07-10 11:20:00", "PRIMARY", "0.7"])

    validator = SubmissionValidator()
    success, errors = validator.validate_files(sig_csv, ev_csv)
    assert success
    assert len(errors) == 0

    # 2. Provocar Fuga Temporal (available_datetime > decision_datetime)
    with open(ev_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["signal_id", "source_file", "record_id", "variable_code", "event_datetime", "available_datetime", "evidence_role", "contribution"])
        # Disponible a las 12:10 (después de la decisión a las 12:00 -> Leakage!)
        writer.writerow(["SIG-001", "vital_signs.csv", "REC-001", "SpO2", "2026-07-10 11:15:00", "2026-07-10 12:10:00", "PRIMARY", "0.7"])

    success, errors = validator.validate_files(sig_csv, ev_csv)
    assert not success
    assert any("Fuga temporal detectada" in err for err in errors)
