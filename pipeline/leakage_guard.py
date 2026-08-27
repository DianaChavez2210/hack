"""
Módulo de Prevención de Fuga Temporal (Temporal Leakage Guard).
Garantiza la regla fundamental de HealthSignal LATAM:
Para cualquier decisión en el instante T, solo se puede utilizar evidencia con T_available <= T.
"""

from typing import List, Optional, Union
from datetime import datetime
import pandas as pd
from ingestion.models import CDMRecord, AuditEntry
from pipeline.temporal import TemporalProcessor


class LeakageGuard:
    """
    Guardián anti-leakage para proteger el pipeline predictivo, de features y de evidencias.
    Soporta filtrado sobre listas de CDMRecord y DataFrames de Pandas.
    """
    def __init__(self):
        self._parser = TemporalProcessor._parse_iso_or_custom

    def filter_available_records(
        self,
        records_df: pd.DataFrame,
        decision_datetime: Union[str, datetime]
    ) -> pd.DataFrame:
        """
        Filtra un DataFrame de Pandas asegurando que disponible_datetime <= decision_datetime.
        Regla inmutable: Bloquea todo registro donde available_datetime > decision_datetime.
        """
        if records_df.empty:
            return records_df

        dt_decision = decision_datetime if isinstance(decision_datetime, datetime) else self._parser(str(decision_datetime))
        if not dt_decision:
            raise ValueError(f"Formato de decision_datetime inválido: {decision_datetime}")

        col_avail = "available_datetime" if "available_datetime" in records_df.columns else "event_datetime"
        if col_avail not in records_df.columns:
            return records_df

        # Usar la serie directamente si ya es de tipo datetime64
        if pd.api.types.is_datetime64_any_dtype(records_df[col_avail]):
            parsed_series = records_df[col_avail]
        else:
            parsed_series = pd.to_datetime(records_df[col_avail], errors="coerce")

        mask = parsed_series <= dt_decision
        return records_df[mask].copy()

    def filter_by_decision_time(
        self,
        records: List[CDMRecord],
        decision_datetime: Union[str, datetime],
        audit_log: Optional[List[AuditEntry]] = None
    ) -> List[CDMRecord]:
        """
        Filtra y retorna únicamente los registros que estaban disponibles en o antes de decision_datetime.
        Registra en audit_log los datos bloqueados por fuga temporal.
        """
        dt_decision = decision_datetime if isinstance(decision_datetime, datetime) else self._parser(str(decision_datetime))
        if not dt_decision:
            raise ValueError(f"Formato de decision_datetime inválido: {decision_datetime}")

        allowed_records: List[CDMRecord] = []

        for rec in records:
            dt_available = self._parser(rec.available_datetime or rec.event_datetime)
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
                        details={"decision_datetime": str(decision_datetime), "available_datetime": rec.available_datetime}
                    ))

        return allowed_records

    def check_leakage(
        self, record: CDMRecord, decision_datetime: Union[str, datetime]
    ) -> bool:
        """
        Retorna True si el registro es seguro de usar (T_available <= decision_datetime),
        o False si representaría fuga temporal.
        """
        dt_decision = decision_datetime if isinstance(decision_datetime, datetime) else self._parser(str(decision_datetime))
        dt_available = self._parser(record.available_datetime or record.event_datetime)

        if not dt_decision or not dt_available:
            return False

        return dt_available <= dt_decision
