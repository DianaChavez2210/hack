"""
Esquemas Pydantic V2 para la Serie Temporal Consolidada (Timeline Schemas).
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class TimelineItemSchema(BaseModel):
    record_id: str
    patient_id: str
    variable_code: str
    value_numeric: Optional[float] = None
    original_unit: Optional[str] = None
    event_datetime: str
    available_datetime: str
    source_file: str
    quality_flag: Optional[str] = "OK"
    signal_quality: Optional[float] = 1.0
    patient_state: Optional[str] = None  # SLEEP, AWAKE


class PatientTimelineResponse(BaseModel):
    patient_id: str
    total_records: int
    context_intervals: List[Dict[str, Any]]
    items: List[TimelineItemSchema]
