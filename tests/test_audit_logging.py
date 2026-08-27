"""
Pruebas Unitarias para el Sistema de Auditoría y Trazabilidad de Decisiones de Calidad.
"""

import sys
from pathlib import Path

# Agregar raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from ingestion.models import CDMRecord, AuditEntry
from ingestion.sinks import AuditStorageSink
from pipeline.validation import SchemaValidator
from pipeline.cleaning import DataCleaner
from pipeline.normalization import UnitNormalizer, PlausibilityChecker
from pipeline.leakage_guard import LeakageGuard


def test_audit_logging_full_pipeline(tmp_path):
    """Verifica que cada decisión de calidad registre el porqué y sus valores asociados."""
    audit_log = []

    # 1. Registro incompleto
    validator = SchemaValidator()
    rec_invalid = CDMRecord(record_id="", patient_id="", source_file="test.csv", variable_code="")
    validator.validate([rec_invalid], audit_log=audit_log)
    assert len(audit_log) == 1
    assert audit_log[0].stage == "SCHEMA_VALIDATION"
    assert audit_log[0].action == "FLAGGED"
    assert "Esquema incompleto" in audit_log[0].reason

    # 2. Registro duplicado y Missing
    cleaner = DataCleaner()
    rec1 = CDMRecord(record_id="REC_01", patient_id="PAT-0001", source_file="test.csv", variable_code="HR", value_numeric=72.0, event_datetime="2026-07-10 09:00:00")
    rec_dup = CDMRecord(record_id="REC_01", patient_id="PAT-0001", source_file="test.csv", variable_code="HR", value_numeric=72.0, event_datetime="2026-07-10 09:00:00")
    rec_missing = CDMRecord(record_id="REC_02", patient_id="PAT-0001", source_file="test.csv", variable_code="HR", value_numeric=None, value_text=None, event_datetime="2026-07-10 09:00:00")

    cleaner.clean([rec1, rec_dup, rec_missing], audit_log=audit_log)
    # Debe haber registrado duplicado descartado y missing preservado
    actions = [e.action for e in audit_log]
    assert "DISCARDED" in actions
    assert "PRESERVED_MISSING" in actions

    # 3. Conversión de unidades
    normalizer = UnitNormalizer()
    rec_temp = CDMRecord(record_id="REC_03", patient_id="PAT-0001", source_file="test.csv", variable_code="TEMP", value_numeric=98.6, original_unit="degF", event_datetime="2026-07-10 09:00:00")
    normalizer.normalize([rec_temp], audit_log=audit_log)
    assert any(e.action == "CONVERTED" and e.stage == "UNIT_NORMALIZATION" for e in audit_log)

    # 4. Outlier biológico
    checker = PlausibilityChecker()
    rec_out = CDMRecord(record_id="REC_04", patient_id="PAT-0001", source_file="test.csv", variable_code="HR", value_numeric=350.0, event_datetime="2026-07-10 09:00:00")
    checker.check([rec_out], audit_log=audit_log)
    assert any(e.stage == "PLAUSIBILITY_CHECK" and "fuera de rango" in e.reason for e in audit_log)

    # 5. Persistencia del log de auditoría
    audit_sink = AuditStorageSink(base_dir=str(tmp_path / "audit"))
    csv_path = audit_sink.save_audit_entries(audit_log, log_name="test_audit_log")
    assert Path(csv_path).exists()
    assert Path(str(tmp_path / "audit" / "test_audit_log.jsonl")).exists()


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        test_audit_logging_full_pipeline(Path(tmp))
    print("[OK] Todos los tests de auditoria y trazabilidad pasaron correctamente.")
