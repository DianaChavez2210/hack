"""
Esquemas Pydantic V2 para Señales de Riesgo Clínico (Signal Schemas).
"""

from typing import List, Optional
from pydantic import BaseModel


class RiskSignalSchema(BaseModel):
    signal_id: str
    patient_id: str
    decision_datetime: str
    risk_score: float
    priority_level: str
    evidence_start: str
    evidence_end: str
    explanation: str
    model_version: str = "v1.0.0"


class SignalListResponse(BaseModel):
    total: int
    signals: List[RiskSignalSchema]
