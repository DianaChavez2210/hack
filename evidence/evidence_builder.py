"""
Módulo de Ingesta, Filtrado y Construcción de Evidencias (EvidenceBuilder).
Garantiza el cumplimiento de reglas temporales y la categorización estructurada de observaciones.
"""

import os
import csv
from typing import List, Dict, Any, Optional
from pathlib import Path
from ingestion.models import CDMRecord
from pipeline.leakage_guard import LeakageGuard


class EvidenceBuilder:
    """
    Clase para construir, evaluar y persistir las evidencias clínicas asociadas a señales de riesgo.
    """
    def __init__(self, output_path: str = "results/evidence.csv"):
        self.output_path = output_path
        self.leakage_guard = LeakageGuard()

    def build_evidence(
        self,
        signal_id: str,
        patient_id: str,
        decision_datetime: str,
        records: List[CDMRecord],
        vitals_ranges: Optional[Dict[str, tuple]] = None
    ) -> List[Dict[str, Any]]:
        """
        Filtra los registros disponibles hasta decision_datetime (sin temporal leakage)
        y clasifica las evidencias en roles: PRIMARY, SUPPORTING, CONTEXT, QUALITY.
        """
        # Filtrar registros usando LeakageGuard
        valid_records = self.leakage_guard.filter_by_decision_time(records, decision_datetime)
        
        evidence_entries: List[Dict[str, Any]] = []

        # Rangos de normalidad por defecto de RISA V1.0
        ranges = vitals_ranges or {
            "HR": (60.0, 100.0),
            "RR": (12.0, 20.0),
            "SpO2": (95.0, 100.0),
            "TEMP": (36.0, 37.5),
            "SBP": (90.0, 120.0),
            "DBP": (60.0, 80.0),
            "WEARABLE_HR": (60.0, 100.0),
            "STEPS": (0.0, 10000.0)
        }

        for rec in valid_records:
            # Si el registro no corresponde al paciente, saltarlo
            if rec.patient_id != patient_id:
                continue

            role = "SUPPORTING"
            contribution = 0.0

            # 1. Determinar roles según el archivo fuente y el tipo de dato
            if rec.source_file in ("patients.csv", "encounters.csv", "patient_context.csv", "01_master/patients.csv", "01_master/encounters.csv", "04_context/patient_context.csv"):
                role = "CONTEXT"
                contribution = 0.05
            elif rec.source_file in ("connectivity_events.csv", "04_context/connectivity_events.csv") or rec.plausibility_status in ("NETWORK_INTERRUPTED", "UNRELIABLE_DEVICE") or (rec.signal_quality is not None and rec.signal_quality < 0.85):
                role = "QUALITY"
                contribution = 0.1
            else:
                # Mediciones clínicas (Vitals, Lab, Wearables, etc.)
                val = rec.converted_value if rec.converted_value is not None else rec.value_numeric
                if val is not None and rec.variable_code in ranges:
                    min_val, max_val = ranges[rec.variable_code]
                    if val < min_val or val > max_val:
                        role = "PRIMARY"
                        # Contribución basada en la desviación lineal respecto a los límites de rango normal
                        deviation = max(min_val - val, val - max_val)
                        range_size = max_val - min_val if max_val > min_val else 1.0
                        contribution = round(min(1.0, deviation / range_size), 4)
                    else:
                        role = "SUPPORTING"
                        contribution = 0.1
                elif rec.plausibility_status == "OUT_OF_RANGE":
                    role = "PRIMARY"
                    contribution = 0.8
                elif not rec.is_observed:
                    role = "QUALITY"
                    contribution = 0.2

            entry = {
                "signal_id": signal_id,
                "source_file": rec.source_file,
                "record_id": rec.record_id,
                "variable_code": rec.variable_code or "",
                "event_datetime": rec.event_datetime,
                "available_datetime": rec.available_datetime,
                "evidence_role": role,
                "contribution": contribution
            }
            evidence_entries.append(entry)

        return evidence_entries

    def save_evidence(self, entries: List[Dict[str, Any]], append: bool = True):
        """
        Persiste los registros de evidencia en results/evidence.csv.
        """
        if not entries:
            return

        out_path = Path(self.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = out_path.exists() and out_path.stat().st_size > 0

        fields = [
            "signal_id",
            "source_file",
            "record_id",
            "variable_code",
            "event_datetime",
            "available_datetime",
            "evidence_role",
            "contribution"
        ]

        mode = "a" if append else "w"
        with open(out_path, mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            if not file_exists or not append:
                writer.writeheader()
            for entry in entries:
                writer.writerow(entry)
