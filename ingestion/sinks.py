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

class RawStorageSink:
    """
    Persiste copias inmutables de los registros crudos en la capa data/raw/.
    Conserva metadatos de auditoría y trazabilidad del payload original.
    """
    def __init__(self, base_dir: str = "data/raw"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_records(
        self, records: List[RawRecord], partition_name: str = "raw_batch", append: bool = False
    ) -> str:
        """
        Guarda una lista de RawRecords en formato JSON Lines.
        Si append=False (por defecto para el primer bloque), sobrescribe el archivo previo.
        """
        if not records:
            return ""

        file_path = self.base_dir / f"{partition_name}.jsonl"
        mode = "a" if append and file_path.exists() else "w"
        with open(file_path, mode, encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
        
        return str(file_path)


class CleanStorageSink:
    """
    Persiste registros procesados y validados del Common Data Model en subcarpetas estructuradas:
    - data/clean/jsonl/
    - data/clean/csv/
    """
    def __init__(self, base_dir: str = "data/clean"):
        self.base_dir = Path(base_dir)
        self.jsonl_dir = self.base_dir / "jsonl"
        self.csv_dir = self.base_dir / "csv"

        self.jsonl_dir.mkdir(parents=True, exist_ok=True)
        self.csv_dir.mkdir(parents=True, exist_ok=True)

    def save_records(
        self, records: List[CDMRecord], dataset_name: str = "clean_observations", append: bool = False
    ) -> str:
        """
        Guarda una lista de CDMRecords en subcarpetas separadas JSONL y CSV.
        Si append=False (por defecto para el primer bloque), reinicia los archivos de destino.
        """
        if not records:
            return ""

        # 1. Guardar en carpeta jsonl/
        jsonl_path = self.jsonl_dir / f"{dataset_name}.jsonl"
        jsonl_mode = "a" if append and jsonl_path.exists() else "w"
        with open(jsonl_path, jsonl_mode, encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

        # 2. Guardar en carpeta csv/
        csv_path = self.csv_dir / f"{dataset_name}.csv"
        file_exists = csv_path.exists() and append

        # Determinar dinámica de cabeceras basada en los registros a exportar
        sample_dict = records[0].to_dict()
        fields = list(sample_dict.keys())

        csv_mode = "a" if file_exists else "w"
        with open(csv_path, csv_mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            for rec in records:
                writer.writerow(rec.to_dict())

        return str(csv_path)


class AuditStorageSink:
    """
    Persiste el registro de auditoría de decisiones de calidad de datos, errores e incidencias
    en archivos de registro .log en data/logs/.
    """
    def __init__(self, base_dir: str = "data/logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_audit_entries(
        self, entries: List[Any], log_name: str = "ingestion_processing", append: bool = True
    ) -> str:
        """
        Guarda las entradas de auditoría e incidencias en un archivo de log (.log).
        """
        if not entries:
            return ""

        log_path = self.base_dir / f"{log_name}.log"
        log_mode = "a" if append and log_path.exists() else "w"

        with open(log_path, log_mode, encoding="utf-8") as f:
            for entry in entries:
                data = entry.to_dict() if hasattr(entry, "to_dict") else dict(entry)
                timestamp = data.get("timestamp", "")
                stage = data.get("stage", "PROCESSING")
                action = data.get("action", "INFO")
                rec_id = data.get("record_id", "GLOBAL")
                src_file = data.get("source_file", "UNKNOWN")
                reason = data.get("reason", "")
                details = data.get("details", "")
                
                log_line = f"{timestamp} [{action}] [{stage}] file={src_file} rec_id={rec_id} - {reason}"
                if details:
                    log_line += f" | Details: {details}"
                f.write(log_line + "\n")

        return str(log_path)

