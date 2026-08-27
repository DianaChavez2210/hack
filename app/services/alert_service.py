"""
Servicio de Alertas Técnicas y de Hardware (Alert Service).
Diferencia descompensación clínica de desincronización de red o fallas de batería/sensor.
"""

from typing import List, Dict, Any
from app.services.data_loader import DataLoaderService
from app.schemas.alerts import TechnicalAlertSchema


class AlertService:
    """
    Servicio de consulta para incidencias técnicas de hardware y red.
    """
    def __init__(self):
        self.loader = DataLoaderService()

    def get_technical_alerts(self) -> List[TechnicalAlertSchema]:
        connectivity = self.loader.load_csv_records("connectivity_events.csv")
        device_obs = self.loader.load_csv_records("device_observations.csv")

        alerts = []
        for idx, conn in enumerate(connectivity):
            status = conn.get("connectivity_status")
            loss = conn.get("packet_loss_estimate")
            loss_val = float(loss) if loss else 0.0

            if status in ("DISCONNECTED", "INTERMITTENT") or loss_val > 0.20:
                alerts.append(TechnicalAlertSchema(
                    alert_id=f"ALT-NET-{idx+1:04d}",
                    patient_id=conn.get("patient_id"),
                    device_id=conn.get("device_id"),
                    facility_id=conn.get("facility_id", "FAC-01"),
                    alert_type="NETWORK_INTERRUPTED" if status == "DISCONNECTED" else "PACKET_LOSS",
                    severity="HIGH" if loss_val > 0.30 or status == "DISCONNECTED" else "MEDIUM",
                    timestamp=conn.get("start_datetime") or "2026-07-10 12:00:00",
                    message=f"Evento de red ({status}): pérdida de paquetes estimada en {loss_val*100:.1f}%",
                    packet_loss_estimate=loss_val,
                    signal_quality_index=None
                ))

        for idx, dev in enumerate(device_obs[:50]):
            sqi = dev.get("signal_quality_index")
            rel = dev.get("reliability_class")
            sqi_val = float(sqi) if sqi else 1.0

            if sqi_val < 0.85 or rel == "R3_VARIABLE":
                alerts.append(TechnicalAlertSchema(
                    alert_id=f"ALT-HW-{idx+1:04d}",
                    patient_id=dev.get("patient_id"),
                    device_id=dev.get("device_id"),
                    facility_id="FAC-01",
                    alert_type="LOW_SIGNAL_QUALITY",
                    severity="MEDIUM" if sqi_val > 0.70 else "HIGH",
                    timestamp=dev.get("timestamp") or "2026-07-10 12:00:00",
                    message=f"Alerta de Hardware: Calidad de señal deficiente ({sqi_val:.2f}) en dispositivo {dev.get('device_id')}",
                    packet_loss_estimate=None,
                    signal_quality_index=sqi_val
                ))

        return alerts
