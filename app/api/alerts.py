"""
Endpoints FastAPI para Alertas Técnicas (Technical Alerts Router).
"""

from fastapi import APIRouter
from app.schemas.alerts import TechnicalAlertListResponse
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Technical Alerts"])
alert_service = AlertService()


@router.get("/technical", response_model=TechnicalAlertListResponse)
def get_technical_alerts():
    """
    Retorna las incidencias técnicas de red, desconexiones y baja calidad de señal de hardware.
    """
    alerts = alert_service.get_technical_alerts()
    return TechnicalAlertListResponse(total=len(alerts), alerts=alerts)
