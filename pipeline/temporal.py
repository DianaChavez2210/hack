"""
Módulo de Procesamiento Temporal y Cálculo de Latencias Operacionales.
Diferencia entre el timeline fisiológico (event_datetime) y el timeline operacional (available_datetime).
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from ingestion.models import CDMRecord, AuditEntry


class TemporalProcessor:
    """
    Procesa y estandariza marcas temporales en registros CDM.
    Valida reglas temporales:
    - TP-01: Fronteras de episodios de atención (encounters).
    - TP-02: Regla Anti-Temporal Leakage (T_available >= T_event).
    - TP-03: Cronología diagnóstica (recorded_datetime >= onset_date).
    """
    def __init__(
        self,
        default_date_format: Optional[str] = None,
        encounters_dict: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        self.default_date_format = default_date_format
        self.encounters_dict = encounters_dict or {}

    def set_encounters_dict(self, encounters_dict: Dict[str, Dict[str, Any]]):
        self.encounters_dict = encounters_dict

    def process(
        self, records: List[CDMRecord], audit_log: Optional[List[AuditEntry]] = None
    ) -> List[CDMRecord]:
        for rec in records:
            dt_event = self._parse_iso_or_custom(rec.event_datetime)
            dt_avail = self._parse_iso_or_custom(rec.available_datetime)

            # Si solo existe uno, propagar razonablemente
            if dt_event and not dt_avail:
                dt_avail = dt_event
                rec.available_datetime = rec.event_datetime
            elif dt_avail and not dt_event:
                dt_event = dt_avail
                rec.event_datetime = rec.available_datetime

            # Calcular latencia en segundos: T_available - T_event
            if dt_event and dt_avail:
                delta = (dt_avail - dt_event).total_seconds()
                rec.latency_seconds = delta

                # 1. Regla TP-02: Regla Anti-Temporal Leakage
                if delta < 0:
                    reason = f"Fuga temporal detectada: T_available ({rec.available_datetime}) anterior a T_event ({rec.event_datetime})"
                    rec.plausibility_status = "TEMPORAL_LEAKAGE"
                    rec.add_audit_entry(stage="TEMPORAL_PROCESS", action="FLAGGED", reason=reason)
                    if audit_log is not None:
                        audit_log.append(AuditEntry(
                            record_id=rec.record_id,
                            patient_id=rec.patient_id,
                            source_file=rec.source_file,
                            variable_code=rec.variable_code or "TEMPORAL",
                            stage="TEMPORAL_PROCESS",
                            action="FLAGGED",
                            reason=reason,
                            details={"rule": "TP-02", "latency_seconds": delta}
                        ))

            # 2. Regla TP-01: Fronteras del Encuentro Clínico
            if rec.encounter_id and dt_event and self.encounters_dict:
                enc_info = self.encounters_dict.get(rec.encounter_id)
                if enc_info:
                    start_dt = self._parse_iso_or_custom(enc_info.get("start_datetime"))
                    end_dt = self._parse_iso_or_custom(enc_info.get("end_datetime"))
                    if start_dt and dt_event < start_dt:
                        reason = f"Evento {rec.event_datetime} anterior al inicio del encuentro {start_dt}"
                        rec.plausibility_status = "OUT_OF_ENCOUNTER_BOUNDS"
                        rec.add_audit_entry(stage="TEMPORAL_PROCESS", action="FLAGGED", reason=reason)
                        if audit_log is not None:
                            audit_log.append(AuditEntry(
                                record_id=rec.record_id,
                                patient_id=rec.patient_id,
                                source_file=rec.source_file,
                                variable_code=rec.variable_code or "TEMPORAL",
                                stage="TEMPORAL_PROCESS",
                                action="FLAGGED",
                                reason=reason,
                                details={"rule": "TP-01", "start_datetime": str(start_dt)}
                            ))
                    elif end_dt and dt_event > end_dt:
                        reason = f"Evento {rec.event_datetime} posterior al fin del encuentro {end_dt}"
                        rec.plausibility_status = "OUT_OF_ENCOUNTER_BOUNDS"
                        rec.add_audit_entry(stage="TEMPORAL_PROCESS", action="FLAGGED", reason=reason)
                        if audit_log is not None:
                            audit_log.append(AuditEntry(
                                record_id=rec.record_id,
                                patient_id=rec.patient_id,
                                source_file=rec.source_file,
                                variable_code=rec.variable_code or "TEMPORAL",
                                stage="TEMPORAL_PROCESS",
                                action="FLAGGED",
                                reason=reason,
                                details={"rule": "TP-01", "end_datetime": str(end_dt)}
                            ))

            # 3. Regla TP-03: Cronología de Diagnósticos
            if rec.header_fields and "onset_date" in rec.header_fields and "recorded_datetime" in rec.header_fields:
                dt_onset = self._parse_iso_or_custom(rec.header_fields.get("onset_date"))
                dt_recorded = self._parse_iso_or_custom(rec.header_fields.get("recorded_datetime"))
                if dt_onset and dt_recorded and dt_recorded < dt_onset:
                    reason = f"Incoherencia cronológica: fecha de registro ({dt_recorded}) anterior a fecha de inicio ({dt_onset})"
                    rec.plausibility_status = "INVALID_CONDITION_CHRONOLOGY"
                    rec.add_audit_entry(stage="TEMPORAL_PROCESS", action="FLAGGED", reason=reason)
                    if audit_log is not None:
                        audit_log.append(AuditEntry(
                            record_id=rec.record_id,
                            patient_id=rec.patient_id,
                            source_file=rec.source_file,
                            variable_code=rec.variable_code or "CONDITION",
                            stage="TEMPORAL_PROCESS",
                            action="FLAGGED",
                            reason=reason,
                            details={"rule": "TP-03", "onset_date": str(dt_onset), "recorded_datetime": str(dt_recorded)}
                        ))

        return records

    @staticmethod
    def _parse_iso_or_custom(dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str or str(dt_str).strip() in ("", "None", "null"):
            return None
        dt_clean = str(dt_str).strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S"
        ):
            try:
                return datetime.strptime(dt_clean, fmt)
            except ValueError:
                continue
        return None
