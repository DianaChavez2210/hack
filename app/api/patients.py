"""
Endpoints FastAPI para Pacientes (Patients Router).
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from app.schemas.patients import PatientBase, PatientDetail, PatientListResponse
from app.schemas.timeline import PatientTimelineResponse
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Patients"])
patient_service = PatientService()


@router.get("", response_model=PatientListResponse)
def get_patients(
    care_program: Optional[str] = Query(None, description="Filtro por programa de atención"),
    priority_level: Optional[str] = Query(None, description="Filtro por nivel de riesgo (CRITICAL, HIGH, MEDIUM, LOW)"),
    search: Optional[str] = Query(None, description="Búsqueda por ID de paciente")
):
    """
    Lista todos los pacientes priorizados por score de riesgo con filtros operacionales.
    """
    patients = patient_service.get_patients(
        care_program=care_program,
        priority_level=priority_level,
        search_query=search
    )
    return PatientListResponse(total=len(patients), patients=patients)


@router.get("/{patient_id}", response_model=PatientDetail)
def get_patient_detail(patient_id: str):
    """
    Retorna la ficha clínica maestra del paciente (demografía, comorbilidades, fármacos y dispositivos).
    """
    patient = patient_service.get_patient_detail(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Paciente {patient_id} no encontrado")
    return patient


@router.get("/{patient_id}/timeline", response_model=PatientTimelineResponse)
def get_patient_timeline(patient_id: str):
    """
    Serie temporal fisiológica consolidada (signos vitales, wearables, laboratorio y reposo/sueño).
    """
    timeline = patient_service.get_patient_timeline(patient_id)
    if not timeline.get("items"):
        raise HTTPException(status_code=404, detail=f"No hay serie temporal para el paciente {patient_id}")
    return timeline
