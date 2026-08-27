"""
Módulo de Contextualización Operacional y de Red.
Integra información de estados de paciente (sueño/actividad) y eventos de conectividad.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from ingestion.models import CDMRecord, AuditEntry
from pipeline.temporal import TemporalProcessor


class Contextualizer:
    """
    Contextualizador para enriquecer registros clínicos con estados operativos y de red.
    """
    def __init__(
        self,
        patient_contexts: Optional[List[Dict[str, Any]]] = None,
        connectivity_events: Optional[List[Dict[str, Any]]] = None
    ):
        self.patient_contexts = patient_contexts or []
        self.connectivity_events = connectivity_events or []
        self._parser = TemporalProcessor._parse_iso_or_custom

    def contextualize(
        self, records: List[CDMRecord], audit_log: Optional[List[AuditEntry]] = None
    ) -> List[CDMRecord]:
        for rec in records:
            if not rec.event_datetime:
                continue

            rec_dt = self._parser(rec.event_datetime)
            if not rec_dt:
                continue

            # 1. Enriquecer con Estado Contextual del Paciente (ej. SLEEP_STATE)
            for ctx in self.patient_contexts:
                if ctx.get("patient_id") == rec.patient_id:
                    start_dt = self._parser(ctx.get("start_datetime"))
                    end_dt = self._parser(ctx.get("end_datetime"))
                    if start_dt and end_dt and start_dt <= rec_dt <= end_dt:
                        rec.context_info["patient_state"] = ctx.get("context_value")
                        rec.context_info["context_confidence"] = ctx.get("confidence")

            # 2. Enriquecer con Eventos de Conectividad de Red
            for conn in self.connectivity_events:
                if conn.get("patient_id") == rec.patient_id or (rec.device_id and conn.get("device_id") == rec.device_id):
                    start_dt = self._parser(conn.get("start_datetime"))
                    end_dt = self._parser(conn.get("end_datetime"))
                    if start_dt and end_dt and start_dt <= rec_dt <= end_dt:
                        status = conn.get("connectivity_status")
                        loss = conn.get("packet_loss_estimate")
                        rec.context_info["network_status"] = status
                        rec.context_info["packet_loss"] = loss

                        if status in ("DISCONNECTED", "INTERMITTENT"):
                            reason = f"Evento de red detectado ({status}, pérdida={loss}); se marca como NETWORK_INTERRUPTED para no confundir con deterioro clínico"
                            if rec.plausibility_status == "VALID":
                                rec.plausibility_status = "NETWORK_INTERRUPTED"
                            rec.add_audit_entry(stage="NETWORK_CONTEXT", action="FLAGGED", reason=reason)
                            if audit_log is not None:
                                audit_log.append(AuditEntry(
                                    record_id=rec.record_id,
                                    patient_id=rec.patient_id,
                                    source_file=rec.source_file,
                                    variable_code=rec.variable_code,
                                    stage="NETWORK_CONTEXT",
                                    action="FLAGGED",
                                    reason=reason,
                                    details={"connectivity_status": status, "packet_loss": loss}
                                ))

        return records
