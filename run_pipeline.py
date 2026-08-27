"""
Punto de Entrada CLI para el Pipeline de Ingesta y Calidad de Datos (RISA Data V1.0).
Ejecuta la ingesta completa desde 01_RISA_DATA_V1_0/ hacia data/raw/ y data/clean/.
"""

import os
import sys
import csv
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Agregar directorio raíz al path de Python
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from ingestion.orchestrator import IngestionOrchestrator


def load_master_context(base_path: Path) -> Dict[str, Any]:
    """Carga en memoria las tablas maestras para validaciones de integridad referencial y temporal."""
    patients_dict = {}
    encounters_dict = {}
    devices_dict = {}
    patient_contexts = []
    connectivity_events = []

    pat_file = base_path / "01_master/patients.csv"
    if pat_file.exists():
        with open(pat_file, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row.get("patient_id"):
                    patients_dict[row["patient_id"]] = row

    enc_file = base_path / "01_master/encounters.csv"
    if enc_file.exists():
        with open(enc_file, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row.get("encounter_id"):
                    encounters_dict[row["encounter_id"]] = row

    dev_file = base_path / "01_master/devices.csv"
    if dev_file.exists():
        with open(dev_file, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row.get("device_id"):
                    devices_dict[row["device_id"]] = row

    ctx_file = base_path / "04_context/patient_context.csv"
    if ctx_file.exists():
        with open(ctx_file, "r", encoding="utf-8-sig") as f:
            patient_contexts = list(csv.DictReader(f))

    conn_file = base_path / "04_context/connectivity_events.csv"
    if conn_file.exists():
        with open(conn_file, "r", encoding="utf-8-sig") as f:
            connectivity_events = list(csv.DictReader(f))

    return {
        "patients_dict": patients_dict,
        "encounters_dict": encounters_dict,
        "devices_dict": devices_dict,
        "patient_contexts": patient_contexts,
        "connectivity_events": connectivity_events
    }


def run_risa_ingestion(
    dataset_dir: str = "01_RISA_DATA_V1_0",
    max_rows_per_table: Optional[int] = None,
    table_filter: str = "all"
):
    """
    Ejecuta el pipeline de ingesta para todas las tablas de RISA Data V1.0 sin truncamiento por defecto.
    """
    base_path = Path(dataset_dir)
    if not base_path.exists():
        print(f"[ERROR] Directorio del dataset no encontrado: {dataset_dir}")
        return

    # Catálogos de normalización
    units_cat = str(base_path / "05_metadata" / "units_catalog.csv")
    var_cat = str(base_path / "05_metadata" / "variable_catalog.csv")

    orchestrator = IngestionOrchestrator(
        units_catalog_path=units_cat if os.path.exists(units_cat) else None,
        variable_catalog_path=var_cat if os.path.exists(var_cat) else None
    )

    # Precarga de contexto maestro para validación de las 13 reglas de integridad
    master_ctx = load_master_context(base_path)
    orchestrator.set_master_context(**master_ctx)

    # Definición completa de tablas objetivo por dominio
    tables_to_ingest = [
        # Dominio 01: Maestros
        ("01_master/patients.csv", "patients", "EHR_SYSTEM"),
        ("01_master/encounters.csv", "encounters", "EHR_SYSTEM"),
        ("01_master/devices.csv", "devices", "DEVICE_GATEWAY"),
        ("01_master/healthcare_facilities.csv", "facilities", "EHR_SYSTEM"),
        # Dominio 02: Clínicos y Laboratorios
        ("02_clinical/conditions.csv", "conditions", "EHR_SYSTEM"),
        ("02_clinical/laboratory_results.csv", "lab_results", "CENTRAL_LAB"),
        ("02_clinical/medication_administrations.csv", "medications", "EHR_MED"),
        # Dominio 03: Monitoreo y Telemetría
        ("03_monitoring/vital_signs.csv", "vital_signs", "HOSP_MONITOR"),
        ("03_monitoring/wearable_observations.csv", "wearables", "WEARABLE_CENTER"),
        ("03_monitoring/device_observations.csv", "device_observations", "DEVICE_GATEWAY"),
        # Dominio 04: Contexto y Conectividad
        ("04_context/patient_context.csv", "patient_context", "WEARABLE_GATEWAY"),
        ("04_context/connectivity_events.csv", "connectivity_events", "DEVICE_GATEWAY"),
    ]

    effective_max_rows = None if not max_rows_per_table or max_rows_per_table <= 0 else max_rows_per_table

    print("=" * 70)
    print("  HEALTHSIGNAL LATAM — SISTEMA DE INGESTA Y CALIDAD DE DATOS")
    print(f"  Directorio Fuente: {dataset_dir}")
    print(f"  Modo de Procesamiento: {'TODOS LOS REGISTROS (COMPLETO)' if effective_max_rows is None else f'Muestra (Máx {effective_max_rows} filas por tabla)'}")
    print("=" * 70)

    results = []

    for rel_path, dataset_name, hospital_id in tables_to_ingest:
        if table_filter != "all" and table_filter not in dataset_name and table_filter not in rel_path:
            continue

        file_path = base_path / rel_path
        if not file_path.exists():
            print(f"[WARN] Archivo no encontrado: {file_path}. Saltando...")
            continue

        print(f"\n[INFO] Procesando completo: {rel_path}...")
        try:
            res = orchestrator.process_and_save(
                source_type="RISA_CSV",
                hospital_id=hospital_id,
                source_config={
                    "file_path": str(file_path),
                    "max_rows": effective_max_rows
                },
                dataset_name=dataset_name
            )
            results.append(res)
            print(f"  [OK] RAW guardado en: {res['raw_path']} ({res['raw_count']} registros)")
            print(f"  [OK] CLEAN JSONL: {res['clean_jsonl_path']}")
            print(f"  [OK] CLEAN CSV:   {res['clean_csv_path']} ({res['clean_count']} registros limpios)")
            if res.get('audit_path'):
                print(f"  [OK] LOG DE INCIDENCIAS: {res['audit_path']} ({res['audit_entries_count']} incidencias registradas)")
            if res.get("audit_actions"):
                actions_str = ", ".join(f"{k}={v}" for k, v in res["audit_actions"].items())
                print(f"       Acciones de Calidad: {actions_str}")
        except Exception as e:
            print(f"  [ERROR] Fallo al procesar {rel_path}: {e}")

    print("\n" + "=" * 70)
    print("  RESUMEN FINAL DE INGESTA, CALIDAD Y AUDITORIA (PROCESAMIENTO COMPLETO)")
    print("=" * 70)
    for r in results:
        actions_str = ", ".join(f"{k}={v}" for k, v in r["audit_actions"].items()) if r.get("audit_actions") else "Sin incidencias"
        print(f"  * {r['source_type']} [{r['hospital_id']}]: RAW={r['raw_count']} | CLEAN={r['clean_count']} | Inválidos={r['invalid_schema_count']}")
        if r.get('audit_path'):
            print(f"    Auditoría Log: {r['audit_entries_count']} eventos ({actions_str}) -> {r['audit_path']}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline de Ingesta RISA Data V1.0 (Procesamiento Completo)")
    parser.add_argument("--data-dir", type=str, default="01_RISA_DATA_V1_0", help="Ruta al dataset")
    parser.add_argument("--max-rows", type=int, default=0, help="Filas máximas a procesar (0 = procesar TODOS los datos)")
    parser.add_argument("--table", type=str, default="all", help="Filtro de tabla (vitals, wearables, lab, all)")
    args = parser.parse_args()

    run_risa_ingestion(
        dataset_dir=args.data_dir,
        max_rows_per_table=args.max_rows if args.max_rows > 0 else None,
        table_filter=args.table
    )
