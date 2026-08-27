"""
Punto de Entrada CLI Oficial para el Pipeline de Ingesta, Calidad, Feature Engineering,
Modelado Predictivo, Priorización y Evidencias Trazables (RISA Data V1.0).

Fases 1, 2 y 3 — HealthSignal LATAM.
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
from features.feature_builder import FeatureBuilder
from model.train import train_risk_model
from model.predict import RiskPredictor
from model.prioritization import classify_priority
from generate_evidence import generate_signals_and_evidence


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
    table_filter: str = "all",
    chunk_size: int = 50000,
    parallel: bool = True,
    workers: Optional[int] = None
):
    """
    Fase 1: Ejecuta la ingesta por lotes con 13 reglas de calidad para RISA Data V1.0.
    """
    base_path = Path(dataset_dir)
    if not base_path.exists():
        print(f"[ERROR] Directorio del dataset no encontrado: {dataset_dir}")
        return

    units_cat = str(base_path / "05_metadata" / "units_catalog.csv")
    var_cat = str(base_path / "05_metadata" / "variable_catalog.csv")

    orchestrator = IngestionOrchestrator(
        units_catalog_path=units_cat if os.path.exists(units_cat) else None,
        variable_catalog_path=var_cat if os.path.exists(var_cat) else None
    )

    master_ctx = load_master_context(base_path)
    orchestrator.set_master_context(**master_ctx)

    tables_to_ingest = [
        ("01_master/patients.csv", "patients", "EHR_SYSTEM"),
        ("01_master/encounters.csv", "encounters", "EHR_SYSTEM"),
        ("01_master/devices.csv", "devices", "DEVICE_GATEWAY"),
        ("01_master/healthcare_facilities.csv", "facilities", "EHR_SYSTEM"),
        ("02_clinical/conditions.csv", "conditions", "EHR_SYSTEM"),
        ("02_clinical/laboratory_results.csv", "lab_results", "CENTRAL_LAB"),
        ("02_clinical/medication_administrations.csv", "medications", "EHR_MED"),
        ("03_monitoring/vital_signs.csv", "vital_signs", "HOSP_MONITOR"),
        ("03_monitoring/wearable_observations.csv", "wearables", "WEARABLE_CENTER"),
        ("03_monitoring/device_observations.csv", "device_observations", "DEVICE_GATEWAY"),
        ("04_context/patient_context.csv", "patient_context", "WEARABLE_GATEWAY"),
        ("04_context/connectivity_events.csv", "connectivity_events", "DEVICE_GATEWAY"),
    ]

    effective_max_rows = None if not max_rows_per_table or max_rows_per_table <= 0 else max_rows_per_table
    num_workers_str = f"{workers or os.cpu_count() or 4} procesadores" if parallel else "Modo Secuencial"

    print("=" * 75, flush=True)
    print("  HEALTHSIGNAL LATAM — FASE 1: INGESTA MULTINUCLEO Y CALIDAD DE DATOS", flush=True)
    print(f"  Directorio Fuente: {dataset_dir}", flush=True)
    print(f"  Modo de Ejecución: {num_workers_str}", flush=True)
    print(f"  Tamaño de Lote:     {chunk_size} registros por batch", flush=True)
    print("=" * 75, flush=True)

    results = []

    for rel_path, dataset_name, hospital_id in tables_to_ingest:
        if table_filter != "all" and table_filter not in dataset_name and table_filter not in rel_path:
            continue

        file_path = base_path / rel_path
        if not file_path.exists():
            print(f"[WARN] Archivo no encontrado: {file_path}. Saltando...", flush=True)
            continue

        print(f"\n[INFO] Procesando por lotes ({dataset_name})...", flush=True)
        try:
            if parallel:
                res = orchestrator.process_and_save_parallel(
                    source_type="RISA_CSV",
                    hospital_id=hospital_id,
                    source_config={"file_path": str(file_path), "max_rows": effective_max_rows},
                    dataset_name=dataset_name,
                    chunk_size=chunk_size,
                    max_workers=workers
                )
            else:
                res = orchestrator.process_and_save_stream(
                    source_type="RISA_CSV",
                    hospital_id=hospital_id,
                    source_config={"file_path": str(file_path), "max_rows": effective_max_rows},
                    dataset_name=dataset_name,
                    chunk_size=chunk_size
                )
            results.append(res)
            print(f"  [OK] RAW guardado en:   {res['raw_path']} ({res['raw_count']} registros)", flush=True)
            print(f"  [OK] CLEAN CSV guardado: {res['clean_csv_path']} ({res['clean_count']} registros limpios)", flush=True)
        except Exception as e:
            print(f"  [ERROR] Fallo al procesar {rel_path}: {e}", flush=True)

    print("\n" + "=" * 75, flush=True)
    print("  RESUMEN FINAL DE INGESTA POR LOTES Y CALIDAD DE DATOS (FASE 1 OK)", flush=True)
    print("=" * 75, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline End-to-End HealthSignal LATAM (Fases 1, 2 y 3)")
    parser.add_argument("--data-dir", type=str, default="01_RISA_DATA_V1_0", help="Ruta al dataset RISA Data V1.0")
    parser.add_argument("--max-rows", type=int, default=0, help="Filas máximas por tabla (0 = procesar TODO)")
    parser.add_argument("--table", type=str, default="all", help="Filtro de tabla")
    parser.add_argument("--chunk-size", type=int, default=50000, help="Tamaño de lote en registros")
    parser.add_argument("--workers", type=int, default=None, help="Número de procesadores paralelos")
    parser.add_argument("--no-parallel", action="store_true", help="Desactivar paralelizador")
    parser.add_argument("--extract-features", action="store_true", help="Fase 2: Generar matriz de características")
    parser.add_argument("--train-model", action="store_true", help="Fase 3: Entrenar y calibrar modelo predictivo")
    parser.add_argument("--generate-results", action="store_true", help="Fase 3: Generar y validar signals.csv y evidence.csv")
    parser.add_argument("--full", action="store_true", help="Ejecutar el pipeline completo (Fases 1, 2 y 3)")
    args = parser.parse_args()

    # Si se pasa --full o no se pasa ningún flag de fase analítica, ejecutar Fase 1 Ingesta por defecto
    run_ingestion = not (args.extract_features or args.train_model or args.generate_results) or args.full

    if run_ingestion:
        run_risa_ingestion(
            dataset_dir=args.data_dir,
            max_rows_per_table=args.max_rows if args.max_rows > 0 else None,
            table_filter=args.table,
            chunk_size=args.chunk_size,
            parallel=not args.no_parallel,
            workers=args.workers
        )

    if args.extract_features or args.full:
        print("\n" + "=" * 75, flush=True)
        print("  HEALTHSIGNAL LATAM — FASE 2: FEATURE ENGINEERING (VENTANAS MOVILES)", flush=True)
        print("=" * 75, flush=True)
        builder = FeatureBuilder()
        builder.build_feature_matrix(clean_dir="data/clean/csv", output_parquet="data/features/features_matrix.parquet")

    if args.train_model or args.full:
        print("\n" + "=" * 75, flush=True)
        print("  HEALTHSIGNAL LATAM — FASE 3: MODELADO PREDICTIVO Y CALIBRACION", flush=True)
        print("=" * 75, flush=True)
        train_risk_model()

    if args.generate_results or args.full:
        print("\n" + "=" * 75, flush=True)
        print("  HEALTHSIGNAL LATAM — FASE 3: SEÑALES, EVIDENCIAS Y VALIDACION", flush=True)
        print("=" * 75, flush=True)
        generate_signals_and_evidence(clean_dir="data/clean/csv", output_dir="results")
