"""
Modelos de Datos para el Sistema de Ingesta HealthSignal LATAM (RISA Data V1.0).
Define las estructuras inmutables para la capa RAW y el Common Data Model (CDM).
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class RawRecord:
    """
    Representa una carga inmutable de datos tal como se extrae de la institución de origen.
    Garantiza la auditabilidad y preservación del payload original antes de cualquier transformación.
    """
    record_id: str
    source_file: str
    facility_id: Optional[str] = None
    ingestion_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    raw_payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RawRecord":
        return cls(**data)


@dataclass
class CDMRecord:
    """
    Common Data Model (CDM) canónico para RISA Data V1.0.
    Estandariza observaciones de signos vitales, laboratorio, wearables y telemetría.
    """
    # Identificadores de Integridad Referencial
    record_id: str
    patient_id: str
    source_file: str
    encounter_id: Optional[str] = None
    facility_id: Optional[str] = None
    device_id: Optional[str] = None
    source_system: Optional[str] = None

    # Variable y Medición
    variable_code: str = ""
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    original_unit: Optional[str] = None
    canonical_unit: Optional[str] = None
    converted_value: Optional[float] = None

    # Semántica Temporal (Anti-Temporal Leakage)
    event_datetime: Optional[str] = None       # T_event (momento fisiológico o toma de muestra)
    available_datetime: Optional[str] = None   # T_available (disponibilidad en sistema / sync)
    latency_seconds: Optional[float] = None

    # Calidad de Datos, Missingness y Auditoría
    is_observed: bool = True                   # Missing != 0 (indica si el valor fue observado)
    is_imputed: bool = False                   # Indica si el valor fue estimado
    imputation_method: Optional[str] = None    # Método de imputación justificado si aplica
    quality_flag: str = "OK"                   # OK, NOISE, ARTIFACT, etc.
    signal_quality: Optional[float] = None     # Calidad de señal (0.0 a 1.0)
    is_retransmission: bool = False            # True si proviene de MONITOR_RETRANSMIT
    plausibility_status: str = "VALID"         # VALID, OUT_OF_RANGE, SUSPICIOUS, UNRELIABLE_DEVICE, etc.
    header_fields: Dict[str, Any] = field(default_factory=dict) # Mapeo completo de la cabecera original
    null_fields: list = field(default_factory=list) # Lista de campos que contienen valores nulos/vacíos
    context_info: Dict[str, Any] = field(default_factory=dict) # Metadata adicional (sueño, conectividad)
    audit_trail: list = field(default_factory=list) # Registro cronológico de transformaciones del registro

    def add_audit_entry(self, stage: str, action: str, reason: str, original_val: Any = None, new_val: Any = None):
        self.audit_trail.append({
            "timestamp": datetime.utcnow().isoformat(),
            "stage": stage,
            "action": action,
            "reason": reason,
            "original_value": original_val,
            "corrected_value": new_val
        })

    def to_dict(self) -> Dict[str, Any]:
        base = asdict(self)
        if self.header_fields:
            # Preservar la estructura exacta de la cabecera original como claves principales,
            # complementada con los indicadores de calidad estandarizados.
            merged = dict(self.header_fields)
            merged.update({
                "is_observed": self.is_observed,
                "quality_flag": self.quality_flag,
                "plausibility_status": self.plausibility_status,
                "signal_quality": self.signal_quality,
                "is_retransmission": self.is_retransmission,
                "null_fields": self.null_fields
            })
            return merged
        return base

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDMRecord":
        return cls(**data)


@dataclass
class AuditEntry:
    """
    Entrada del registro de auditoría de calidad de datos.
    Permite inspeccionar por qué se decidió eliminar, corregir o marcar cualquier dato.
    """
    record_id: str
    patient_id: str
    source_file: str
    variable_code: str
    stage: str                  # SCHEMA_VALIDATION, DEDUPLICATION, MISSINGNESS, UNIT_NORMALIZATION, PLAUSIBILITY_CHECK, CONTEXT, LEAKAGE_GUARD
    action: str                 # DISCARDED, FLAGGED, CONVERTED, PRESERVED_MISSING, LEAKAGE_BLOCKED
    reason: str                 # Explicación del criterio aplicado
    original_value: Optional[Any] = None
    corrected_value: Optional[Any] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        return cls(**data)

