"""
Módulo de Contextualización Operacional y de Red.
Integra información de estados de paciente (sueño/actividad) y eventos de conectividad.
Optimizado con índices O(1) por patient_id y device_id para alto rendimiento.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
from ingestion.models import CDMRecord, AuditEntry
from pipeline.temporal import TemporalProcessor


class Contextualizer:
    """
    Contextualizador para enriquecer registros clínicos con estados operativos y de red.
    Indexación O(1) para soporte de datasets masivos de telemetría.
    """
    def __init__(
        self,
        patient_contexts: Optional[List[Dict[str, Any]]] = None,
        connectivity_events: Optional[List[Dict[str, Any]]] = None
    ):
        self._parser = TemporalProcessor._parse_iso_or_custom
        self.patient_contexts = patient_contexts or []
        self.connectivity_events = connectivity_events or []
        self._build_indices()

    def set_context(
        self,
        patient_contexts: Optional[List[Dict[str, Any]]] = None,
        connectivity_events: Optional[List[Dict[str, Any]]] = None
    ):
        if patient_contexts is not None:
            self.patient_contexts = patient_contexts
        if connectivity_events is not None:
            self.connectivity_events = connectivity_events
        self._build_indices()

    def _build_indices(self):
        """Indexa contextualizaciones y eventos de conectividad por patient_id y device_id en O(1)."""
        self.patient_ctx_by_pat = defaultdict(list)
        for ctx in self.patient_contexts:
            pat_id = ctx.get("patient_id")
            if pat_id:
                start_dt = self._parser(ctx.get("start_datetime"))
                end_dt = self._parser(ctx.get("end_datetime"))
                self.patient_ctx_by_pat[pat_id].append({
                    "raw": ctx,
                    "start_dt": start_dt,
                    "end_dt": end_dt
                })

        self.conn_events_by_pat = defaultdict(list)
        self.conn_events_by_dev = defaultdict(list)
        for conn in self.connectivity_events:
            pat_id = conn.get("patient_id")
            dev_id = conn.get("device_id")
            start_dt = self._parser(conn.get("start_datetime"))
            end_dt = self._parser(conn.get("end_datetime"))
            item = {"raw": conn, "start_dt": start_dt, "end_dt": end_dt}
            if pat_id:
                self.conn_events_by_pat[pat_id].append(item)
            if dev_id:
                self.conn_events_by_dev[dev_id].append(item)

    def contextualize(
        self, records: List[CDMRecord], audit_log: Optional[List[AuditEntry]] = None
    ) -> List[CDMRecord]:
        for rec in records:
            if not rec.event_datetime:
                continue

            rec_dt = self._parser(rec.event_datetime)
            if not rec_dt:
                continue

            # 1. Enriquecer con Estado Contextual del Paciente (O(1) por paciente)
            if rec.patient_id and rec.patient_id in self.patient_ctx_by_pat:
                for ctx_item in self.patient_ctx_by_pat[rec.patient_id]:
                    start_dt = ctx_item["start_dt"]
                    end_dt = ctx_item["end_dt"]
                    ctx = ctx_item["raw"]

                    if start_dt and end_dt and start_dt <= rec_dt <= end_dt:
                        state_val = ctx.get("context_value")
                        rec.context_info["patient_state"] = state_val
                        rec.context_info["context_confidence"] = ctx.get("confidence")

                        # Regla CX-03: Correlación Fisiológica - Contexto (Sueño)
                        if state_val == "SLEEP":
                            val = rec.converted_value if rec.converted_value is not None else rec.value_numeric
                            if val is not None:
                                is_suspicious = False
                                reason = ""
                                if rec.variable_code in ("WEARABLE_HR", "HR") and val > 100.0:
                                    is_suspicious = True
                                    reason = f"Frecuencia cardíaca elevada ({val} bpm) durante estado SLEEP en paciente {rec.patient_id}"
                                elif rec.variable_code == "STEPS" and val > 10.0:
                                    is_suspicious = True
                                    reason = f"Conteo de pasos ({val}) detectado durante estado SLEEP en paciente {rec.patient_id}"

                                if is_suspicious:
                                    rec.plausibility_status = "SUSPICIOUS_SLEEP_ACTIVITY"
                                    rec.add_audit_entry(stage="PATIENT_CONTEXT", action="FLAGGED", reason=reason)
                                    if audit_log is not None:
                                        audit_log.append(AuditEntry(
                                            record_id=rec.record_id,
                                            patient_id=rec.patient_id,
                                            source_file=rec.source_file,
                                            variable_code=rec.variable_code,
                                            stage="PATIENT_CONTEXT",
                                            action="FLAGGED",
                                            reason=reason,
                                            details={"rule": "CX-03", "patient_state": state_val, "value": val}
                                        ))

            # 2. Enriquecer con Eventos de Conectividad de Red (O(1) por paciente / dispositivo)
            conn_candidates = []
            if rec.patient_id and rec.patient_id in self.conn_events_by_pat:
                conn_candidates.extend(self.conn_events_by_pat[rec.patient_id])
            if rec.device_id and rec.device_id in self.conn_events_by_dev:
                conn_candidates.extend(self.conn_events_by_dev[rec.device_id])

            for conn_item in conn_candidates:
                start_dt = conn_item["start_dt"]
                end_dt = conn_item["end_dt"]
                conn = conn_item["raw"]

                if start_dt and end_dt and start_dt <= rec_dt <= end_dt:
                    status = conn.get("connectivity_status")
                    loss = conn.get("packet_loss_estimate")
                    rec.context_info["network_status"] = status
                    rec.context_info["packet_loss"] = loss

                    if status in ("DISCONNECTED", "INTERMITTENT") or (loss is not None and float(loss) > 0.20):
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
                                details={"rule": "CX-01", "connectivity_status": status, "packet_loss": loss}
                            ))

        return records
