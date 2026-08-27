"""
Esquemas Pydantic V2 para Pacientes (Patient Schemas).
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PatientBase(BaseModel):
    patient_id: str
    age_years: Optional[float] = None
    sex_at_birth: Optional[str] = None
    facility_id: Optional[str] = None
    care_program: Optional[str] = "HOME_MONITORING"
    risk_score: float = 0.15
    priority_level: str = "LOW"
    status: str = "CONNECTED"


class PatientDetail(PatientBase):
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    medications: List[Dict[str, Any]] = Field(default_factory=list)
    devices: List[Dict[str, Any]] = Field(default_factory=list)
    encounters: List[Dict[str, Any]] = Field(default_factory=list)


class PatientListResponse(BaseModel):
    total: int
    patients: List[PatientBase]
