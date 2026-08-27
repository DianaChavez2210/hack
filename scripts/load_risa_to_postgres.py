"""
Proceso Independiente de Carga de RISA Data V1.0 a PostgreSQL 18.
Este script es una herramienta auxiliar fuera del pipeline de la aplicación.

Uso:
    python scripts/load_risa_to_postgres.py --dbname risa_db --user postgres --password secret --create-schema
"""

import os
import sys
import csv
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Cargar automáticamente el archivo .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_file = Path(".env")
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8-sig", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        os.environ.setdefault(k, v)
        except Exception:
            pass

# Intentar importar psycopg2 o psycopg (v3)
HAS_PSYCOPG2 = False
HAS_PSYCOPG3 = False

try:
    import psycopg2
    from psycopg2.extras import execute_values
    HAS_PSYCOPG2 = True
except ImportError:
    try:
        import psycopg
        HAS_PSYCOPG3 = True
    except ImportError:
        pass


def safe_str(val: Any) -> str:
    """
    Decodifica o convierte objetos de excepción o cadenas a string sin fallos por UTF-8 en Windows (cp1252).
    """
    if isinstance(val, Exception):
        try:
            return str(val)
        except UnicodeDecodeError:
            try:
                if hasattr(val, "args") and val.args and isinstance(val.args[0], bytes):
                    return val.args[0].decode("cp1252", errors="replace")
                return repr(val)
            except Exception:
                return repr(val)
    return str(val)


def execute_sql_file(conn, sql_file_path: str, schema_name: str = "risa_raw"):
    """Ejecuta el archivo DDL SQL para crear la estructura de base de datos en PostgreSQL 18."""
    print(f"[INFO] Creando esquema y tablas desde: {sql_file_path}...")
    with open(sql_file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        sql_content = f.read()

    # Reemplazar schema si se especificó uno diferente
    if schema_name != "risa_raw":
        sql_content = sql_content.replace("CREATE SCHEMA IF NOT EXISTS risa_raw;", f"CREATE SCHEMA IF NOT EXISTS {schema_name};")
        sql_content = sql_content.replace("SET search_path TO risa_raw, public;", f"SET search_path TO {schema_name}, public;")

    with conn.cursor() as cur:
        cur.execute(sql_content)
    conn.commit()
    print("[OK] Estructura de esquemas y tablas creada con éxito.")


def load_csv_to_table(conn, csv_path: Path, table_name: str, schema_name: str = "risa_raw"):
    """
    Carga masiva de un archivo CSV en una tabla PostgreSQL con soporte UTF-8 con BOM y reemplazo seguro.
    """
    if not csv_path.exists():
        print(f"[WARN] Archivo no encontrado: {csv_path}. Saltando...")
        return 0

    target_table = f"{schema_name}.{table_name}"
    
    with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        fieldnames = [k.lstrip("\ufeff").strip() for k in reader.fieldnames] if reader.fieldnames else []
        
        if not fieldnames:
            return 0

        rows = []
        for raw_row in reader:
            clean_row = {}
            for k, v in raw_row.items():
                if k is None:
                    continue
                clean_k = k.lstrip("\ufeff").strip()
                clean_v = v.strip() if isinstance(v, str) else v
                # Convertir cadenas vacías o 'None' a None (SQL NULL)
                if clean_v in ("", "None", "null", "NaN", "nan"):
                    clean_v = None
                clean_row[clean_k] = clean_v
            rows.append(clean_row)

    if not rows:
        return 0

    cols = list(rows[0].keys())
    col_names_str = ", ".join([f'"{c}"' for c in cols])
    placeholders = ", ".join(["%s"] * len(cols))
    
    insert_query = f'INSERT INTO {target_table} ({col_names_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;'
    data_tuples = [tuple(r.get(c) for c in cols) for r in rows]

    cur = conn.cursor()
    if HAS_PSYCOPG2:
        execute_values(cur, f'INSERT INTO {target_table} ({col_names_str}) VALUES %s ON CONFLICT DO NOTHING;', data_tuples, page_size=1000)
    else:
        cur.executemany(insert_query, data_tuples)
    
    conn.commit()
    cur.close()
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="Herramienta de Carga de RISA Data V1.0 a PostgreSQL 18")
    parser.add_argument("--host", type=str, default=os.getenv("POSTGRES_HOST", "localhost"), help="Host de PostgreSQL")
    parser.add_argument("--port", type=int, default=int(os.getenv("POSTGRES_PORT", 5432)), help="Puerto de PostgreSQL")
    parser.add_argument("--dbname", type=str, default=os.getenv("POSTGRES_DB", "risa_db"), help="Nombre de la base de datos")
    parser.add_argument("--user", type=str, default=os.getenv("POSTGRES_USER", "postgres"), help="Usuario de PostgreSQL")
    parser.add_argument("--password", type=str, default=os.getenv("POSTGRES_PASSWORD", "postgres"), help="Contraseña de PostgreSQL")
    parser.add_argument("--schema-name", type=str, default="risa_raw", help="Nombre del esquema en PostgreSQL")
    parser.add_argument("--data-dir", type=str, default="01_RISA_DATA_V1_0", help="Directorio raíz del dataset RISA")
    parser.add_argument("--create-schema", action="store_true", help="Ejecuta el script SQL de creación de tablas antes de cargar")

    args = parser.parse_args()

    if not HAS_PSYCOPG2 and not HAS_PSYCOPG3:
        print("[ERROR] Se requiere la librería 'psycopg2' o 'psycopg' instalada en Python.")
        print("        Por favor instala con: pip install psycopg2-binary")
        sys.exit(1)

    print("=" * 75)
    print("  CARGADOR INDEPENDIENTE RISA DATA V1.0 -> POSTGRESQL 18")
    print(f"  Base de Datos: {args.user}@{args.host}:{args.port}/{args.dbname}")
    print(f"  Esquema Objetivo: {args.schema_name}")
    print(f"  Directorio Dataset: {args.data_dir}")
    print("=" * 75)

    try:
        if HAS_PSYCOPG2:
            conn = psycopg2.connect(
                host=args.host,
                port=args.port,
                dbname=args.dbname,
                user=args.user,
                password=args.password,
                client_encoding="UTF8"
            )
            conn.set_client_encoding("UTF8")
        else:
            conn = psycopg.connect(
                host=args.host,
                port=args.port,
                dbname=args.dbname,
                user=args.user,
                password=args.password
            )
        print("[OK] Conexión establecida exitosamente con PostgreSQL 18.")
    except Exception as e:
        err_msg = safe_str(e)
        print(f"[ERROR] No se pudo conectar a PostgreSQL: {err_msg}")
        sys.exit(1)

    script_dir = Path(__file__).parent
    sql_ddl_path = script_dir / "schema_postgresql.sql"

    if args.create_schema and sql_ddl_path.exists():
        execute_sql_file(conn, str(sql_ddl_path), schema_name=args.schema_name)

    base_data = Path(args.data_dir)

    # Lista ordenada por dependencias de Claves Foráneas (FKs)
    load_sequence = [
        # 1. Catálogos y Metadatos (sin FKs)
        ("05_metadata/units_catalog.csv", "units_catalog"),
        ("05_metadata/source_catalog.csv", "source_catalog"),
        ("05_metadata/variable_catalog.csv", "variable_catalog"),
        ("05_metadata/data_dictionary.csv", "data_dictionary"),
        
        # 2. Entidades Maestras (Raíz de FKs)
        ("01_master/healthcare_facilities.csv", "healthcare_facilities"),
        ("01_master/patients.csv", "patients"),
        ("01_master/devices.csv", "devices"),
        ("01_master/encounters.csv", "encounters"),
        
        # 3. Datos Clínicos
        ("02_clinical/medications.csv", "medications"),
        ("02_clinical/conditions.csv", "conditions"),
        ("02_clinical/medication_administrations.csv", "medication_administrations"),
        ("02_clinical/laboratory_results.csv", "laboratory_results"),
        
        # 4. Monitoreo y Telemetría
        ("03_monitoring/vital_signs.csv", "vital_signs"),
        ("03_monitoring/wearable_observations.csv", "wearable_observations"),
        ("03_monitoring/device_observations.csv", "device_observations"),
        
        # 5. Contexto y Conectividad
        ("04_context/patient_context.csv", "patient_context"),
        ("04_context/connectivity_events.csv", "connectivity_events"),
    ]

    total_rows = 0
    print("\n[INFO] Iniciando carga de datos...")
    
    for rel_csv, table_name in load_sequence:
        csv_file = base_data / rel_csv
        print(f"  • Cargando {table_name} desde {rel_csv}...", end="", flush=True)
        try:
            count = load_csv_to_table(conn, csv_file, table_name, schema_name=args.schema_name)
            total_rows += count
            print(f" [OK] ({count:,} filas)")
        except Exception as e:
            err_msg = safe_str(e)
            print(f" [ERROR]: {err_msg}")

    conn.close()

    print("\n" + "=" * 75)
    print("  RESUMEN DE CARGA POSTGRESQL 18")
    print(f"  Filas Totales Insertadas: {total_rows:,}")
    print("  Estado: PROCESO COMPLETADO EXITOSAMENTE")
    print("=" * 75)


if __name__ == "__main__":
    main()
