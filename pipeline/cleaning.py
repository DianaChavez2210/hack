"""
Módulo de Limpieza de Datos, Deduplicación y Control de Missingness.
Aplica directrices fundamentales:
1. Missing no es cero ni normal: se preserva null/None con is_observed=False.
2. Deduplicación por (record_id, source_file).
3. Identificación de retransmisiones y artefactos.
"""

from typing import List, Set, Tuple, Optional
from ingestion.models import CDMRecord, AuditEntry


class DataCleaner:
    """
    Limpiador común de registros CDM con trazabilidad y auditoría de decisiones.
    """
    def __init__(self, drop_duplicates: bool = True):
        self.drop_duplicates = drop_duplicates

    def clean(
        self, records: List[CDMRecord], audit_log: Optional[List[AuditEntry]] = None
    ) -> List[CDMRecord]:
        """
        Ejecuta la limpieza sobre una lista de CDMRecords registrando el porqué de cada decisión.
        """
        cleaned: List[CDMRecord] = []
        seen_keys: Set[Tuple[str, str]] = set()

        for rec in records:
            # 1. Deduplicación por clave de origen única
            key = (rec.record_id, rec.source_file)
            if self.drop_duplicates:
                if key in seen_keys:
                    reason = f"Registro duplicado descartado por clave de origen (record_id='{rec.record_id}', source_file='{rec.source_file}')"
                    if audit_log is not None:
                        audit_log.append(AuditEntry(
                            record_id=rec.record_id,
                            patient_id=rec.patient_id,
                            source_file=rec.source_file,
                            variable_code=rec.variable_code,
                            stage="DEDUPLICATION",
                            action="DISCARDED",
                            reason=reason,
                            original_value=rec.value_numeric or rec.value_text or rec.record_id,
                            details={"encounter_id": rec.encounter_id, "timestamp": rec.event_datetime}
                        ))
                    continue
                seen_keys.add(key)

            src_file_lower = rec.source_file.lower()
            is_master_table = any(m in src_file_lower for m in ("devices", "patients", "healthcare_facilities", "facilities", "units_catalog", "variable_catalog", "source_catalog"))

            # 2. Control de Missingness y Detección de Valores Nulos/Vacíos en Cabecera
            if rec.null_fields and len(rec.null_fields) > 0 and not is_master_table:
                null_list_str = ", ".join(rec.null_fields)
                reason = f"Valores nulos/vacíos detectados en [{null_list_str}]; preservados como None sin imputación destructiva"
                rec.add_audit_entry(
                    stage="MISSINGNESS",
                    action="PRESERVED_MISSING",
                    reason=reason
                )
                if audit_log is not None:
                    audit_log.append(AuditEntry(
                        record_id=rec.record_id,
                        patient_id=rec.patient_id,
                        source_file=rec.source_file,
                        variable_code=rec.variable_code,
                        stage="MISSINGNESS",
                        action="PRESERVED_MISSING",
                        reason=reason,
                        details={"null_fields": rec.null_fields}
                    ))
            elif not is_master_table and (rec.value_numeric is None and (rec.value_text is None or str(rec.value_text).strip() == "")):
                rec.is_observed = False
                reason = "Valor principal de observación nulo/vacío; preservado como None sin imputación destructiva"
                rec.add_audit_entry(
                    stage="MISSINGNESS",
                    action="PRESERVED_MISSING",
                    reason=reason
                )
                if audit_log is not None:
                    audit_log.append(AuditEntry(
                        record_id=rec.record_id,
                        patient_id=rec.patient_id,
                        source_file=rec.source_file,
                        variable_code=rec.variable_code,
                        stage="MISSINGNESS",
                        action="PRESERVED_MISSING",
                        reason=reason,
                        details={"null_fields": rec.null_fields}
                    ))
            else:
                rec.is_observed = True

            # 3. Tratamiento de Retransmisiones
            if rec.source_system == "MONITOR_RETRANSMIT":
                rec.is_retransmission = True
                reason = "Observación identificada como retransmisión diferida (MONITOR_RETRANSMIT)"
                rec.add_audit_entry(stage="RETRANSMISSION", action="FLAGGED", reason=reason)
                if audit_log is not None:
                    audit_log.append(AuditEntry(
                        record_id=rec.record_id,
                        patient_id=rec.patient_id,
                        source_file=rec.source_file,
                        variable_code=rec.variable_code,
                        stage="RETRANSMISSION",
                        action="FLAGGED",
                        reason=reason,
                        details={"source_system": rec.source_system}
                    ))

            # 4. Evaluación de Calidad de Señal y Confiabilidad de Máquinas (solo en tablas de observaciones/telemetría)
            if not is_master_table:
                # 4.1 Evaluación por Confiabilidad de Máquina (reliability_class)
                rel_class = rec.header_fields.get("reliability_class") if rec.header_fields else None
                if rel_class == "R3_VARIABLE":
                    reason = f"Confiabilidad de dispositivo variable ({rel_class}); se marca como UNRELIABLE_DEVICE"
                    rec.plausibility_status = "UNRELIABLE_DEVICE"
                    rec.add_audit_entry(stage="SIGNAL_QUALITY", action="FLAGGED", reason=reason)
                    if audit_log is not None:
                        audit_log.append(AuditEntry(
                            record_id=rec.record_id,
                            patient_id=rec.patient_id,
                            source_file=rec.source_file,
                            variable_code=rec.variable_code,
                            stage="SIGNAL_QUALITY",
                            action="FLAGGED",
                            reason=reason,
                            details={"reliability_class": rel_class}
                        ))

                # 4.2 Evaluación por Estado Activo de Dispositivo
                is_active = rec.header_fields.get("active") if rec.header_fields else None
                if is_active is not None and str(is_active).lower() in ("false", "0"):
                    reason = "Dispositivo registrado como inactivo (active=False); marcado como INACTIVE_DEVICE"
                    rec.plausibility_status = "INACTIVE_DEVICE"
                    rec.add_audit_entry(stage="DEVICE_STATUS", action="FLAGGED", reason=reason)
                    if audit_log is not None:
                        audit_log.append(AuditEntry(
                            record_id=rec.record_id,
                            patient_id=rec.patient_id,
                            source_file=rec.source_file,
                            variable_code=rec.variable_code,
                            stage="DEVICE_STATUS",
                            action="FLAGGED",
                            reason=reason
                        ))

                # 4.3 Evaluación por Flags de Calidad de Medición y Señal
                if rec.quality_flag and str(rec.quality_flag).upper() not in ("OK", "VALID"):
                    reason = f"Calidad de señal deficiente ({rec.quality_flag}); se marca como NOISY_SIGNAL para penalizar peso en evidencia"
                    if rec.plausibility_status == "VALID":
                        rec.plausibility_status = "NOISY_SIGNAL"
                    rec.add_audit_entry(stage="SIGNAL_QUALITY", action="FLAGGED", reason=reason)
                    if audit_log is not None:
                        audit_log.append(AuditEntry(
                            record_id=rec.record_id,
                            patient_id=rec.patient_id,
                            source_file=rec.source_file,
                            variable_code=rec.variable_code,
                            stage="SIGNAL_QUALITY",
                            action="FLAGGED",
                            reason=reason,
                            details={"quality_flag": rec.quality_flag}
                        ))

                # 4.4 Evaluación por Índice Numérico de Calidad de Señal
                if rec.signal_quality is not None and rec.signal_quality < 0.85:
                    reason = f"Calidad de señal de máquina baja (signal_quality={rec.signal_quality} < 0.85); marcado como LOW_SIGNAL_QUALITY"
                    if rec.plausibility_status == "VALID":
                        rec.plausibility_status = "LOW_SIGNAL_QUALITY"
                    rec.add_audit_entry(stage="SIGNAL_QUALITY", action="FLAGGED", reason=reason)
                    if audit_log is not None:
                        audit_log.append(AuditEntry(
                            record_id=rec.record_id,
                            patient_id=rec.patient_id,
                            source_file=rec.source_file,
                            variable_code=rec.variable_code,
                            stage="SIGNAL_QUALITY",
                            action="FLAGGED",
                            reason=reason,
                            details={"signal_quality": rec.signal_quality}
                        ))

            cleaned.append(rec)

        return cleaned
