"""
Servicio de Carga y Caché de Datos en Memoria (Data Loader Service).
Carga datasets de data/clean/csv/ y results/ con fallback inteligente.
"""

import os
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class DataLoaderService:
    """
    Servicio singleton para disponibilizar datasets limpios y resultados.
    """
    _instance = None

    def __new__(cls, clean_dir: str = "data/clean/csv", results_dir: str = "results"):
        if cls._instance is None:
            cls._instance = super(DataLoaderService, cls).__new__(cls)
            cls._instance.clean_dir = Path(clean_dir)
            cls._instance.results_dir = Path(results_dir)
            cls._instance.data_cache = {}
        return cls._instance

    def load_csv_records(self, filename: str, is_results: bool = False) -> List[Dict[str, Any]]:
        """
        Carga un archivo CSV retornando una lista de diccionarios.
        """
        base_dir = self.results_dir if is_results else self.clean_dir
        filepath = base_dir / filename
        
        cache_key = f"{'results' if is_results else 'clean'}:{filename}"
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]

        if not filepath.exists():
            return []

        records = []
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(row)
            self.data_cache[cache_key] = records
        except Exception as e:
            print(f"[WARN] Error al leer {filepath}: {e}")
            records = []

        return records

    def clear_cache(self):
        self.data_cache.clear()
