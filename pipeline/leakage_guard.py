"""
Módulo de Prevención de Fuga Temporal (Temporal Leakage Guard).
Garantiza la regla fundamental de HealthSignal LATAM:
Para cualquier decisión en el instante T, solo se puede utilizar evidencia con T_available <= T.
"""

from typing import List, Optional
from datetime import datetime
from ingestion.models import CDMRecord, AuditEntry
from pipeline.temporal import TemporalProcessor


class LeakageGuard:
    """
    Guardián anti-leakage para proteger el pipeline predictivo y de features.
    """
    def __init__(self):
        self._parser = TemporalProcessor._parse_iso_or_custom

    def filter_by_decision_time(
        self,
        records: List[CDMRecord],
        decision_datetime: str,
        audit_log: Optional[List[AuditEntry]] = None
    ) -> List[CDMRecord]:
        """
        Filtra y retorna únicamente los registros que estaban disponibles en o antes de decision_datetime.
        Registra en audit_log los datos bloqueados por fuga temporal.
        """
        dt_decision = self._parser(decision_datetime)
        if not dt_decision:
            raise ValueError(f"Formato de decision_datetime inválido: {decision_datetime}")

        allowed_records: List[CDMRecord] = []

        for rec in records:
            dt_available = self._parser(rec.available_datetime)
            if dt_available and dt_available <= dt_decision:
                allowed_records.append(rec)
            else:
                reason = f"Fuga temporal prevenida: disponible en '{rec.available_datetime}' posterior al momento de decisión '{decision_datetime}'"
                rec.add_audit_entry(stage="LEAKAGE_GUARD", action="LEAKAGE_BLOCKED", reason=reason)
                if audit_log is not None:
                    audit_log.append(AuditEntry(
                        record_id=rec.record_id,
                        patient_id=rec.patient_id,
                        source_file=rec.source_file,
                        variable_code=rec.variable_code,
                        stage="LEAKAGE_GUARD",
                        action="LEAKAGE_BLOCKED",
                        reason=reason,
                        details={"decision_datetime": decision_datetime, "available_datetime": rec.available_datetime}
                    ))

        return allowed_records

    def check_leakage(
        self, record: CDMRecord, decision_datetime: str
    ) -> bool:
        """
        Retorna True si el registro es seguro de usar (T_available <= decision_datetime),
        o False si representaría fuga temporal.
        """
        dt_decision = self._parser(decision_datetime)
        dt_available = self._parser(record.available_datetime)

        if not dt_decision or not dt_available:
            return False

        return dt_available <= dt_decision
