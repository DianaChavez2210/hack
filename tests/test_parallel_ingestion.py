"""
Pruebas Unitarias para Ingesta Paralela Multinúcleo (Multiprocessing).
"""

import pytest
import os
import csv
from pathlib import Path
from ingestion.sinks import CleanStorageSink
from ingestion.orchestrator import IngestionOrchestrator


def test_orchestrator_process_and_save_parallel(tmp_path):
    test_csv = tmp_path / "test_parallel_vitals.csv"
    with open(test_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["observation_id", "patient_id", "variable_code", "value", "unit", "timestamp"])
        for i in range(200):
            writer.writerow([f"OBS-{i:06d}", "PAT-0001", "HR", "75.0", "bpm", "2026-07-10 10:00:00"])

    clean_sink = CleanStorageSink(base_dir=str(tmp_path / "clean"))
    orchestrator = IngestionOrchestrator(clean_sink=clean_sink)

    config = {"file_path": str(test_csv)}
    res = orchestrator.process_and_save_parallel(
        source_type="RISA_CSV",
        hospital_id="TEST_HOSP",
        source_config=config,
        dataset_name="test_parallel_output",
        chunk_size=50,
        max_workers=2
    )

    assert res["status"] == "SUCCESS"
    assert res["raw_count"] == 200
    assert res["clean_count"] == 200
    assert res["chunks_processed"] == 4
    assert res["workers_used"] == 2
    assert os.path.exists(res["clean_csv_path"])


if __name__ == "__main__":
    pytest.main([__file__])
