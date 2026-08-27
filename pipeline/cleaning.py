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
            # 1. Deduplicación por clave única
            key = (rec.record_id, rec.source_file)
            if self.drop_duplicates:
                if key in seen_keys:
                    reason = f"Registro duplicado descartado por clave compuesta (record_id='{rec.record_id}', source_file='{rec.source_file}')"
                    if audit_log is not None:
                        audit_log.append(AuditEntry(
                            record_id=rec.record_id,
                            patient_id=rec.patient_id,
                            source_file=rec.source_file,
                            variable_code=rec.variable_code,
                            stage="DEDUPLICATION",
                            action="DISCARDED",
                            reason=reason,
                            original_value=rec.value_numeric or rec.value_text,
                            details={"encounter_id": rec.encounter_id, "timestamp": rec.event_datetime}
                        ))
                    continue
                seen_keys.add(key)

            # 2. Control de Missingness (No destructivo)
            if rec.value_numeric is None and (rec.value_text is None or str(rec.value_text).strip() == ""):
                rec.is_observed = False
                reason = "Valor nulo detectado; preservado con is_observed=False sin sustitución por 0 para evaluar completitud clínica"
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
                        reason=reason
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

            # 4. Evaluación de Calidad de Señal
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

            cleaned.append(rec)

        return cleaned
