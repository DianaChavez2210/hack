"""
Pruebas Unitarias para la Prevención de Fuga Temporal (LeakageGuard).
HealthSignal LATAM — RISA Data V1.0.
"""

import pytest
from datetime import datetime
import pandas as pd
from ingestion.models import CDMRecord
from pipeline.leakage_guard import LeakageGuard


def test_leakage_guard_blocks_future_records():
    guard = LeakageGuard()
    t_decision = datetime(2026, 7, 10, 12, 0, 0)

    rec_past = CDMRecord(
        record_id="REC-001",
        patient_id="PAT-001",
        source_file="vital_signs.csv",
        event_datetime="2026-07-10 10:00:00",
        available_datetime="2026-07-10 11:30:00"
    )
    rec_exact = CDMRecord(
        record_id="REC-002",
        patient_id="PAT-001",
        source_file="vital_signs.csv",
        event_datetime="2026-07-10 11:59:00",
        available_datetime="2026-07-10 12:00:00"
    )
    rec_future = CDMRecord(
        record_id="REC-003",
        patient_id="PAT-001",
        source_file="vital_signs.csv",
        event_datetime="2026-07-10 11:50:00",
        available_datetime="2026-07-10 12:01:00"  # Fuga temporal!
    )

    records = [rec_past, rec_exact, rec_future]
    allowed = guard.filter_by_decision_time(records, t_decision)

    assert len(allowed) == 2
    assert "REC-001" in [r.record_id for r in allowed]
    assert "REC-002" in [r.record_id for r in allowed]
    assert "REC-003" not in [r.record_id for r in allowed]


def test_leakage_guard_dataframe_support():
    guard = LeakageGuard()
    t_decision = datetime(2026, 7, 10, 12, 0, 0)

    df = pd.DataFrame([
        {"record_id": "R1", "available_datetime": "2026-07-10 11:00:00"},
        {"record_id": "R2", "available_datetime": "2026-07-10 12:00:00"},
        {"record_id": "R3", "available_datetime": "2026-07-10 12:05:00"}
    ])

    df_safe = guard.filter_available_records(df, t_decision)
    assert len(df_safe) == 2
    assert set(df_safe["record_id"]) == {"R1", "R2"}


if __name__ == "__main__":
    pytest.main([__file__])
