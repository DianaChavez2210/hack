"""
Submódulo de Extracción de Características Temporales (Recency).
Calcula los minutos transcurridos desde el último registro de cada variable clave hasta T_decision.
"""

from typing import List, Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class TemporalFeaturesExtractor:
    """
    Extractor de características temporales de recency por variable.
    """
    TRACKED_VARS = ["HR", "RR", "SpO2", "TEMP", "SBP", "DBP", "WEARABLE_HR", "STEPS", "WBC", "GLUCOSE"]

    def _get_time_col(self, df: pd.DataFrame) -> str:
        for c in ["available_datetime", "event_datetime", "timestamp", "result_datetime", "sample_datetime"]:
            if c in df.columns:
                return c
        return df.columns[0]

    def extract_features(
        self,
        all_records_df: pd.DataFrame,
        patient_id: str,
        decision_datetime: datetime
    ) -> Dict[str, float]:
        """
        Calcula minutos desde el último evento por variable.
        """
        features: Dict[str, float] = {}

        if all_records_df.empty:
            return self._empty_features()

        df_pat = all_records_df[all_records_df["patient_id"] == patient_id].copy()
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

        col_var = "variable_code" if "variable_code" in df_pat.columns else "test_code"

        for var in self.TRACKED_VARS:
            if col_var in df_pat.columns:
                df_var = df_pat[df_pat[col_var] == var]
            else:
                df_var = pd.DataFrame()

            prefix = f"recency_{var.lower()}_mins"

            if df_var.empty:
                features[prefix] = 99999.0
            else:
                last_dt = df_var["dt"].iloc[-1]
                if pd.notnull(last_dt):
                    delta_mins = (decision_datetime - last_dt).total_seconds() / 60.0
                    features[prefix] = max(0.0, float(delta_mins))
                else:
                    features[prefix] = 99999.0

        return features

    def _empty_features(self) -> Dict[str, float]:
        feats = {}
        for var in self.TRACKED_VARS:
            feats[f"recency_{var.lower()}_mins"] = 99999.0
        return feats
