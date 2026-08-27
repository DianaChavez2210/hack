"""
Esquemas Pydantic V2 para Evidencias y Grafo de Linaje (Evidence Schemas).
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class EvidenceRecordSchema(BaseModel):
    signal_id: str
    source_file: str
    record_id: str
    variable_code: str
    event_datetime: str
    available_datetime: str
    evidence_role: str  # PRIMARY, SUPPORTING, CONTEXT, QUALITY
    contribution: float
    value_numeric: Optional[float] = None
    original_unit: Optional[str] = None
    canonical_unit: Optional[str] = None


class SignalEvidenceResponse(BaseModel):
    signal_id: str
    patient_id: str
    decision_datetime: str
    risk_score: float
    priority_level: str
    shap_contributions: List[Dict[str, Any]]
    evidences: List[EvidenceRecordSchema]
