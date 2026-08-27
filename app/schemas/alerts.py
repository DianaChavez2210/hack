"""
Esquemas Pydantic V2 para Alertas Técnicas y de Hardware (Technical Alert Schemas).
"""

from typing import List, Optional
from pydantic import BaseModel


class TechnicalAlertSchema(BaseModel):
    alert_id: str
    patient_id: Optional[str] = None
    device_id: Optional[str] = None
    facility_id: Optional[str] = None
    alert_type: str  # DISCONNECTED, DELAYED_SYNC, LOW_SIGNAL_QUALITY, PACKET_LOSS
    severity: str    # HIGH, MEDIUM, LOW
    timestamp: str
    message: str
    packet_loss_estimate: Optional[float] = None
    signal_quality_index: Optional[float] = None


class TechnicalAlertListResponse(BaseModel):
    total: int
    alerts: List[TechnicalAlertSchema]
