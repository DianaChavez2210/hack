"""
Endpoints FastAPI para Linaje de Evidencia (Evidence Router).
"""

from fastapi import APIRouter, HTTPException
from app.schemas.evidence import SignalEvidenceResponse
from app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/signals", tags=["Evidence & Lineage"])
evidence_service = EvidenceService()


@router.get("/{signal_id}/evidence", response_model=SignalEvidenceResponse)
def get_signal_evidence(signal_id: str):
    """
    Retorna la justificación SHAP y la tabla de evidencias trazables a los registros CDM originales.
    """
    evidence = evidence_service.get_signal_evidence(signal_id)
    if not evidence:
        raise HTTPException(status_code=404, detail=f"No se encontró evidencia para la señal {signal_id}")
    return evidence
