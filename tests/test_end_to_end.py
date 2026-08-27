"""
Pruebas de Integración End-to-End para el IngestionOrchestrator.
"""

import sys
from pathlib import Path

# Agregar raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from ingestion.orchestrator import IngestionOrchestrator
from ingestion.sinks import RawStorageSink, CleanStorageSink


def test_orchestrator_end_to_end(tmp_path):
    """Ejecuta el flujo completo de ingesta, calidad y persistencia con un adaptador Mock."""
    raw_sink = RawStorageSink(base_dir=str(tmp_path / "raw"))
    clean_sink = CleanStorageSink(base_dir=str(tmp_path / "clean"))

    orchestrator = IngestionOrchestrator(
        raw_sink=raw_sink,
        clean_sink=clean_sink
    )

    result = orchestrator.process_and_save(
        source_type="MOCK",
        hospital_id="HOSP_E2E_01",
        source_config={"num_records": 10},
        dataset_name="e2e_test_dataset"
    )

    assert result["status"] == "SUCCESS"
    assert result["raw_count"] == 10
    assert result["clean_count"] == 10
    assert Path(result["raw_path"]).exists()
    assert Path(result["clean_path"]).exists()


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        test_orchestrator_end_to_end(Path(tmp))
    print("[OK] Test de integracion End-to-End completado con exito.")
