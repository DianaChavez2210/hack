"""
Módulo de Trazabilidad y Linaje de Auditoría (LineageTracker).
Permite rastrear el camino desde una señal de riesgo hasta los registros CDM y archivos físicos de origen.
"""

import os
import csv
from typing import List, Dict, Any, Tuple
from pathlib import Path


class LineageTracker:
    """
    Grafo de linaje para mantener la trazabilidad de señales.
    Rastrea: signal_id -> feature_name -> record_id -> source_file.
    """
    def __init__(self, output_path: str = "results/lineage_audit.csv"):
        self.output_path = output_path
        self.lineage_store: List[Dict[str, str]] = []

    def register_lineage(
        self,
        signal_id: str,
        feature_name: str,
        record_id: str,
        source_file: str
    ):
        """
        Registra la relación de linaje de una señal con una feature derivada y su registro fuente.
        """
        entry = {
            "signal_id": signal_id,
            "feature_name": feature_name,
            "record_id": record_id,
            "source_file": source_file
        }
        self.lineage_store.append(entry)

    def get_contributing_records(self, signal_id: str) -> List[Tuple[str, str, str]]:
        """
        Retorna una lista de tuplas (record_id, source_file, feature_name)
        que contribuyeron a una señal de riesgo específica.
        """
        contributors = []
        for entry in self.lineage_store:
            if entry["signal_id"] == signal_id:
                contributors.append((entry["record_id"], entry["source_file"], entry["feature_name"]))
        return contributors

    def save_lineage(self, append: bool = True):
        """
        Guarda el historial de linaje en results/lineage_audit.csv para trazabilidad del evaluador.
        """
        if not self.lineage_store:
            return

        out_path = Path(self.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = out_path.exists() and out_path.stat().st_size > 0

        fields = ["signal_id", "feature_name", "record_id", "source_file"]

        mode = "a" if append else "w"
        with open(out_path, mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            if not file_exists or not append:
                writer.writeheader()
            for entry in self.lineage_store:
                writer.writerow(entry)

        # Limpiar el almacén temporal tras guardar
        self.lineage_store.clear()
