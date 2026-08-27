"""
Pruebas Unitarias para Procesamiento Temporal y Prevención de Fuga Temporal (Leakage Guard).
"""

import sys
from pathlib import Path

# Agregar raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from ingestion.models import CDMRecord
from pipeline.temporal import TemporalProcessor
from pipeline.leakage_guard import LeakageGuard


def test_temporal_latency_calculation():
    """Verifica el cálculo de latencia en segundos entre T_event y T_available."""
    processor = TemporalProcessor()
    rec = CDMRecord(
        record_id="REC_LAB_01",
        patient_id="PAT-0001",
        source_file="labs.csv",
        variable_code="LAB_A",
        value_numeric=4.5,
        event_datetime="2026-07-16 08:00:00",    # Toma de muestra
        available_datetime="2026-07-16 10:00:00" # Resultado disponible (2 horas = 7200 s)
    )

    processed = processor.process([rec])
    assert processed[0].latency_seconds == 7200.0


def test_leakage_guard_filtering():
    """Verifica que registros futuros respecto a decision_datetime sean bloqueados."""
    guard = LeakageGuard()
    
    # Registro disponible a las 09:00 (Seguro para decisión a las 09:30)
    rec_past = CDMRecord(
        record_id="REC_PAST",
        patient_id="PAT-0001",
        source_file="vitals.csv",
        variable_code="HR",
        value_numeric=72.0,
        event_datetime="2026-07-10 08:50:00",
        available_datetime="2026-07-10 09:00:00"
    )

    # Registro con muestra tomada a las 09:15 pero disponible a las 11:00 (Fuga temporal para decisión a las 09:30)
    rec_future = CDMRecord(
        record_id="REC_FUTURE",
        patient_id="PAT-0001",
        source_file="labs.csv",
        variable_code="LAB_B",
        value_numeric=95.0,
        event_datetime="2026-07-10 09:15:00",
        available_datetime="2026-07-10 11:00:00"
    )

    decision_time = "2026-07-10 09:30:00"
    
    # Check individual
    assert guard.check_leakage(rec_past, decision_time) is True
    assert guard.check_leakage(rec_future, decision_time) is False

    # Check batch filter
    filtered = guard.filter_by_decision_time([rec_past, rec_future], decision_time)
    assert len(filtered) == 1
    assert filtered[0].record_id == "REC_PAST"


if __name__ == "__main__":
    test_temporal_latency_calculation()
    test_leakage_guard_filtering()
    print("[OK] Todos los tests temporales y de leakage guard pasaron correctamente.")
