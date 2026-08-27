"""
Pruebas Unitarias para el Módulo de Ingesta, Fábrica y Adaptadores.
"""

import sys
from pathlib import Path

# Agregar raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from ingestion.models import RawRecord, CDMRecord
from ingestion.factory import HospitalIngestionFactory
from ingestion.base_adapter import BaseHospitalAdapter
from ingestion.mock_adapter import MockHospitalAdapter
from ingestion.sinks import RawStorageSink, CleanStorageSink


def test_factory_registration_and_instance():
    """Verifica que la fábrica registre e instancie correctamente los adaptadores."""
    adapters = HospitalIngestionFactory.list_available_adapters()
    assert "MOCK" in adapters
    assert "RISA_CSV" in adapters or "CSV" in adapters

    adapter = HospitalIngestionFactory.get_adapter("MOCK", hospital_id="HOSP_TEST")
    assert isinstance(adapter, BaseHospitalAdapter)
    assert adapter.hospital_id == "HOSP_TEST"


def test_mock_adapter_flow():
    """Verifica la extracción RAW y mapeo a CDM del adaptador Mock."""
    adapter = MockHospitalAdapter(hospital_id="HOSP_01")
    raw_records = adapter.extract_raw({"num_records": 4})
    
    assert len(raw_records) == 4
    assert raw_records[0].record_id == "MOCK_REC_0001"
    assert raw_records[0].facility_id == "HOSP_01"
    
    cdm_records = adapter.map_to_cdm(raw_records)
    assert len(cdm_records) == 4
    assert cdm_records[0].record_id == "MOCK_REC_0001"
    assert cdm_records[0].variable_code in ("HR", "TEMP")
    assert cdm_records[0].is_observed is True


def test_storage_sinks_temporary(tmp_path):
    """Verifica que los sinks escriban archivos JSONL y CSV sin errores."""
    raw_sink = RawStorageSink(base_dir=str(tmp_path / "raw"))
    clean_sink = CleanStorageSink(base_dir=str(tmp_path / "clean"))

    raw_rec = RawRecord(record_id="REC_01", source_file="test.csv", raw_payload={"val": 10})
    raw_path = raw_sink.save_records([raw_rec], partition_name="test_raw")
    assert Path(raw_path).exists()

    cdm_rec = CDMRecord(
        record_id="REC_01",
        patient_id="PAT-0001",
        source_file="test.csv",
        variable_code="HR",
        value_numeric=72.0,
        event_datetime="2026-07-10 09:00:00"
    )
    clean_path = clean_sink.save_records([cdm_rec], dataset_name="test_clean")
    assert Path(clean_path).exists()
    assert (tmp_path / "clean" / "jsonl" / "test_clean.jsonl").exists()
    assert (tmp_path / "clean" / "csv" / "test_clean.csv").exists()


if __name__ == "__main__":
    test_factory_registration_and_instance()
    test_mock_adapter_flow()
    print("[OK] Todos los tests de ingestion pasaron correctamente.")
