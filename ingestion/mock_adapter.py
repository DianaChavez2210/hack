"""
Adaptador Sintético de Prueba (Mock Hospital Adapter).
Genera registros Raw y CDM en memoria para tests unitarios y de estrés.
"""

from typing import List, Dict, Any
from datetime import datetime
from ingestion.base_adapter import BaseHospitalAdapter
from ingestion.models import RawRecord, CDMRecord
from ingestion.factory import HospitalIngestionFactory


@HospitalIngestionFactory.register("MOCK")
class MockHospitalAdapter(BaseHospitalAdapter):
    """
    Adaptador mock para pruebas unitarias e integración sin dependencias externas.
    """
    def __init__(self, hospital_id: str = "HOSP_MOCK_01", source_name: str = "MOCK_SOURCE"):
        super().__init__(hospital_id=hospital_id, source_name=source_name)

    def extract_raw(self, source_config: Dict[str, Any]) -> List[RawRecord]:
        num_records = source_config.get("num_records", 5)
        raw_records: List[RawRecord] = []

        for i in range(num_records):
            rec_id = f"MOCK_REC_{i+1:04d}"
            payload = {
                "observation_id": rec_id,
                "patient_id": f"PAT-{(i%2)+1:04d}",
                "timestamp": "2026-07-10 09:00:00",
                "variable_code": "HR" if i % 2 == 0 else "TEMP",
                "value": "75.5" if i % 2 == 0 else "98.6",
                "unit": "bpm" if i % 2 == 0 else "degF",
                "quality_flag": "OK" if i != 3 else "NOISE",
                "source_system": "MONITOR_GATEWAY" if i != 4 else "MONITOR_RETRANSMIT"
            }
            raw_records.append(RawRecord(
                record_id=rec_id,
                source_file="mock_vitals.csv",
                facility_id=self.hospital_id,
                raw_payload=payload
            ))

        return raw_records

    def map_to_cdm(self, raw_records: List[RawRecord]) -> List[CDMRecord]:
        cdm_records: List[CDMRecord] = []
        for raw in raw_records:
            p = raw.raw_payload
            val = float(p["value"]) if p.get("value") else None
            cdm_records.append(CDMRecord(
                record_id=raw.record_id,
                patient_id=p.get("patient_id", ""),
                facility_id=raw.facility_id,
                source_file=raw.source_file,
                source_system=p.get("source_system", "MOCK_SYS"),
                variable_code=p.get("variable_code", ""),
                value_numeric=val,
                original_unit=p.get("unit"),
                event_datetime=p.get("timestamp"),
                available_datetime=p.get("timestamp"),
                quality_flag=p.get("quality_flag", "OK"),
                is_observed=val is not None,
                is_retransmission=(p.get("source_system") == "MONITOR_RETRANSMIT")
            ))
        return cdm_records
