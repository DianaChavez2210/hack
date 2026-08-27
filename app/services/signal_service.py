"""
Servicio de Consulta de Señales de Riesgo Clínico (Signal Service).
Conectado a la base de datos PostgreSQL local risa_db (tabla risa_raw.signals).
"""

from typing import List, Dict, Any, Optional
from app.services.data_loader import DataLoaderService
from app.schemas.signals import RiskSignalSchema


def safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        s = str(val).strip()
        if not s or s.lower() in ("none", "null", "nan"):
            return default
        return float(s)
    except Exception:
        return default


class SignalService:
    """
    Servicio para consultar las alertas de riesgo generadas desde PostgreSQL risa_db.
    """
    def __init__(self):
        self.loader = DataLoaderService()

    def get_signals(
        self,
        priority_level: Optional[str] = None,
        patient_id: Optional[str] = None
    ) -> List[RiskSignalSchema]:
        signal_list = []

        try:
            sql = "SELECT signal_id, patient_id, decision_datetime, risk_score, priority_level, evidence_start, evidence_end, explanation, model_version FROM risa_raw.signals ORDER BY risk_score DESC;"
            rows = self.loader.query_db(sql)
            for s in rows:
                sig = RiskSignalSchema(
                    signal_id=str(s.get("signal_id", "SIG-000000")),
                    patient_id=str(s.get("patient_id", "PAT-0000")),
                    decision_datetime=str(s.get("decision_datetime", "")),
                    risk_score=safe_float(s.get("risk_score"), default=0.0),
                    priority_level=str(s.get("priority_level", "LOW")),
                    evidence_start=str(s.get("evidence_start", "")),
                    evidence_end=str(s.get("evidence_end", "")),
                    explanation=str(s.get("explanation", "")),
                    model_version=str(s.get("model_version", "v1.0.0"))
                )

                if priority_level and sig.priority_level != priority_level:
                    continue
                if patient_id and sig.patient_id != patient_id:
                    continue

                signal_list.append(sig)
        except Exception as e:
            print(f"[WARN] Error al consultar señales en PostgreSQL: {e}")

        # Fallback CSV si la base de datos no arrojó resultados
        if not signal_list:
            signals_raw = self.loader.load_csv_records("signals.csv", is_results=True)
            for s in signals_raw:
                sig = RiskSignalSchema(
                    signal_id=s.get("signal_id", "SIG-000000"),
                    patient_id=s.get("patient_id", "PAT-0000"),
                    decision_datetime=s.get("decision_datetime", ""),
                    risk_score=safe_float(s.get("risk_score"), default=0.0),
                    priority_level=s.get("priority_level", "LOW"),
                    evidence_start=s.get("evidence_start", ""),
                    evidence_end=s.get("evidence_end", ""),
                    explanation=s.get("explanation", ""),
                    model_version=s.get("model_version", "v1.0.0")
                )

                if priority_level and sig.priority_level != priority_level:
                    continue
                if patient_id and sig.patient_id != patient_id:
                    continue

                signal_list.append(sig)

        signal_list.sort(key=lambda x: x.risk_score, reverse=True)
        return signal_list

    def get_signal_by_id(self, signal_id: str) -> Optional[RiskSignalSchema]:
        signals = self.get_signals()
        return next((s for s in signals if s.signal_id == signal_id), None)

