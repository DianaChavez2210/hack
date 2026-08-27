"""
Submódulo de Extracción de Características para Analíticas de Laboratorio.
Extrae el último valor disponible de laboratorio antes de T_decision, desviaciones respecto a rangos de referencia y antigüedad.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class LabFeaturesExtractor:
    """
    Extractor de características para analíticas de laboratorio clínico.
    """
    LAB_TESTS = ["WBC", "CREATININE", "LACTATE", "HEMOGLOBIN", "PLATELETS", "CRP", "BUN", "GLUCOSE"]

    def _get_time_col(self, df: pd.DataFrame) -> str:
        for c in ["available_datetime", "result_datetime", "event_datetime", "timestamp", "sample_datetime"]:
            if c in df.columns:
                return c
        return df.columns[0]

    def extract_features(
        self,
        lab_df: pd.DataFrame,
        patient_id: str,
        decision_datetime: datetime
    ) -> Dict[str, float]:
        """
        Extrae el último resultado disponible de laboratorio por analítica y calcula desviaciones respecto a rangos.
        """
        features: Dict[str, float] = {}

        if lab_df.empty:
            return self._empty_features()

        df_pat = lab_df[lab_df["patient_id"] == patient_id].copy()
        if df_pat.empty:
            return self._empty_features()

        col_time = self._get_time_col(df_pat)
        if pd.api.types.is_datetime64_any_dtype(df_pat[col_time]):
            df_pat["dt"] = df_pat[col_time]
        else:
            df_pat["dt"] = pd.to_datetime(df_pat[col_time], format="mixed", errors="coerce")
        df_pat = df_pat[df_pat["dt"] <= decision_datetime].sort_values("dt")

        if df_pat.empty:
            return self._empty_features()

        val_col = "converted_value" if "converted_value" in df_pat.columns and df_pat["converted_value"].notnull().any() else "result_value"
        if val_col not in df_pat.columns:
            val_col = "value_numeric"
        if val_col not in df_pat.columns:
            val_col = "value"

        code_col = "test_code" if "test_code" in df_pat.columns else "variable_code"

        for test_code in self.LAB_TESTS:
            if code_col in df_pat.columns:
                df_test = df_pat[df_pat[code_col] == test_code]
            else:
                df_test = pd.DataFrame()

            prefix = f"lab_{test_code.lower()}"

            if df_test.empty:
                features[f"{prefix}_latest"] = np.nan
                features[f"{prefix}_abnormal_flag"] = 0.0
                features[f"{prefix}_hours_ago"] = np.nan
            else:
                latest_row = df_test.iloc[-1]
                val = pd.to_numeric(latest_row.get(val_col), errors="coerce")
                dt_result = latest_row["dt"]

                features[f"{prefix}_latest"] = float(val) if pd.notnull(val) else np.nan

                if pd.notnull(dt_result):
                    hours_ago = (decision_datetime - dt_result).total_seconds() / 3600.0
                    features[f"{prefix}_hours_ago"] = max(0.0, float(hours_ago))
                else:
                    features[f"{prefix}_hours_ago"] = np.nan

                ref_low = pd.to_numeric(latest_row.get("reference_low"), errors="coerce")
                ref_high = pd.to_numeric(latest_row.get("reference_high"), errors="coerce")

                is_abnormal = 0.0
                if pd.notnull(val):
                    if pd.notnull(ref_low) and val < ref_low:
                        is_abnormal = 1.0
                    elif pd.notnull(ref_high) and val > ref_high:
                        is_abnormal = 1.0

                features[f"{prefix}_abnormal_flag"] = is_abnormal

        return features

    def _empty_features(self) -> Dict[str, float]:
        feats = {}
        for test_code in self.LAB_TESTS:
            prefix = f"lab_{test_code.lower()}"
            feats[f"{prefix}_latest"] = np.nan
            feats[f"{prefix}_abnormal_flag"] = 0.0
            feats[f"{prefix}_hours_ago"] = np.nan
        return feats
