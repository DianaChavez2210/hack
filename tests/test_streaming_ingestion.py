"""
Pruebas Unitarias para Ingesta Streaming por Lotes (Chunking).
"""

import pytest
import os
import csv
from pathlib import Path
from ingestion.models import CDMRecord
from ingestion.csv_adapter import RISACSVAdapter
from ingestion.orchestrator import IngestionOrchestrator
from ingestion.sinks import CleanStorageSink


def test_csv_adapter_extract_raw_chunks(tmp_path):
    # Crear archivo CSV temporal con 150 filas
    test_csv = tmp_path / "test_vitals.csv"
    with open(test_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["observation_id", "patient_id", "value", "unit", "timestamp"])
        for i in range(150):
            writer.writerow([f"OBS-{i:06d}", "PAT-0001", "72.0", "bpm", "2026-07-10 10:00:00"])

    adapter = RISACSVAdapter()
    config = {"file_path": str(test_csv)}
    chunks = list(adapter.extract_raw_chunks(config, chunk_size=50))

    assert len(chunks) == 3
    assert len(chunks[0]) == 50
    assert len(chunks[1]) == 50
    assert len(chunks[2]) == 50


def test_orchestrator_process_and_save_stream(tmp_path):
    test_csv = tmp_path / "test_stream_vitals.csv"
    with open(test_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["observation_id", "patient_id", "variable_code", "value", "unit", "timestamp"])
        for i in range(120):
            writer.writerow([f"OBS-{i:06d}", "PAT-0001", "HR", "75.0", "bpm", "2026-07-10 10:00:00"])

    clean_sink = CleanStorageSink(base_dir=str(tmp_path / "clean"))
    orchestrator = IngestionOrchestrator(clean_sink=clean_sink)

    config = {"file_path": str(test_csv)}
    res = orchestrator.process_and_save_stream(
        source_type="RISA_CSV",
        hospital_id="TEST_HOSP",
        source_config=config,
        dataset_name="test_stream_output",
        chunk_size=50
    )

    assert res["status"] == "SUCCESS"
    assert res["raw_count"] == 120
    assert res["clean_count"] == 120
    assert res["chunks_processed"] == 3
    assert os.path.exists(res["clean_csv_path"])


if __name__ == "__main__":
    pytest.main([__file__])
