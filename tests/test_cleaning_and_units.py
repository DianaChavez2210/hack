"""
Pruebas Unitarias para Limpieza de Datos, Missingness, Normalización de Unidades y Plausibilidad.
"""

import sys
from pathlib import Path

# Agregar raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from ingestion.models import CDMRecord
from pipeline.cleaning import DataCleaner
from pipeline.normalization import UnitNormalizer, PlausibilityChecker


def test_missingness_preservation_not_zero():
    """Verifica que missing no sea convertido a cero y se marque is_observed = False."""
    cleaner = DataCleaner()
    rec_null = CDMRecord(
        record_id="REC_NULL_01",
        patient_id="PAT-0001",
        source_file="vitals.csv",
        variable_code="HR",
        value_numeric=None,
        value_text=None,
        event_datetime="2026-07-10 09:00:00"
    )

    cleaned = cleaner.clean([rec_null])
    assert len(cleaned) == 1
    assert cleaned[0].value_numeric is None
    assert cleaned[0].is_observed is False
    assert cleaned[0].value_numeric != 0.0


def test_deduplication():
    """Verifica la deduplicación por clave única (record_id, source_file)."""
    cleaner = DataCleaner(drop_duplicates=True)
    rec1 = CDMRecord(record_id="REC_DUP", patient_id="PAT-0001", source_file="vitals.csv", variable_code="HR", value_numeric=70.0, event_datetime="2026-07-10 09:00:00")
    rec2 = CDMRecord(record_id="REC_DUP", patient_id="PAT-0001", source_file="vitals.csv", variable_code="HR", value_numeric=75.0, event_datetime="2026-07-10 09:00:00")
    
    cleaned = cleaner.clean([rec1, rec2])
    assert len(cleaned) == 1
    assert cleaned[0].record_id == "REC_DUP"


def test_unit_normalization_degf_to_degc():
    """Verifica la conversión matemática de Fahrenheit a Celsius."""
    normalizer = UnitNormalizer()
    rec_temp = CDMRecord(
        record_id="REC_TEMP",
        patient_id="PAT-0001",
        source_file="vitals.csv",
        variable_code="TEMP",
        value_numeric=98.6,
        original_unit="degF",
        event_datetime="2026-07-10 09:00:00"
    )

    normalized = normalizer.normalize([rec_temp])
    assert normalized[0].canonical_unit == "degC"
    assert normalized[0].converted_value is not None
    # 98.6 F -> ~37.0 C
    assert abs(normalized[0].converted_value - 37.0) < 0.1


def test_plausibility_checker():
    """Verifica que valores biológicamente extremos se marquen como OUT_OF_RANGE sin descartarse."""
    checker = PlausibilityChecker()
    rec_out = CDMRecord(
        record_id="REC_EXTREME",
        patient_id="PAT-0001",
        source_file="vitals.csv",
        variable_code="HR",
        value_numeric=350.0, # Implausible
        event_datetime="2026-07-10 09:00:00"
    )

    checked = checker.check([rec_out])
    assert len(checked) == 1
    assert checked[0].plausibility_status == "OUT_OF_RANGE"


if __name__ == "__main__":
    test_missingness_preservation_not_zero()
    test_deduplication()
    test_unit_normalization_degf_to_degc()
    test_plausibility_checker()
    print("[OK] Todos los tests de limpieza y unidades pasaron correctamente.")
