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
        from pipeline.validation import SchemaValidator
        from pipeline.cleaning import DataCleaner
        from pipeline.normalization import UnitNormalizer, PlausibilityChecker
        from pipeline.temporal import TemporalProcessor
        from pipeline.contextualizer import Contextualizer
        from pipeline.integrity import SystemIntegrityValidator

        self.raw_sink = raw_sink or RawStorageSink()
        self.clean_sink = clean_sink or CleanStorageSink()
        self.audit_sink = audit_sink or AuditStorageSink()

        # Inicializar etapas del pipeline común
        self.validator = SchemaValidator(reject_invalid=False)
        self.cleaner = DataCleaner(drop_duplicates=True)
        self.unit_normalizer = UnitNormalizer(catalog_path=units_catalog_path)
        self.plausibility_checker = PlausibilityChecker(catalog_path=variable_catalog_path)
        self.integrity_validator = SystemIntegrityValidator()
        self.temporal_processor = TemporalProcessor()
        self.contextualizer = Contextualizer()

    def set_master_context(
        self,
        patients_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        encounters_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        devices_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        patient_contexts: Optional[List[Dict[str, Any]]] = None,
        connectivity_events: Optional[List[Dict[str, Any]]] = None
    ):
        """Inyecta contexto maestro global para validación referencial y cruzada entre dominios."""
        self.integrity_validator.set_master_context(
            patients_dict=patients_dict,
            encounters_dict=encounters_dict,
            devices_dict=devices_dict
        )
        if encounters_dict:
            self.temporal_processor.set_encounters_dict(encounters_dict)
        if patient_contexts or connectivity_events:
            self.contextualizer.set_context(
                patient_contexts=patient_contexts,
                connectivity_events=connectivity_events
            )

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
        # 4.4 Chequeo de plausibilidad biológica y dosis
        checked_records = self.plausibility_checker.check(normalized_records, audit_log=audit_log)
        # 4.5 Validación de Integridad Referencial y Relacional Cruzada (13 reglas)
        integrity_records = self.integrity_validator.validate(checked_records, audit_log=audit_log)
        # 4.6 Procesamiento temporal y latencias
        temporal_records = self.temporal_processor.process(integrity_records, audit_log=audit_log)
        # 4.7 Contextualización operacional y de red
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
            log_name="ingestion_processing",
            append=True
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

    def process_and_save_stream(
        self,
        source_type: str,
        hospital_id: str,
        source_config: Dict[str, Any],
        dataset_name: str = "clean_records",
        chunk_size: int = 50000
    ) -> Dict[str, Any]:
        """
        Ejecuta la ingesta en streaming por lotes (chunk_size=50,000) procesando
        y guardando incrementalmente sin sobrecargar la memoria RAM ni el hardware.
        """
        adapter = HospitalIngestionFactory.get_adapter(
            source_type=source_type,
            hospital_id=hospital_id
        )

        total_raw_count = 0
        total_invalid_schema_count = 0
        total_clean_count = 0
        total_audit_entries_count = 0
        global_audit_log: List[AuditEntry] = []

        chunk_generator = getattr(adapter, "extract_raw_chunks", None)
        if chunk_generator is None:
            return self.process_and_save(
                source_type=source_type,
                hospital_id=hospital_id,
                source_config=source_config,
                dataset_name=dataset_name
            )

        chunk_index = 0
        raw_file_path = ""
        clean_file_path = ""
        audit_file_path = ""

        for raw_chunk in chunk_generator(source_config, chunk_size=chunk_size):
            is_append = (chunk_index > 0)
            chunk_audit_log: List[AuditEntry] = []

            # 1. Guardar chunk en RAW Inmutable
            raw_file_path = self.raw_sink.save_records(
                raw_chunk,
                partition_name=f"raw_{dataset_name}",
                append=is_append
            )

            # 2. Mapeo a CDM
            cdm_chunk = adapter.map_to_cdm(raw_chunk)

            # 3. Pipeline de Calidad y 13 Reglas de Integridad
            valid_records, invalid_records = self.validator.validate(cdm_chunk, audit_log=chunk_audit_log)
            cleaned_records = self.cleaner.clean(valid_records, audit_log=chunk_audit_log)
            normalized_records = self.unit_normalizer.normalize(cleaned_records, audit_log=chunk_audit_log)
            checked_records = self.plausibility_checker.check(normalized_records, audit_log=chunk_audit_log)
            integrity_records = self.integrity_validator.validate(checked_records, audit_log=chunk_audit_log)
            temporal_records = self.temporal_processor.process(integrity_records, audit_log=chunk_audit_log)
            final_records = self.contextualizer.contextualize(temporal_records, audit_log=chunk_audit_log)

            # 4. Guardar chunk limpio en JSONL y CSV
            clean_file_path = self.clean_sink.save_records(
                final_records,
                dataset_name=dataset_name,
                append=is_append
            )

            # 5. Guardar incidencias de auditoría del chunk
            if chunk_audit_log:
                audit_file_path = self.audit_sink.save_audit_entries(
                    chunk_audit_log,
                    log_name="ingestion_processing",
                    append=True
                )
                global_audit_log.extend(chunk_audit_log)

            total_raw_count += len(raw_chunk)
            total_invalid_schema_count += len(invalid_records)
            total_clean_count += len(final_records)
            total_audit_entries_count += len(chunk_audit_log)
            chunk_index += 1

        clean_jsonl_path = str(self.clean_sink.jsonl_dir / f"{dataset_name}.jsonl")
        clean_csv_path = str(self.clean_sink.csv_dir / f"{dataset_name}.csv")

        action_summary = dict(Counter(e.action for e in global_audit_log))
        stage_summary = dict(Counter(e.stage for e in global_audit_log))

        return {
            "hospital_id": hospital_id,
            "source_type": source_type,
            "raw_count": total_raw_count,
            "invalid_schema_count": total_invalid_schema_count,
            "clean_count": total_clean_count,
            "chunks_processed": chunk_index,
            "audit_entries_count": total_audit_entries_count,
            "audit_actions": action_summary,
            "audit_stages": stage_summary,
            "raw_path": raw_file_path,
            "clean_path": clean_file_path,
            "clean_jsonl_path": clean_jsonl_path,
            "clean_csv_path": clean_csv_path,
            "audit_path": audit_file_path,
            "status": "SUCCESS"
        }

    def process_and_save_parallel(
        self,
        source_type: str,
        hospital_id: str,
        source_config: Dict[str, Any],
        dataset_name: str = "clean_records",
        chunk_size: int = 50000,
        max_workers: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta la ingesta acelerada mediante procesamiento paralelo multinúcleo (ProcessPoolExecutor).
        """
        import os
        from concurrent.futures import ProcessPoolExecutor, as_completed

        adapter = HospitalIngestionFactory.get_adapter(
            source_type=source_type,
            hospital_id=hospital_id
        )

        chunk_generator = getattr(adapter, "extract_raw_chunks", None)
        if chunk_generator is None:
            return self.process_and_save(
                source_type=source_type,
                hospital_id=hospital_id,
                source_config=source_config,
                dataset_name=dataset_name
            )

        num_workers = max_workers or max(1, os.cpu_count() or 4)

        master_ctx_dict = {
            "patients_dict": getattr(self.integrity_validator, "patients_dict", {}),
            "encounters_dict": getattr(self.integrity_validator, "encounters_dict", {}),
            "devices_dict": getattr(self.integrity_validator, "devices_dict", {}),
            "patient_contexts": getattr(self.contextualizer, "patient_contexts", []),
            "connectivity_events": getattr(self.contextualizer, "connectivity_events", [])
        }

        total_raw_count = 0
        total_invalid_schema_count = 0
        total_clean_count = 0
        total_audit_entries_count = 0
        global_audit_log: List[AuditEntry] = []

        chunk_index = 0
        raw_file_path = ""
        clean_file_path = ""
        audit_file_path = ""

        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            future_to_chunk_idx = {}
            for raw_chunk in chunk_generator(source_config, chunk_size=chunk_size):
                task_args = (
                    raw_chunk,
                    source_type,
                    hospital_id,
                    master_ctx_dict,
                    getattr(self.unit_normalizer, "catalog_path", None),
                    getattr(self.plausibility_checker, "catalog_path", None)
                )
                future = executor.submit(_process_chunk_worker, task_args)
                future_to_chunk_idx[future] = (chunk_index, raw_chunk)
                chunk_index += 1

            for future in as_completed(future_to_chunk_idx):
                idx, raw_chunk = future_to_chunk_idx[future]
                final_records, chunk_audit_log, invalid_count = future.result()

                is_append = (idx > 0 or total_raw_count > 0)
                
                # 1. Guardar chunk en RAW Inmutable
                raw_file_path = self.raw_sink.save_records(
                    raw_chunk,
                    partition_name=f"raw_{dataset_name}",
                    append=is_append
                )

                # 2. Guardar chunk limpio en JSONL y CSV
                clean_file_path = self.clean_sink.save_records(
                    final_records,
                    dataset_name=dataset_name,
                    append=is_append
                )

                # 3. Persistir auditoría
                if chunk_audit_log:
                    audit_file_path = self.audit_sink.save_audit_entries(
                        chunk_audit_log,
                        log_name="ingestion_processing",
                        append=True
                    )
                    global_audit_log.extend(chunk_audit_log)

                total_raw_count += len(raw_chunk)
                total_invalid_schema_count += invalid_count
                total_clean_count += len(final_records)
                total_audit_entries_count += len(chunk_audit_log)

        clean_jsonl_path = str(self.clean_sink.jsonl_dir / f"{dataset_name}.jsonl")
        clean_csv_path = str(self.clean_sink.csv_dir / f"{dataset_name}.csv")

        action_summary = dict(Counter(e.action for e in global_audit_log))
        stage_summary = dict(Counter(e.stage for e in global_audit_log))

        return {
            "hospital_id": hospital_id,
            "source_type": source_type,
            "raw_count": total_raw_count,
            "invalid_schema_count": total_invalid_schema_count,
            "clean_count": total_clean_count,
            "chunks_processed": chunk_index,
            "workers_used": num_workers,
            "audit_entries_count": total_audit_entries_count,
            "audit_actions": action_summary,
            "audit_stages": stage_summary,
            "raw_path": raw_file_path,
            "clean_path": clean_file_path,
            "clean_jsonl_path": clean_jsonl_path,
            "clean_csv_path": clean_csv_path,
            "audit_path": audit_file_path,
            "status": "SUCCESS"
        }


def _process_chunk_worker(args):
    """
    Función de trabajo aislada y serializable (multiprocessing worker).
    Procesa un chunk de datos de forma paralela en un núcleo de CPU.
    """
    raw_chunk, source_type, hospital_id, master_ctx_dict, units_catalog_path, variable_catalog_path = args

    from pipeline.validation import SchemaValidator
    from pipeline.cleaning import DataCleaner
    from pipeline.normalization import UnitNormalizer, PlausibilityChecker
    from pipeline.temporal import TemporalProcessor
    from pipeline.contextualizer import Contextualizer
    from pipeline.integrity import SystemIntegrityValidator
    from ingestion.factory import HospitalIngestionFactory

    adapter = HospitalIngestionFactory.get_adapter(source_type=source_type, hospital_id=hospital_id)
    cdm_chunk = adapter.map_to_cdm(raw_chunk)

    validator = SchemaValidator(reject_invalid=False)
    cleaner = DataCleaner(drop_duplicates=True)
    unit_normalizer = UnitNormalizer(catalog_path=units_catalog_path)
    plausibility_checker = PlausibilityChecker(catalog_path=variable_catalog_path)
    integrity_validator = SystemIntegrityValidator()
    temporal_processor = TemporalProcessor()
    contextualizer = Contextualizer()

    if master_ctx_dict:
        integrity_validator.set_master_context(
            patients_dict=master_ctx_dict.get("patients_dict"),
            encounters_dict=master_ctx_dict.get("encounters_dict"),
            devices_dict=master_ctx_dict.get("devices_dict")
        )
        if master_ctx_dict.get("encounters_dict"):
            temporal_processor.set_encounters_dict(master_ctx_dict["encounters_dict"])
        if master_ctx_dict.get("patient_contexts") or master_ctx_dict.get("connectivity_events"):
            contextualizer.set_context(
                patient_contexts=master_ctx_dict.get("patient_contexts"),
                connectivity_events=master_ctx_dict.get("connectivity_events")
            )

    chunk_audit_log = []
    valid_records, invalid_records = validator.validate(cdm_chunk, audit_log=chunk_audit_log)
    cleaned_records = cleaner.clean(valid_records, audit_log=chunk_audit_log)
    normalized_records = unit_normalizer.normalize(cleaned_records, audit_log=chunk_audit_log)
    checked_records = plausibility_checker.check(normalized_records, audit_log=chunk_audit_log)
    integrity_records = integrity_validator.validate(checked_records, audit_log=chunk_audit_log)
    temporal_records = temporal_processor.process(integrity_records, audit_log=chunk_audit_log)
    final_records = contextualizer.contextualize(temporal_records, audit_log=chunk_audit_log)

    return (final_records, chunk_audit_log, len(invalid_records))
