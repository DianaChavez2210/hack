"""
Servicio de Carga e Integración con PostgreSQL risa_db y Caché de Datos (Data Loader Service).
Soporta consultas relacionales nativas a PostgreSQL 18 con fallback inteligente a CSV.
"""

import os
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


def serializable_value(val: Any) -> Any:
    """Convierte tipos no serializables como datetime, date, Decimal a tipos nativos."""
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    try:
        from decimal import Decimal
        if isinstance(val, Decimal):
            return float(val)
    except ImportError:
        pass
    return val


class DataLoaderService:
    """
    Servicio singleton para disponibilizar datasets limpios y resultados
    conectados dinámicamente a la base de datos de PostgreSQL risa_db.
    """
    _instance = None

    def __new__(cls, clean_dir: str = "data/clean/csv", results_dir: str = "results"):
        if cls._instance is None:
            cls._instance = super(DataLoaderService, cls).__new__(cls)
            cls._instance.clean_dir = Path(clean_dir)
            cls._instance.results_dir = Path(results_dir)
            cls._instance.data_cache = {}
            cls._instance.db_host = os.getenv("POSTGRES_HOST", "127.0.0.1")
            cls._instance.db_port = int(os.getenv("POSTGRES_PORT", "5432"))
            cls._instance.db_name = os.getenv("POSTGRES_DB", "risa_db")
            cls._instance.db_user = os.getenv("POSTGRES_USER", "postgres")
            cls._instance.db_pass = os.getenv("POSTGRES_PASSWORD", "JoSeSiTo%_10")
        return cls._instance

    def get_db_connection(self):
        """Retorna una conexión activa a la base de datos PostgreSQL local risa_db."""
        if not HAS_PSYCOPG2:
            return None
        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_pass,
                client_encoding="UTF8",
                connect_timeout=3
            )
            return conn
        except Exception as e:
            print(f"[WARN] No se pudo conectar a PostgreSQL ({self.db_name}): {e}")
            return None

    def query_db(self, query: str, params: Optional[tuple] = None, schema: str = "risa_raw") -> List[Dict[str, Any]]:
        """
        Ejecuta una consulta SQL en PostgreSQL risa_db y retorna los resultados como lista de diccionarios.
        """
        conn = self.get_db_connection()
        if not conn:
            return []
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if schema:
                    cur.execute(f"SET search_path TO {schema}, public;")
                cur.execute(query, params)
                rows = cur.fetchall()
                records = []
                for r in rows:
                    rec = {k: serializable_value(v) for k, v in dict(r).items()}
                    records.append(rec)
                return records
        except Exception as e:
            print(f"[WARN] Error ejecutando consulta SQL en PostgreSQL: {e}")
            return []
        finally:
            conn.close()

    def load_csv_records(self, filename: str, is_results: bool = False) -> List[Dict[str, Any]]:
        """
        Carga un archivo CSV retornando una lista de diccionarios (fallback).
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

