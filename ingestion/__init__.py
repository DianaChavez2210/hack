"""
Módulo de Ingesta y Adaptadores de Salud - HealthSignal LATAM.
"""

from ingestion.models import RawRecord, CDMRecord, AuditEntry
from ingestion.base_adapter import BaseHospitalAdapter
from ingestion.factory import HospitalIngestionFactory
from ingestion.sinks import RawStorageSink, CleanStorageSink, AuditStorageSink
from ingestion.csv_adapter import RISACSVAdapter
from ingestion.mock_adapter import MockHospitalAdapter
from ingestion.orchestrator import IngestionOrchestrator

__all__ = [
    "RawRecord",
    "CDMRecord",
    "AuditEntry",
    "BaseHospitalAdapter",
    "HospitalIngestionFactory",
    "RawStorageSink",
    "CleanStorageSink",
    "AuditStorageSink",
    "RISACSVAdapter",
    "MockHospitalAdapter",
    "IngestionOrchestrator"
]
