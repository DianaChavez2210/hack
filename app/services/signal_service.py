"""
Servicio de Consulta de Señales de Riesgo Clínico (Signal Service).
"""

from typing import List, Dict, Any, Optional
from app.services.data_loader import DataLoaderService
from app.schemas.signals import RiskSignalSchema


class SignalService:
    """
    Servicio para consultar las alertas de riesgo generadas en results/signals.csv.
    """
    def __init__(self):
        self.loader = DataLoaderService()

    def get_signals(
        self,
        priority_level: Optional[str] = None,
        patient_id: Optional[str] = None
    ) -> List[RiskSignalSchema]:
        signals_raw = self.loader.load_csv_records("signals.csv", is_results=True)

        signal_list = []
        for s in signals_raw:
            sig = RiskSignalSchema(
                signal_id=s.get("signal_id", "SIG-000000"),
                patient_id=s.get("patient_id", "PAT-0000"),
                decision_datetime=s.get("decision_datetime", ""),
                risk_score=float(s.get("risk_score", 0.0)),
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
