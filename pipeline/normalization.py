"""
Módulo de Normalización de Unidades y Chequeo de Plausibilidad Biológica.
Utiliza los catálogos oficiales RISA (units_catalog.csv y variable_catalog.csv).
"""

import csv
import os
from typing import Dict, Any, Optional, List
from ingestion.models import CDMRecord, AuditEntry


class UnitNormalizer:
    """
    Normaliza unidades de medida a las unidades canónicas oficiales de RISA.
    """
    # Reglas base integradas según 05_metadata/units_catalog.csv
    DEFAULT_UNIT_RULES = {
        "bpm": {"canonical": "bpm", "factor": 1.0, "offset": 0.0},
        "rpm": {"canonical": "rpm", "factor": 1.0, "offset": 0.0},
        "%": {"canonical": "%", "factor": 1.0, "offset": 0.0},
        "degC": {"canonical": "degC", "factor": 1.0, "offset": 0.0},
        "degF": {"canonical": "degC", "factor": 0.5555555555555556, "offset": -17.77777777777778},
        "mmHg": {"canonical": "mmHg", "factor": 1.0, "offset": 0.0},
        "count": {"canonical": "count", "factor": 1.0, "offset": 0.0},
        "ratio": {"canonical": "ratio", "factor": 1.0, "offset": 0.0},
        "uA": {"canonical": "uA", "factor": 1.0, "offset": 0.0},
        "uB": {"canonical": "uB", "factor": 1.0, "offset": 0.0},
        "uC": {"canonical": "uC", "factor": 1.0, "offset": 0.0},
        "uD": {"canonical": "uD", "factor": 1.0, "offset": 0.0}
    }

    def __init__(self, catalog_path: Optional[str] = None):
        self.rules = dict(self.DEFAULT_UNIT_RULES)
        if catalog_path and os.path.exists(catalog_path):
            self._load_from_catalog(catalog_path)

    def _load_from_catalog(self, catalog_path: str):
        try:
            with open(catalog_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    u_code = row.get("unit_code")
                    if u_code:
                        self.rules[u_code] = {
                            "canonical": row.get("canonical_unit", u_code),
                            "factor": float(row.get("conversion_factor", 1.0)),
                            "offset": float(row.get("conversion_offset", 0.0))
                        }
        except Exception:
            pass

    def normalize(
        self, records: List[CDMRecord], audit_log: Optional[List[AuditEntry]] = None
    ) -> List[CDMRecord]:
        for rec in records:
            unit = rec.original_unit
            if unit in self.rules:
                rule = self.rules[unit]
                rec.canonical_unit = rule["canonical"]
                if rec.value_numeric is not None:
                    orig_val = rec.value_numeric
                    conv_val = round((orig_val * rule["factor"]) + rule["offset"], 4)
                    rec.converted_value = conv_val

                    if unit != rule["canonical"]:
                        reason = f"Unidad '{unit}' convertida a '{rule['canonical']}' (factor={rule['factor']}, offset={rule['offset']})"
                        rec.add_audit_entry(
                            stage="UNIT_NORMALIZATION",
                            action="CONVERTED",
                            reason=reason,
                            original_val=f"{orig_val} {unit}",
                            new_val=f"{conv_val} {rule['canonical']}"
                        )
                        if audit_log is not None:
                            audit_log.append(AuditEntry(
                                record_id=rec.record_id,
                                patient_id=rec.patient_id,
                                source_file=rec.source_file,
                                variable_code=rec.variable_code,
                                stage="UNIT_NORMALIZATION",
                                action="CONVERTED",
                                reason=reason,
                                original_value=f"{orig_val} {unit}",
                                corrected_value=f"{conv_val} {rule['canonical']}",
                                details={"rule": rule}
                            ))
                else:
                    rec.converted_value = None
            else:
                rec.canonical_unit = unit
                rec.converted_value = rec.value_numeric

        return records


class PlausibilityChecker:
    """
    Verifica si las mediciones clínicas se encuentran dentro de rangos biológicos plausibles
    según 05_metadata/variable_catalog.csv.
    """
    DEFAULT_RANGES = {
        "HR": (20.0, 220.0),
        "RR": (5.0, 60.0),
        "SpO2": (50.0, 100.0),
        "TEMP": (30.0, 45.0),
        "SBP": (60.0, 240.0),
        "DBP": (30.0, 150.0),
        "WEARABLE_HR": (20.0, 220.0),
        "STEPS": (0.0, 1000.0),
        "SIGNAL_QUALITY_INDEX": (0.0, 1.0),
        "LAB_A": (0.0, 50.0),
        "LAB_B": (0.0, 300.0),
        "LAB_C": (0.0, 10.0),
        "LAB_D": (0.0, 10.0)
    }

    def __init__(self, catalog_path: Optional[str] = None):
        self.ranges = dict(self.DEFAULT_RANGES)
        if catalog_path and os.path.exists(catalog_path):
            self._load_from_catalog(catalog_path)

    def _load_from_catalog(self, catalog_path: str):
        try:
            with open(catalog_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    v_code = row.get("variable_code")
                    p_min = row.get("plausibility_min")
                    p_max = row.get("plausibility_max")
                    if v_code and p_min and p_max:
                        self.ranges[v_code] = (float(p_min), float(p_max))
        except Exception:
            pass

    def check(
        self, records: List[CDMRecord], audit_log: Optional[List[AuditEntry]] = None
    ) -> List[CDMRecord]:
        for rec in records:
            v_code = rec.variable_code
            val = rec.converted_value if rec.converted_value is not None else rec.value_numeric

            # 1. Regla PL-01: Chequeo de rangos biológicos plausibles
            if v_code in self.ranges and val is not None:
                min_val, max_val = self.ranges[v_code]
                if val < min_val or val > max_val:
                    reason = f"Valor {val} fuera de rango biológico plausible [{min_val}, {max_val}] para {v_code}"
                    if rec.plausibility_status == "VALID":
                        rec.plausibility_status = "OUT_OF_RANGE"
                    rec.add_audit_entry(
                        stage="PLAUSIBILITY_CHECK",
                        action="FLAGGED",
                        reason=reason,
                        original_val=val,
                        new_val="OUT_OF_RANGE"
                    )
                    if audit_log is not None:
                        audit_log.append(AuditEntry(
                            record_id=rec.record_id,
                            patient_id=rec.patient_id,
                            source_file=rec.source_file,
                            variable_code=rec.variable_code,
                            stage="PLAUSIBILITY_CHECK",
                            action="FLAGGED",
                            reason=reason,
                            original_value=val,
                            corrected_value="OUT_OF_RANGE",
                            details={"plausibility_min": min_val, "plausibility_max": max_val}
                        ))

            # 2. Regla PL-02: Dosis de medicamentos positivas
            if rec.header_fields and "dose_value" in rec.header_fields:
                try:
                    dose_val = float(rec.header_fields["dose_value"])
                    if dose_val <= 0:
                        reason = f"Dosis de medicamento no positiva ({dose_val} <= 0) en {rec.record_id}"
                        rec.plausibility_status = "INVALID_MEDICATION_DOSE"
                        rec.add_audit_entry(stage="PLAUSIBILITY_CHECK", action="FLAGGED", reason=reason)
                        if audit_log is not None:
                            audit_log.append(AuditEntry(
                                record_id=rec.record_id,
                                patient_id=rec.patient_id,
                                source_file=rec.source_file,
                                variable_code=rec.variable_code or "DOSE",
                                stage="PLAUSIBILITY_CHECK",
                                action="FLAGGED",
                                reason=reason,
                                details={"rule": "PL-02", "dose_value": dose_val}
                            ))
                except (ValueError, TypeError):
                    pass

        return records
