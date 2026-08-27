"""
Módulos de Persistencia (Storage Sinks) para las Capas RAW y CLEAN.
Desacopla el almacenamiento de datos del procesamiento y orquestación.
"""

import os
import json
import csv
from typing import List, Dict, Any
from pathlib import Path
from ingestion.models import RawRecord, CDMRecord


class RawStorageSink:
    """
    Persiste copias inmutables de los registros crudos en la capa data/raw/.
    Conserva metadatos de auditoría y trazabilidad del payload original.
    """
    def __init__(self, base_dir: str = "data/raw"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_records(self, records: List[RawRecord], partition_name: str = "raw_batch") -> str:
        """
        Guarda una lista de RawRecords en formato JSON Lines inmutable.
        """
        if not records:
            return ""

        file_path = self.base_dir / f"{partition_name}.jsonl"
        with open(file_path, "a", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
        
        return str(file_path)


class CleanStorageSink:
    """
    Persiste registros procesados y validados del Common Data Model en data/clean/.
    """
    def __init__(self, base_dir: str = "data/clean"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_records(self, records: List[CDMRecord], dataset_name: str = "clean_observations") -> str:
        """
        Guarda una lista de CDMRecords en formato JSON Lines y CSV estructurado.
        """
        if not records:
            return ""

        # 1. Guardar en JSON Lines
        jsonl_path = self.base_dir / f"{dataset_name}.jsonl"
        with open(jsonl_path, "a", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

        # 2. Guardar en CSV para inspección rápida
        csv_path = self.base_dir / f"{dataset_name}.csv"
        file_exists = csv_path.exists()
        
        fields = [
            "record_id", "patient_id", "encounter_id", "facility_id", "device_id",
            "source_file", "source_system", "variable_code", "value_numeric",
            "value_text", "original_unit", "canonical_unit", "converted_value",
            "event_datetime", "available_datetime", "latency_seconds",
            "is_observed", "is_imputed", "imputation_method", "quality_flag",
            "signal_quality", "is_retransmission", "plausibility_status"
        ]

        with open(csv_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            for rec in records:
                writer.writerow(rec.to_dict())

        return str(csv_path)


class AuditStorageSink:
    """
    Persiste el registro de auditoría de decisiones de calidad de datos
    (motivos de eliminación, corrección, conversión o flags).
    """
    def __init__(self, base_dir: str = "data/clean"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_audit_entries(self, entries: List[Any], log_name: str = "ingestion_audit_log") -> str:
        """
        Guarda las entradas de auditoría en JSONL y CSV.
        """
        if not entries:
            return ""

        # 1. JSON Lines
        jsonl_path = self.base_dir / f"{log_name}.jsonl"
        with open(jsonl_path, "a", encoding="utf-8") as f:
            for entry in entries:
                data = entry.to_dict() if hasattr(entry, "to_dict") else dict(entry)
                f.write(json.dumps(data, ensure_ascii=False) + "\n")

        # 2. CSV para auditoría manual de parámetros y reglas
        csv_path = self.base_dir / f"{log_name}.csv"
        file_exists = csv_path.exists()
        fields = [
            "timestamp", "record_id", "patient_id", "source_file", "variable_code",
            "stage", "action", "reason", "original_value", "corrected_value", "details"
        ]

        with open(csv_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            for entry in entries:
                data = entry.to_dict() if hasattr(entry, "to_dict") else dict(entry)
                writer.writerow(data)

        return str(csv_path)

