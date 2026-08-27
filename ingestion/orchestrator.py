"""
Orquestador Principal de Ingesta (IngestionOrchestrator).
Coordina la extracción por adaptador, persistencia en capa RAW, mapeo a CDM,
ejecución secuencial del pipeline de calidad y guardado en capa CLEAN.
"""

from typing import Dict, Any, Optional, List
from collections import Counter
from ingestion.models import AuditEntry
from ingestion.factory import HospitalIngestionFactory
from ingestion.sinks import RawStorageSink, CleanStorageSink, AuditStorageSink
from pipeline.validation import SchemaValidator
from pipeline.cleaning import DataCleaner
from pipeline.normalization import UnitNormalizer, PlausibilityChecker
from pipeline.temporal import TemporalProcessor
from pipeline.contextualizer import Contextualizer


class IngestionOrchestrator:
    """
    Orquestador desacoplado para flujos de ingesta y normalización.
    Registra el porqué de cada decisión de calidad, corrección y descarte.
    """
    def __init__(
        self,
        raw_sink: Optional[RawStorageSink] = None,
        clean_sink: Optional[CleanStorageSink] = None,
        audit_sink: Optional[AuditStorageSink] = None,
        units_catalog_path: Optional[str] = None,
        variable_catalog_path: Optional[str] = None
    ):
        self.raw_sink = raw_sink or RawStorageSink()
        self.clean_sink = clean_sink or CleanStorageSink()
        self.audit_sink = audit_sink or AuditStorageSink()
        
        # Inicializar etapas del pipeline común
        self.validator = SchemaValidator(reject_invalid=False)
        self.cleaner = DataCleaner(drop_duplicates=True)
        self.unit_normalizer = UnitNormalizer(catalog_path=units_catalog_path)
        self.plausibility_checker = PlausibilityChecker(catalog_path=variable_catalog_path)
        self.temporal_processor = TemporalProcessor()
        self.contextualizer = Contextualizer()

    def process_and_save(
        self,
        source_type: str,
        hospital_id: str,
        source_config: Dict[str, Any],
        dataset_name: str = "clean_records"
    ) -> Dict[str, Any]:
        """
        Ejecuta el flujo completo para una fuente de datos con registro de auditoría de calidad.
        """
        # Contenedor de decisiones de calidad para esta ejecución
        audit_log: List[AuditEntry] = []

        # 1. Obtener adaptador correspondiente mediante Factory
        adapter = HospitalIngestionFactory.get_adapter(
            source_type=source_type,
            hospital_id=hospital_id
        )

        # 2. Extracción y Guardado en RAW Inmutable
        raw_records = adapter.extract_raw(source_config)
        raw_file_path = self.raw_sink.save_records(
            raw_records,
            partition_name=f"raw_{dataset_name}"
        )

        # 3. Mapeo a Common Data Model (CDM)
        cdm_records = adapter.map_to_cdm(raw_records)

        # 4. Pipeline de Calidad y Limpieza (cada etapa registra sus decisiones)
        # 4.1 Validación de esquema
        valid_records, invalid_records = self.validator.validate(cdm_records, audit_log=audit_log)
        # 4.2 Limpieza, deduplicación y missingness no destructivo
        cleaned_records = self.cleaner.clean(valid_records, audit_log=audit_log)
        # 4.3 Normalización de unidades
        normalized_records = self.unit_normalizer.normalize(cleaned_records, audit_log=audit_log)
        # 4.4 Chequeo de plausibilidad biológica
        checked_records = self.plausibility_checker.check(normalized_records, audit_log=audit_log)
        # 4.5 Procesamiento temporal y latencias
        temporal_records = self.temporal_processor.process(checked_records)
        # 4.6 Contextualización
        final_records = self.contextualizer.contextualize(temporal_records, audit_log=audit_log)

        # 5. Persistencia en Capa CLEAN (Subcarpetas jsonl/ y csv/)
        clean_file_path = self.clean_sink.save_records(
            final_records,
            dataset_name=dataset_name
        )

        clean_jsonl_path = str(self.clean_sink.jsonl_dir / f"{dataset_name}.jsonl")
        clean_csv_path = str(self.clean_sink.csv_dir / f"{dataset_name}.csv")

        # 6. Persistencia de Registro de Calidad e Incidencias en Archivo .log
        audit_file_path = self.audit_sink.save_audit_entries(
            audit_log,
            log_name="ingestion_processing"
        )

        # Resumen de decisiones tomadas
        action_summary = dict(Counter(e.action for e in audit_log))
        stage_summary = dict(Counter(e.stage for e in audit_log))

        return {
            "hospital_id": hospital_id,
            "source_type": source_type,
            "raw_count": len(raw_records),
            "invalid_schema_count": len(invalid_records),
            "clean_count": len(final_records),
            "audit_entries_count": len(audit_log),
            "audit_actions": action_summary,
            "audit_stages": stage_summary,
            "raw_path": raw_file_path,
            "clean_path": clean_file_path,
            "clean_jsonl_path": clean_jsonl_path,
            "clean_csv_path": clean_csv_path,
            "audit_path": audit_file_path,
            "status": "SUCCESS"
        }
