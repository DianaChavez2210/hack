"""
Pruebas Unitarias para la Capa de Feature Engineering (features/).
HealthSignal LATAM — RISA Data V1.0.
"""

import pytest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from features.vital_features import VitalFeaturesExtractor
from features.feature_builder import FeatureBuilder


def test_vital_features_extractor():
    extractor = VitalFeaturesExtractor()
    t_decision = datetime(2026, 7, 10, 12, 0, 0)

    # Crear dataset sintético de signos vitales para paciente PAT-TEST
    df_vitals = pd.DataFrame([
        {"patient_id": "PAT-TEST", "variable_code": "HR", "converted_value": 70.0, "available_datetime": "2026-07-10 10:00:00"},
        {"patient_id": "PAT-TEST", "variable_code": "HR", "converted_value": 90.0, "available_datetime": "2026-07-10 11:05:00"},
        {"patient_id": "PAT-TEST", "variable_code": "HR", "converted_value": 110.0, "available_datetime": "2026-07-10 11:30:00"},
        {"patient_id": "PAT-TEST", "variable_code": "SBP", "converted_value": 100.0, "available_datetime": "2026-07-10 11:30:00"},
    ])

    feats = extractor.extract_features(df_vitals, "PAT-TEST", t_decision)

    assert "vital_HR_1h_mean" in feats
    assert feats["vital_HR_1h_mean"] == 100.0  # Promedio de lecturas en ventana 1h (11:05 y 11:30) = (90 + 110) / 2 = 100.0
    assert feats["vital_HR_6h_mean"] == 90.0   # Promedio de 70, 90, 110 = 90
    assert feats["vital_HR_6h_min"] == 70.0
    assert feats["vital_HR_6h_max"] == 110.0

    # Shock Index = HR_mean_24h / SBP_mean_24h = 90 / 100 = 0.90
    assert feats["vital_shock_index"] == 0.90


def test_feature_builder_integration(tmp_path):
    builder = FeatureBuilder()
    t_decision = datetime(2026, 7, 10, 12, 0, 0)

    df_vitals = pd.DataFrame([
        {"patient_id": "PAT-01", "variable_code": "HR", "converted_value": 80.0, "available_datetime": "2026-07-10 11:00:00"}
    ])
    df_empty = pd.DataFrame()

    feats = builder.build_features_for_patient(
        patient_id="PAT-01",
        decision_datetime=t_decision,
        vitals_df=df_vitals,
        wearables_df=df_empty,
        labs_df=df_empty,
        conditions_df=df_empty,
        patients_df=df_empty,
        context_df=df_empty
    )

    assert feats["patient_id"] == "PAT-01"
    assert "vital_HR_24h_mean" in feats
    assert feats["vital_HR_24h_mean"] == 80.0


if __name__ == "__main__":
    pytest.main([__file__])
