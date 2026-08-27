"""
Adaptador de Ingesta para Datasets CSV (RISA Data V1.0).
Implementa extract_raw() para capturar datos crudos y map_to_cdm() para transformar
a la estructura del Common Data Model sin aplicar lógica de limpieza.
"""

import csv
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from ingestion.base_adapter import BaseHospitalAdapter
from ingestion.models import RawRecord, CDMRecord
from ingestion.factory import HospitalIngestionFactory


@HospitalIngestionFactory.register("RISA_CSV")
@HospitalIngestionFactory.register("CSV")
class RISACSVAdapter(BaseHospitalAdapter):
    """
    Adaptador para ingesta de archivos CSV del ecosistema RISA Data V1.0.
    """
    def __init__(self, hospital_id: str = "RISA_CORE", source_name: str = "RISA_CSV"):
        super().__init__(hospital_id=hospital_id, source_name=source_name)

    def extract_raw(self, source_config: Dict[str, Any]) -> List[RawRecord]:
        """
        Lee un archivo CSV o lote de registros y produce una lista de RawRecords inmutables.
        Configuración esperada:
          - file_path: Ruta al archivo CSV
          - max_rows: Opcional, límite de filas a leer
        """
        file_path = source_config.get("file_path")
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo no encontrado en ruta: {file_path}")

        max_rows = source_config.get("max_rows", None)
        raw_records: List[RawRecord] = []
        source_file_name = Path(file_path).name

        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            count = 0
            for raw_row in reader:
                # Limpiar posibles caracteres BOM residuales en claves
                row = {k.lstrip("\ufeff").strip(): v for k, v in raw_row.items() if k is not None}

                # Determinar el record_id según la tabla o columna primaria
                record_id = (
                    row.get("observation_id")
                    or row.get("wearable_observation_id")
                    or row.get("device_observation_id")
                    or row.get("lab_result_id")
                    or row.get("administration_id")
                    or row.get("condition_id")
                    or row.get("context_id")
                    or row.get("event_id")
                    or row.get("patient_id")
                    or f"{source_file_name}_{count}"
                )

                raw_rec = RawRecord(
                    record_id=str(record_id),
                    source_file=source_file_name,
                    facility_id=row.get("facility_id", self.hospital_id),
                    raw_payload=row
                )
                raw_records.append(raw_rec)
                count += 1
                if max_rows and count >= max_rows:
                    break

        return raw_records

    def map_to_cdm(self, raw_records: List[RawRecord]) -> List[CDMRecord]:
        """
        Transforma los RawRecords a CDMRecords estandarizados según el esquema de la tabla de origen.
        """
        cdm_records: List[CDMRecord] = []

        for raw in raw_records:
            payload = raw.raw_payload
            source_file = raw.source_file.lower()

            # 1. Signos Vitales (vital_signs.csv)
            if "vital_signs" in source_file:
                val_num = self._safe_float(payload.get("value"))
                cdm_records.append(CDMRecord(
                    record_id=raw.record_id,
                    patient_id=payload.get("patient_id", ""),
                    encounter_id=payload.get("encounter_id"),
                    facility_id=payload.get("facility_id", raw.facility_id),
                    device_id=payload.get("device_id"),
                    source_file=raw.source_file,
                    source_system=payload.get("source_system", "MONITOR_GATEWAY"),
                    variable_code=payload.get("variable_code", ""),
                    value_numeric=val_num,
                    original_unit=payload.get("unit"),
                    event_datetime=payload.get("timestamp"),
                    available_datetime=payload.get("timestamp"), # En gateway monitor, near real time
                    quality_flag=payload.get("quality_flag", "OK"),
                    is_observed=val_num is not None or bool(payload.get("value")),
                    is_retransmission=(payload.get("source_system") == "MONITOR_RETRANSMIT")
                ))

            # 2. Wearables (wearable_observations.csv)
            elif "wearable" in source_file:
                raw_val = payload.get("value")
                val_num = self._safe_float(raw_val)
                val_txt = str(raw_val) if val_num is None and raw_val is not None else None
                cdm_records.append(CDMRecord(
                    record_id=raw.record_id,
                    patient_id=payload.get("patient_id", ""),
                    device_id=payload.get("device_id"),
                    source_file=raw.source_file,
                    source_system="WEARABLE_GATEWAY",
                    variable_code=payload.get("variable_code", ""),
                    value_numeric=val_num,
                    value_text=val_txt,
                    original_unit=payload.get("unit"),
                    event_datetime=payload.get("timestamp"),
                    available_datetime=payload.get("sync_datetime"), # Sync diferido (T_available)
                    quality_flag=payload.get("measurement_quality", "OK"),
                    is_observed=val_num is not None or val_txt is not None
                ))

            # 3. Laboratorio (laboratory_results.csv)
            elif "laboratory" in source_file:
                val_num = self._safe_float(payload.get("result_value"))
                cdm_records.append(CDMRecord(
                    record_id=raw.record_id,
                    patient_id=payload.get("patient_id", ""),
                    encounter_id=payload.get("encounter_id"),
                    facility_id=payload.get("facility_id"),
                    source_file=raw.source_file,
                    source_system=payload.get("source_system", "LAB_SYS"),
                    variable_code=payload.get("test_code", ""),
                    value_numeric=val_num,
                    value_text=payload.get("test_name"),
                    original_unit=payload.get("unit"),
                    event_datetime=payload.get("sample_datetime"), # Momento toma de muestra
                    available_datetime=payload.get("result_datetime"), # Momento resultado disponible
                    quality_flag=payload.get("quality_flag", "OK"),
                    is_observed=val_num is not None
                ))

            # 4. Observaciones de Dispositivo / Calidad (device_observations.csv)
            elif "device_observations" in source_file:
                val_num = self._safe_float(payload.get("value"))
                sig_qual = self._safe_float(payload.get("signal_quality"))
                cdm_records.append(CDMRecord(
                    record_id=raw.record_id,
                    patient_id=payload.get("patient_id", ""),
                    encounter_id=payload.get("encounter_id"),
                    device_id=payload.get("device_id"),
                    source_file=raw.source_file,
                    source_system=payload.get("source_system", "MONITOR_GATEWAY"),
                    variable_code=payload.get("variable_code", "SIGNAL_QUALITY_INDEX"),
                    value_numeric=val_num,
                    original_unit=payload.get("unit"),
                    event_datetime=payload.get("timestamp"),
                    available_datetime=payload.get("timestamp"),
                    signal_quality=sig_qual or val_num,
                    is_observed=val_num is not None
                ))

            # 5. Medicaciones (medication_administrations.csv)
            elif "medication_administrations" in source_file:
                val_num = self._safe_float(payload.get("dose_value"))
                cdm_records.append(CDMRecord(
                    record_id=raw.record_id,
                    patient_id=payload.get("patient_id", ""),
                    encounter_id=payload.get("encounter_id"),
                    source_file=raw.source_file,
                    source_system=payload.get("source_system", "EHR_MED"),
                    variable_code=payload.get("medication_id", ""),
                    value_numeric=val_num,
                    original_unit=payload.get("dose_unit"),
                    event_datetime=payload.get("start_datetime"),
                    available_datetime=payload.get("end_datetime") or payload.get("start_datetime"),
                    quality_flag="OK",
                    is_observed=val_num is not None
                ))

            # 6. Diagnósticos y Antecedentes (conditions.csv)
            elif "conditions" in source_file:
                cdm_records.append(CDMRecord(
                    record_id=raw.record_id,
                    patient_id=payload.get("patient_id", ""),
                    source_file=raw.source_file,
                    source_system=payload.get("source_system", "EHR_CORE"),
                    variable_code=payload.get("condition_category", ""),
                    value_text=payload.get("status", "ACTIVE"),
                    event_datetime=payload.get("onset_date"),
                    available_datetime=payload.get("recorded_datetime") or payload.get("onset_date"),
                    quality_flag="OK",
                    is_observed=True
                ))

            # 7. Fallback para otras tablas (pacientes, encuentros, contexto)
            else:
                cdm_records.append(CDMRecord(
                    record_id=raw.record_id,
                    patient_id=payload.get("patient_id", ""),
                    encounter_id=payload.get("encounter_id"),
                    facility_id=payload.get("facility_id"),
                    device_id=payload.get("device_id"),
                    source_file=raw.source_file,
                    source_system=payload.get("source_system", "GENERIC_CSV"),
                    variable_code=payload.get("variable_code") or payload.get("context_type") or "METADATA",
                    value_text=str(payload),
                    event_datetime=payload.get("timestamp") or payload.get("start_datetime"),
                    available_datetime=payload.get("sync_datetime") or payload.get("end_datetime") or payload.get("start_datetime"),
                    is_observed=True
                ))

        return cdm_records

    @staticmethod
    def _safe_float(val: Any) -> Optional[float]:
        if val is None or str(val).strip() in ("", "None", "null", "NaN", "nan"):
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
