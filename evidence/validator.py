"""
Módulo de Validación de Archivos de Entrega (SubmissionValidator).
Verifica reglas estructurales y de lógica clínica/temporal para evitar fuga temporal y asegurar la integridad de la entrega.
"""

import os
import csv
from typing import Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
from pipeline.temporal import TemporalProcessor


class SubmissionValidator:
    """
    Validador oficial del formato de entrega (signals.csv y evidence.csv).
    Garantiza el cumplimiento estricto de las especificaciones técnicas de HealthSignal LATAM.
    """
    def __init__(self):
        self._parser = TemporalProcessor._parse_iso_or_custom

        self.required_signals_fields = {
            "signal_id", "patient_id", "decision_datetime", "risk_score",
            "priority_level", "evidence_start", "evidence_end",
            "explanation", "model_version"
        }

        self.required_evidence_fields = {
            "signal_id", "source_file", "record_id", "event_datetime",
            "available_datetime", "evidence_role"
        }

    def validate_files(
        self,
        signals_csv_path: str,
        evidence_csv_path: str
    ) -> Tuple[bool, List[str]]:
        """
        Valida estructural y lógicamente ambos archivos.
        Retorna (es_valido, lista_de_errores).
        """
        errors: List[str] = []

        sig_path = Path(signals_csv_path)
        ev_path = Path(evidence_csv_path)

        if not sig_path.exists():
            return False, [f"Archivo de señales no encontrado: {signals_csv_path}"]
        if not ev_path.exists():
            return False, [f"Archivo de evidencia no encontrado: {evidence_csv_path}"]

        # 1. Cargar y Validar Estructura de signals.csv
        signals_data: Dict[str, Dict[str, Any]] = {}
        try:
            with open(sig_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = set(reader.fieldnames or [])
                
                # Verificar campos obligatorios
                missing_fields = self.required_signals_fields - headers
                if missing_fields:
                    errors.append(f"signals.csv no contiene los campos obligatorios: {missing_fields}")
                
                # Validar registros uno a uno
                for row_idx, row in enumerate(reader, start=2):
                    sig_id = row.get("signal_id")
                    if not sig_id:
                        errors.append(f"Fila {row_idx} en signals.csv: 'signal_id' está vacío o nulo.")
                        continue
                    
                    if sig_id in signals_data:
                        errors.append(f"signals.csv contiene signal_id duplicado: '{sig_id}' en fila {row_idx}.")
                    
                    # Validar valores
                    priority = row.get("priority_level")
                    if priority not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
                        errors.append(f"Fila {row_idx} (signal_id='{sig_id}'): priority_level '{priority}' no es válido.")

                    try:
                        risk = float(row.get("risk_score", -1))
                        if not (0.0 <= risk <= 1.0):
                            errors.append(f"Fila {row_idx} (signal_id='{sig_id}'): risk_score '{risk}' fuera de rango [0, 1].")
                    except ValueError:
                        errors.append(f"Fila {row_idx} (signal_id='{sig_id}'): risk_score no es un valor numérico válido.")

                    # Validar consistencia de fechas
                    t_dec = self._parser(row.get("decision_datetime", ""))
                    t_start = self._parser(row.get("evidence_start", ""))
                    t_end = self._parser(row.get("evidence_end", ""))

                    if not t_dec:
                        errors.append(f"Fila {row_idx} (signal_id='{sig_id}'): decision_datetime inválida o vacía.")
                    if not t_start:
                        errors.append(f"Fila {row_idx} (signal_id='{sig_id}'): evidence_start inválida o vacía.")
                    if not t_end:
                        errors.append(f"Fila {row_idx} (signal_id='{sig_id}'): evidence_end inválida o vacía.")

                    if t_start and t_end and t_start > t_end:
                        errors.append(f"Fila {row_idx} (signal_id='{sig_id}'): evidence_start es posterior a evidence_end.")
                    if t_end and t_dec and t_end > t_dec:
                        errors.append(f"Fila {row_idx} (signal_id='{sig_id}'): evidence_end es posterior a decision_datetime.")

                    explanation = row.get("explanation", "")
                    if not explanation or explanation.strip() == "":
                        errors.append(f"Fila {row_idx} (signal_id='{sig_id}'): explanation está vacía.")

                    signals_data[sig_id] = {
                        "patient_id": row.get("patient_id"),
                        "decision_datetime_str": row.get("decision_datetime"),
                        "decision_datetime": t_dec,
                        "evidence_start": t_start,
                        "evidence_end": t_end
                    }
        except Exception as e:
            errors.append(f"Error procesando signals.csv: {e}")

        # 2. Cargar y Validar Estructura e Integridad Lógica en evidence.csv
        try:
            with open(ev_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = set(reader.fieldnames or [])

                # Verificar campos obligatorios
                missing_fields = self.required_evidence_fields - headers
                if missing_fields:
                    errors.append(f"evidence.csv no contiene los campos obligatorios: {missing_fields}")

                for row_idx, row in enumerate(reader, start=2):
                    sig_id = row.get("signal_id")
                    rec_id = row.get("record_id")
                    
                    if not sig_id:
                        errors.append(f"Fila {row_idx} en evidence.csv: 'signal_id' está vacío.")
                        continue
                    
                    # Integridad Referencial
                    if sig_id not in signals_data:
                        errors.append(f"Fila {row_idx} en evidence.csv: signal_id '{sig_id}' no existe en signals.csv.")
                        continue

                    role = row.get("evidence_role")
                    if role not in ("PRIMARY", "SUPPORTING", "CONTEXT", "QUALITY"):
                        errors.append(f"Fila {row_idx} (signal_id='{sig_id}'): evidence_role '{role}' inválido.")

                    t_event = self._parser(row.get("event_datetime", ""))
                    t_avail = self._parser(row.get("available_datetime", ""))

                    if not t_event:
                        errors.append(f"Fila {row_idx} (record_id='{rec_id}'): event_datetime inválida o vacía.")
                    if not t_avail:
                        errors.append(f"Fila {row_idx} (record_id='{rec_id}'): available_datetime inválida o vacía.")

                    if t_event and t_avail and t_event > t_avail:
                        errors.append(f"Fila {row_idx} (record_id='{rec_id}'): event_datetime es posterior a available_datetime (inconsistencia operacional).")

                    # Validar Fuga Temporal (Leakage Guard)
                    sig_info = signals_data[sig_id]
                    t_dec = sig_info["decision_datetime"]

                    if t_avail and t_dec and t_avail > t_dec:
                        errors.append(
                            f"Fila {row_idx} en evidence.csv (record_id='{rec_id}'): available_datetime ({row.get('available_datetime')}) "
                            f"es posterior a decision_datetime de la señal ({sig_info['decision_datetime_str']}). ¡Fuga temporal detectada!"
                        )
        except Exception as e:
            errors.append(f"Error procesando evidence.csv: {e}")

        return len(errors) == 0, errors
