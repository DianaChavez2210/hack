"""
Endpoints FastAPI para Señales de Riesgo (Signals Router).
"""

from typing import Optional
from fastapi import APIRouter, Query
from app.schemas.signals import SignalListResponse, RiskSignalSchema
from app.services.signal_service import SignalService

router = APIRouter(prefix="/signals", tags=["Signals"])
signal_service = SignalService()


@router.get("", response_model=SignalListResponse)
def get_signals(
    priority_level: Optional[str] = Query(None, description="Filtro de prioridad (CRITICAL, HIGH, MEDIUM, LOW)"),
    patient_id: Optional[str] = Query(None, description="Filtro por ID de paciente")
):
    """
    Consulta las alertas de riesgo generadas por los modelos analíticos.
    """
    signals = signal_service.get_signals(
        priority_level=priority_level,
        patient_id=patient_id
    )
    return SignalListResponse(total=len(signals), signals=signals)
