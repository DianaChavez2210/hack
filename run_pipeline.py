"""
Punto de Entrada CLI para el Pipeline de Ingesta y Calidad de Datos (RISA Data V1.0).
Ejecuta la ingesta desde 01_RISA_DATA_V1_0/ hacia data/raw/ y data/clean/.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# Agregar directorio raíz al path de Python
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from ingestion.orchestrator import IngestionOrchestrator


def run_risa_ingestion(
    dataset_dir: str = "01_RISA_DATA_V1_0",
    max_rows_per_table: int = 1000,
    table_filter: str = "all"
):
    """
    Ejecuta el pipeline de ingesta para las tablas de RISA Data V1.0.
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

    # Definición de tablas objetivo por dominio
    tables_to_ingest = [
        ("03_monitoring/vital_signs.csv", "vital_signs", "HOSP_MONITOR"),
        ("03_monitoring/wearable_observations.csv", "wearables", "WEARABLE_CENTER"),
        ("03_monitoring/device_observations.csv", "device_observations", "DEVICE_GATEWAY"),
        ("02_clinical/laboratory_results.csv", "lab_results", "CENTRAL_LAB"),
        ("02_clinical/conditions.csv", "conditions", "EHR_SYSTEM"),
        ("02_clinical/medication_administrations.csv", "medications", "EHR_MED"),
    ]

    print("=" * 70)
    print("  HEALTHSIGNAL LATAM — SISTEMA DE INGESTA Y CALIDAD DE DATOS")
    print(f"  Directorio Fuente: {dataset_dir}")
    print(f"  Límite de filas por tabla: {max_rows_per_table if max_rows_per_table else 'Sin límite'}")
    print("=" * 70)

    results = []

    for rel_path, dataset_name, hospital_id in tables_to_ingest:
        if table_filter != "all" and table_filter not in dataset_name:
            continue

        file_path = base_path / rel_path
        if not file_path.exists():
            print(f"[WARN] Archivo no encontrado: {file_path}. Saltando...")
            continue

        print(f"\n[INFO] Procesando: {rel_path}...")
        try:
            res = orchestrator.process_and_save(
                source_type="RISA_CSV",
                hospital_id=hospital_id,
                source_config={
                    "file_path": str(file_path),
                    "max_rows": max_rows_per_table
                },
                dataset_name=dataset_name
            )
            results.append(res)
            print(f"  [OK] RAW guardado en: {res['raw_path']} ({res['raw_count']} registros)")
            print(f"  [OK] CLEAN guardado en: {res['clean_path']} ({res['clean_count']} registros limpios)")
            print(f"  [OK] AUDIT LOG guardado en: {res['audit_path']} ({res['audit_entries_count']} decisiones registradas)")
            if res["audit_actions"]:
                actions_str = ", ".join(f"{k}={v}" for k, v in res["audit_actions"].items())
                print(f"       Acciones de Calidad: {actions_str}")
        except Exception as e:
            print(f"  [ERROR] Fallo al procesar {rel_path}: {e}")

    print("\n" + "=" * 70)
    print("  RESUMEN DE INGESTA, CALIDAD Y AUDITORIA")
    print("=" * 70)
    for r in results:
        actions_str = ", ".join(f"{k}={v}" for k, v in r["audit_actions"].items()) if r["audit_actions"] else "Sin incidencias"
        print(f"  * {r['source_type']} [{r['hospital_id']}]: RAW={r['raw_count']} | CLEAN={r['clean_count']} | Inválidos={r['invalid_schema_count']}")
        print(f"    Auditoría: {r['audit_entries_count']} eventos ({actions_str}) -> {r['audit_path']}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline de Ingesta RISA Data V1.0")
    parser.add_argument("--data-dir", type=str, default="01_RISA_DATA_V1_0", help="Ruta al dataset")
    parser.add_argument("--max-rows", type=int, default=500, help="Filas máximas a procesar por tabla")
    parser.add_argument("--table", type=str, default="all", help="Filtro de tabla (vitals, wearables, lab, all)")
    args = parser.parse_args()

    run_risa_ingestion(
        dataset_dir=args.data_dir,
        max_rows_per_table=args.max_rows,
        table_filter=args.table
    )
