"""
Módulo de Validación de Esquema y Contratos Canónicos.
Verifica campos obligatorios indispensables antes de procesar o limpiar el lote.
"""

from typing import List, Tuple, Optional
from ingestion.models import CDMRecord, AuditEntry


class SchemaValidator:
    """
    Validador de contratos canónicos para CDMRecords.
    """
    def __init__(self, reject_invalid: bool = False):
        self.reject_invalid = reject_invalid

    def validate(
        self, records: List[CDMRecord], audit_log: Optional[List[AuditEntry]] = None
    ) -> Tuple[List[CDMRecord], List[CDMRecord]]:
        """
        Valida una lista de CDMRecords y registra en audit_log cualquier no conformidad.
        Retorna una tupla: (registros_validos, registros_invalidos).
        """
        valid_records: List[CDMRecord] = []
        invalid_records: List[CDMRecord] = []

        for rec in records:
            # Comprobación de integridad estructural según el esquema propio de la cabecera
            missing_fields = []
            if not rec.record_id or not str(rec.record_id).strip():
                missing_fields.append("record_id")

            # Para registros sin header_fields explícito (compatibilidad previa), evaluar identificador
            if not rec.header_fields:
                if not rec.patient_id and not rec.device_id and not rec.facility_id:
                    missing_fields.append("entity_identifier")

            if not missing_fields:
                valid_records.append(rec)
            else:
                reason = f"Esquema incompleto para {rec.source_file}: faltan campos estructurales obligatorios [{', '.join(missing_fields)}]"
                rec.plausibility_status = "INVALID_SCHEMA"
                rec.add_audit_entry(
                    stage="SCHEMA_VALIDATION",
                    action="DISCARDED" if self.reject_invalid else "FLAGGED",
                    reason=reason
                )

                if audit_log is not None:
                    audit_log.append(AuditEntry(
                        record_id=rec.record_id or "UNKNOWN",
                        patient_id=rec.patient_id or "UNKNOWN",
                        source_file=rec.source_file,
                        variable_code=rec.variable_code or "METADATA",
                        stage="SCHEMA_VALIDATION",
                        action="DISCARDED" if self.reject_invalid else "FLAGGED",
                        reason=reason,
                        details={"missing_fields": missing_fields}
                    ))

                invalid_records.append(rec)
                if not self.reject_invalid:
                    valid_records.append(rec)

        return valid_records, invalid_records
