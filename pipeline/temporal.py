"""
Módulo de Procesamiento Temporal y Cálculo de Latencias Operacionales.
Diferencia entre el timeline fisiológico (event_datetime) y el timeline operacional (available_datetime).
"""

from typing import List, Optional
from datetime import datetime
from ingestion.models import CDMRecord


class TemporalProcessor:
    """
    Procesa y estandariza las marcas temporales de los registros CDM.
    Calcula la latencia operacional entre el fenómeno y su disponibilidad.
    """
    def __init__(self, default_date_format: Optional[str] = None):
        self.default_date_format = default_date_format

    def process(self, records: List[CDMRecord]) -> List[CDMRecord]:
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

        return records

    @staticmethod
    def _parse_iso_or_custom(dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str or str(dt_str).strip() in ("", "None", "null"):
            return None
        dt_clean = str(dt_str).strip()
        # Formatos comunes en RISA: '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d', ISO-8601
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
