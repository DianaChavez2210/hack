"""
Módulo de Integridad Referencial y Relacional (SystemIntegrityValidator).
Ejecuta validaciones entre dominios cruzando registros con tablas maestras:
- IR-01: Pacientes existentes y activos (patients.csv).
- IR-02: Coherencia de episodio y paciente (encounters.csv).
- IR-03: Asignación y estado de dispositivos (devices.csv).
- PL-03: Consistencia demográfica paciente (paciente/sexo/edad).
"""

from typing import List, Dict, Any, Optional
from ingestion.models import CDMRecord, AuditEntry


class SystemIntegrityValidator:
    """
    Validador de integridad referencial y consistencia de entidades cruzadas.
    """
    def __init__(
        self,
        patients_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        encounters_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        devices_dict: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        self.patients_dict = patients_dict or {}
        self.encounters_dict = encounters_dict or {}
        self.devices_dict = devices_dict or {}

    def set_master_context(
        self,
        patients_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        encounters_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        devices_dict: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        if patients_dict is not None:
            self.patients_dict = patients_dict
        if encounters_dict is not None:
            self.encounters_dict = encounters_dict
        if devices_dict is not None:
            self.devices_dict = devices_dict

    def validate(
        self, records: List[CDMRecord], audit_log: Optional[List[AuditEntry]] = None
    ) -> List[CDMRecord]:
        for rec in records:
            # 1. Regla IR-01: Pacientes Existentes y Activos
            if rec.patient_id and self.patients_dict:
                pat_info = self.patients_dict.get(rec.patient_id)
                if not pat_info:
                    reason = f"Identificador de paciente desconocido '{rec.patient_id}' en maestro patients"
                    if rec.plausibility_status == "VALID":
                        rec.plausibility_status = "INVALID_PATIENT_ID"
                    rec.add_audit_entry(stage="REFERENTIAL_INTEGRITY", action="FLAGGED", reason=reason)
                    if audit_log is not None:
                        audit_log.append(AuditEntry(
                            record_id=rec.record_id,
                            patient_id=rec.patient_id,
                            source_file=rec.source_file,
                            variable_code=rec.variable_code or "PATIENT_REF",
                            stage="REFERENTIAL_INTEGRITY",
                            action="FLAGGED",
                            reason=reason,
                            details={"rule": "IR-01", "patient_id": rec.patient_id}
                        ))
                else:
                    is_active = pat_info.get("active")
                    if is_active is not None and str(is_active).lower() in ("false", "0"):
                        reason = f"Registro asociado a paciente inactivo '{rec.patient_id}'"
                        if rec.plausibility_status == "VALID":
                            rec.plausibility_status = "INACTIVE_PATIENT"
                        rec.add_audit_entry(stage="REFERENTIAL_INTEGRITY", action="FLAGGED", reason=reason)
                        if audit_log is not None:
                            audit_log.append(AuditEntry(
                                record_id=rec.record_id,
                                patient_id=rec.patient_id,
                                source_file=rec.source_file,
                                variable_code=rec.variable_code or "PATIENT_REF",
                                stage="REFERENTIAL_INTEGRITY",
                                action="FLAGGED",
                                reason=reason,
                                details={"rule": "IR-01", "patient_id": rec.patient_id}
                            ))

            # 2. Regla IR-02: Coherencia Episodio - Paciente
            if rec.encounter_id and self.encounters_dict:
                enc_info = self.encounters_dict.get(rec.encounter_id)
                if not enc_info:
                    reason = f"Identificador de episodio desconocido '{rec.encounter_id}' en maestro encounters"
                    if rec.plausibility_status == "VALID":
                        rec.plausibility_status = "UNKNOWN_ENCOUNTER"
                    rec.add_audit_entry(stage="REFERENTIAL_INTEGRITY", action="FLAGGED", reason=reason)
                    if audit_log is not None:
                        audit_log.append(AuditEntry(
                            record_id=rec.record_id,
                            patient_id=rec.patient_id,
                            source_file=rec.source_file,
                            variable_code=rec.variable_code or "ENCOUNTER_REF",
                            stage="REFERENTIAL_INTEGRITY",
                            action="FLAGGED",
                            reason=reason,
                            details={"rule": "IR-02", "encounter_id": rec.encounter_id}
                        ))
                else:
                    enc_pat = enc_info.get("patient_id")
                    if rec.patient_id and enc_pat and rec.patient_id != enc_pat:
                        reason = f"Incoherencia entre episodio '{rec.encounter_id}' (paciente '{enc_pat}') y paciente en registro ('{rec.patient_id}')"
                        rec.plausibility_status = "ENCOUNTER_PATIENT_MISMATCH"
                        rec.add_audit_entry(stage="REFERENTIAL_INTEGRITY", action="FLAGGED", reason=reason)
                        if audit_log is not None:
                            audit_log.append(AuditEntry(
                                record_id=rec.record_id,
                                patient_id=rec.patient_id,
                                source_file=rec.source_file,
                                variable_code=rec.variable_code or "ENCOUNTER_REF",
                                stage="REFERENTIAL_INTEGRITY",
                                action="FLAGGED",
                                reason=reason,
                                details={"rule": "IR-02", "encounter_id": rec.encounter_id, "encounter_patient": enc_pat}
                            ))

            # 3. Regla IR-03: Asignación y Estado de Dispositivos
            if rec.device_id and self.devices_dict:
                dev_info = self.devices_dict.get(rec.device_id)
                if not dev_info:
                    reason = f"Dispositivo desconocido '{rec.device_id}' en maestro devices"
                    if rec.plausibility_status == "VALID":
                        rec.plausibility_status = "UNKNOWN_DEVICE"
                    rec.add_audit_entry(stage="DEVICE_INTEGRITY", action="FLAGGED", reason=reason)
                    if audit_log is not None:
                        audit_log.append(AuditEntry(
                            record_id=rec.record_id,
                            patient_id=rec.patient_id,
                            source_file=rec.source_file,
                            variable_code=rec.variable_code or "DEVICE_REF",
                            stage="DEVICE_INTEGRITY",
                            action="FLAGGED",
                            reason=reason,
                            details={"rule": "IR-03", "device_id": rec.device_id}
                        ))
                else:
                    dev_active = dev_info.get("active")
                    if dev_active is not None and str(dev_active).lower() in ("false", "0"):
                        reason = f"Dispositivo inactivo '{rec.device_id}' asignado a la medición"
                        rec.plausibility_status = "INACTIVE_DEVICE"
                        rec.add_audit_entry(stage="DEVICE_INTEGRITY", action="FLAGGED", reason=reason)
                        if audit_log is not None:
                            audit_log.append(AuditEntry(
                                record_id=rec.record_id,
                                patient_id=rec.patient_id,
                                source_file=rec.source_file,
                                variable_code=rec.variable_code or "DEVICE_REF",
                                stage="DEVICE_INTEGRITY",
                                action="FLAGGED",
                                reason=reason,
                                details={"rule": "IR-03", "device_id": rec.device_id}
                            ))

                    assigned_pat = dev_info.get("assigned_patient_id")
                    if rec.patient_id and assigned_pat and rec.patient_id != assigned_pat:
                        reason = f"Dispositivo '{rec.device_id}' asignado a paciente '{assigned_pat}' pero usado por '{rec.patient_id}'"
                        rec.plausibility_status = "DEVICE_PATIENT_MISMATCH"
                        rec.add_audit_entry(stage="DEVICE_INTEGRITY", action="FLAGGED", reason=reason)
                        if audit_log is not None:
                            audit_log.append(AuditEntry(
                                record_id=rec.record_id,
                                patient_id=rec.patient_id,
                                source_file=rec.source_file,
                                variable_code=rec.variable_code or "DEVICE_REF",
                                stage="DEVICE_INTEGRITY",
                                action="FLAGGED",
                                reason=reason,
                                details={"rule": "IR-03", "device_id": rec.device_id, "assigned_patient": assigned_pat}
                            ))

            # 4. Regla PL-03: Consistencia Demográfica Paciente
            if rec.patient_id and self.patients_dict:
                pat_info = self.patients_dict.get(rec.patient_id)
                if pat_info:
                    age = pat_info.get("age_years")
                    sex = pat_info.get("sex_at_birth")

                    if rec.variable_code == "PREGNANCY_CONTEXT" and sex == "M":
                        reason = f"Incoherencia demográfica: variable de embarazo en paciente de sexo masculino ({rec.patient_id})"
                        rec.plausibility_status = "DEMOGRAPHIC_INCONSISTENCY"
                        rec.add_audit_entry(stage="DEMOGRAPHIC_CHECK", action="FLAGGED", reason=reason)
                        if audit_log is not None:
                            audit_log.append(AuditEntry(
                                record_id=rec.record_id,
                                patient_id=rec.patient_id,
                                source_file=rec.source_file,
                                variable_code=rec.variable_code,
                                stage="DEMOGRAPHIC_CHECK",
                                action="FLAGGED",
                                reason=reason,
                                details={"rule": "PL-03", "sex": sex, "age": age}
                            ))

        return records
