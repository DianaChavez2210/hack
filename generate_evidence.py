"""
Script CLI Ultra-Rápido para la Generación Completa de Señales y Evidencias de Riesgo Clínico (HealthSignal LATAM).
Genera los entregables oficiales results/signals.csv y results/evidence.csv a partir de los datos limpios.

Uso en terminal (un solo comando):
    python generate_evidence.py
"""

import os
import sys
import csv
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict

# Agregar directorio raíz al sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from ingestion.models import CDMRecord
from evidence.evidence_builder import EvidenceBuilder
from evidence.explanation_builder import ExplanationBuilder
from evidence.validator import SubmissionValidator
from pipeline.temporal import TemporalProcessor


def parse_float(val: Any) -> Optional[float]:
    if val is None or str(val).strip() in ("", "None", "null", "NaN", "nan"):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def generate_signals_and_evidence(
    clean_dir: str = "data/clean/csv",
    output_dir: str = "results",
    dataset_dir: str = "01_RISA_DATA_V1_0",
    max_patients: int = 0
):
    clean_path = Path(clean_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    signals_csv_path = out_path / "signals.csv"
    evidence_csv_path = out_path / "evidence.csv"

    # Reiniciar archivos de salida
    if signals_csv_path.exists():
        signals_csv_path.unlink()
    if evidence_csv_path.exists():
        evidence_csv_path.unlink()

    print("=" * 75, flush=True)
    print("  HEALTHSIGNAL LATAM — GENERADOR DE SEÑALES Y EVIDENCIA CLINICA", flush=True)
    print(f"  Directorio Datos Limpios: {clean_dir}", flush=True)
    print(f"  Directorio de Salida:      {output_dir}", flush=True)
    print("=" * 75, flush=True)

    ev_builder = EvidenceBuilder(output_path=str(evidence_csv_path))
    exp_builder = ExplanationBuilder()
    parser = TemporalProcessor._parse_iso_or_custom

    # 1. Cargar Mapa de Pacientes
    patients_map = {}
    pat_file = clean_path / "patients.csv"
    if not pat_file.exists():
        pat_file = Path(dataset_dir) / "01_master/patients.csv"
    if pat_file.exists():
        with open(pat_file, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                pid = row.get("patient_id")
                if pid:
                    patients_map[pid] = row

    # 2. Cargar Registros en Estructura Ligera Dict (Ultra-Rápido)
    patient_records_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    files_to_load = [
        ("vital_signs.csv", "vital_signs.csv"),
        ("lab_results.csv", "laboratory_results.csv"),
        ("wearables.csv", "wearable_observations.csv"),
        ("medications.csv", "medication_administrations.csv"),
        ("conditions.csv", "conditions.csv"),
    ]

    total_loaded = 0
    for filename, src_name in files_to_load:
        filepath = clean_path / filename
        if not filepath.exists():
            continue
        
        print(f"[INFO] Cargando registros desde: {filename}...", flush=True)
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("patient_id")
                if not pid:
                    continue

                if max_patients > 0 and len(patient_records_map) >= max_patients and pid not in patient_records_map:
                    continue

                row["source_file"] = row.get("source_file") or src_name
                patient_records_map[pid].append(row)
                total_loaded += 1

    print(f"[OK] {total_loaded} registros cargados para {len(patient_records_map)} pacientes.", flush=True)

    # Rangos fisiológicos de referencia
    ranges = {
        "HR": (60.0, 100.0),
        "RR": (12.0, 20.0),
        "SpO2": (95.0, 100.0),
        "TEMP": (36.0, 37.5),
        "SBP": (90.0, 120.0),
        "DBP": (60.0, 80.0),
        "WEARABLE_HR": (60.0, 100.0),
        "STEPS": (0.0, 10000.0)
    }

    signals_list = []
    total_evidences_count = 0

    print("\n[INFO] Generando señales y evidencias por paciente...", flush=True)

    for pid, raw_rows in patient_records_map.items():
        if not raw_rows:
            continue

        # Convertir a objetos CDMRecord ligeros para los 60 eventos más recientes
        valid_items = []

        for row in raw_rows[-60:]:
            val_num = parse_float(row.get("converted_value")) or parse_float(row.get("value_numeric")) or parse_float(row.get("value")) or parse_float(row.get("result_value"))
            ts = row.get("event_datetime") or row.get("timestamp") or row.get("sample_datetime") or row.get("onset_date")
            avail_ts = row.get("available_datetime") or row.get("sync_datetime") or row.get("result_datetime") or ts

            rec = CDMRecord(
                record_id=row.get("record_id") or row.get("observation_id") or row.get("lab_result_id") or f"REC-{total_loaded}",
                patient_id=pid,
                encounter_id=row.get("encounter_id"),
                facility_id=row.get("facility_id"),
                device_id=row.get("device_id"),
                source_file=row.get("source_file"),
                source_system=row.get("source_system", "CDM"),
                variable_code=row.get("variable_code") or row.get("test_code") or "VITAL",
                value_numeric=val_num,
                converted_value=val_num,
                value_text=row.get("value_text") or row.get("test_name"),
                original_unit=row.get("original_unit") or row.get("unit"),
                canonical_unit=row.get("canonical_unit") or row.get("unit"),
                event_datetime=ts,
                available_datetime=avail_ts,
                plausibility_status=row.get("plausibility_status", "VALID"),
                quality_flag=row.get("quality_flag", "OK"),
                signal_quality=parse_float(row.get("signal_quality")),
                is_observed=str(row.get("is_observed", "True")).lower() in ("true", "1")
            )
            avail_dt = parser(rec.available_datetime) or parser(rec.event_datetime)
            if avail_dt:
                valid_items.append((avail_dt, rec))

        if not valid_items:
            continue

        # Ordenar estrictamente por fecha disponible T_available
        valid_items.sort(key=lambda x: x[0])
        max_avail_dt, latest_rec = valid_items[-1]
        decision_datetime_str = max_avail_dt.strftime("%Y-%m-%d %H:%M:%S")

        cdm_records = [rec for dt, rec in valid_items]

        # Evaluar desviaciones biológicas primarias
        primary_deviations = []
        
        for dt, r in valid_items:
            val = r.converted_value if r.converted_value is not None else r.value_numeric
            if val is not None and r.variable_code in ranges:
                min_v, max_v = ranges[r.variable_code]
                if val < min_v or val > max_v:
                    dev = max(min_v - val, val - max_v)
                    primary_deviations.append((r.variable_code, val, dev))

        # Determinar risk score y nivel de prioridad
        if primary_deviations:
            max_dev = max(d[2] for d in primary_deviations)
            risk_score = round(min(0.99, 0.50 + (len(primary_deviations) * 0.05) + (max_dev * 0.01)), 3)
        else:
            risk_score = 0.15

        if risk_score >= 0.85:
            priority_level = "CRITICAL"
        elif risk_score >= 0.65:
            priority_level = "HIGH"
        elif risk_score >= 0.40:
            priority_level = "MEDIUM"
        else:
            priority_level = "LOW"

        signal_id = f"SIG-{len(signals_list)+1:06d}"
        start_dt = max_avail_dt - timedelta(hours=24)
        evidence_start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")

        # 1. Construir y guardar evidencias
        ev_entries = ev_builder.build_evidence(
            signal_id=signal_id,
            patient_id=pid,
            decision_datetime=decision_datetime_str,
            records=cdm_records,
            vitals_ranges=ranges
        )
        
        if ev_entries:
            ev_builder.save_evidence(ev_entries, append=True)
            total_evidences_count += len(ev_entries)

        # 2. Explicación narrativa basada en las evidencias reales
        explanation_text = exp_builder.generate_explanation(
            patient_id=pid,
            priority_level=priority_level,
            decision_datetime=decision_datetime_str,
            evidence_entries=ev_entries,
            cdm_records=cdm_records
        )

        signals_list.append({
            "signal_id": signal_id,
            "patient_id": pid,
            "decision_datetime": decision_datetime_str,
            "risk_score": risk_score,
            "priority_level": priority_level,
            "evidence_start": evidence_start_str,
            "evidence_end": decision_datetime_str,
            "explanation": explanation_text,
            "model_version": "v1.0.0"
        })

    # Guardar signals.csv
    signals_fields = [
        "signal_id", "patient_id", "decision_datetime", "risk_score",
        "priority_level", "evidence_start", "evidence_end",
        "explanation", "model_version"
    ]
    with open(signals_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=signals_fields)
        writer.writeheader()
        for sig in signals_list:
            writer.writerow(sig)

    print(f"\n[OK] Generación finalizada exitosamente:", flush=True)
    print(f"  - signals.csv:  {signals_csv_path} ({len(signals_list)} señales de riesgo)", flush=True)
    print(f"  - evidence.csv: {evidence_csv_path} ({total_evidences_count} registros de evidencia trazables)", flush=True)

    # 4. Validar automáticamente los entregables con SubmissionValidator
    print("\n" + "=" * 75, flush=True)
    print("  EJECUTANDO VALIDACION AUTOMATICA DE ENTREGABLES (SubmissionValidator)", flush=True)
    print("=" * 75, flush=True)
    val = SubmissionValidator()
    is_valid, errors = val.validate_files(str(signals_csv_path), str(evidence_csv_path))

    if is_valid:
        print("[SUCCESS] ¡Validación Exitosa! Los archivos cumplen 100% las especificaciones sin fuga temporal.", flush=True)
    else:
        print(f"[FAILED] Se encontraron {len(errors)} errores en la entrega:", flush=True)
        for err in errors[:10]:
            print(f"  * {err}", flush=True)
        if len(errors) > 10:
            print(f"  ... y {len(errors) - 10} errores adicionales.", flush=True)
    print("=" * 75, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generador de Señales y Evidencias Clínicas (HealthSignal LATAM)")
    parser.add_argument("--clean-dir", type=str, default="data/clean/csv", help="Ruta a datos limpios (CSV)")
    parser.add_argument("--output-dir", type=str, default="results", help="Ruta de destino para signals.csv y evidence.csv")
    parser.add_argument("--max-patients", type=int, default=0, help="Límite de pacientes a procesar (0 = procesar TODOS)")
    args = parser.parse_args()

    generate_signals_and_evidence(
        clean_dir=args.clean_dir,
        output_dir=args.output_dir,
        max_patients=args.max_patients
    )
