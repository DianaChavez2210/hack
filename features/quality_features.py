"""
Submódulo de Extracción de Características de Calidad y Conectividad.
Ratios de missingness por variable en 6h y promedio de SIGNAL_QUALITY_INDEX.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


class QualityFeaturesExtractor:
    """
    Extractor de indicadores de calidad de datos, missingness y salud de la red de sensores.
    """
    TRACKED_VARS = ["HR", "RR", "SpO2", "TEMP", "SBP", "DBP", "WEARABLE_HR", "STEPS"]

    def _get_time_col(self, df: pd.DataFrame) -> str:
        for c in ["available_datetime", "event_datetime", "timestamp", "result_datetime", "sample_datetime"]:
            if c in df.columns:
                return c
        return df.columns[0]

    def extract_features(
        self,
        vitals_df: pd.DataFrame,
        wearables_df: pd.DataFrame,
        patient_id: str,
        decision_datetime: datetime
    ) -> Dict[str, float]:
        """
        Extrae ratios de datos faltantes y calidad de señal.
        """
        features: Dict[str, float] = {}
        cutoff_6h = decision_datetime - timedelta(hours=6)

        combined_dfs = []
        if not vitals_df.empty:
            df_v = vitals_df[vitals_df["patient_id"] == patient_id]
            if not df_v.empty:
                combined_dfs.append(df_v)
        if not wearables_df.empty:
            df_w = wearables_df[wearables_df["patient_id"] == patient_id]
            if not df_w.empty:
                combined_dfs.append(df_w)

        if not combined_dfs:
            return self._empty_features()

        df_all = pd.concat(combined_dfs, ignore_index=True)
        col_time = self._get_time_col(df_all)
        if pd.api.types.is_datetime64_any_dtype(df_all[col_time]):
            df_all["dt"] = df_all[col_time]
        else:
            df_all["dt"] = pd.to_datetime(df_all[col_time], format="mixed", errors="coerce")
        df_6h = df_all[(df_all["dt"] <= decision_datetime) & (df_all["dt"] >= cutoff_6h)]

        if df_6h.empty:
            return self._empty_features()

        col_var = "variable_code"
        col_q = "signal_quality"

        for var in self.TRACKED_VARS:
            if col_var in df_6h.columns:
                df_var = df_6h[df_6h[col_var] == var]
                count = len(df_var)
            else:
                count = 0
            expected = 6.0
            missing_ratio = max(0.0, min(1.0, 1.0 - (count / expected)))
            features[f"quality_missing_ratio_6h_{var.lower()}"] = float(missing_ratio)

        if col_q in df_6h.columns:
            q_vals = pd.to_numeric(df_6h[col_q], errors="coerce").dropna().values
            if len(q_vals) > 0:
                features["quality_avg_signal_index"] = float(np.mean(q_vals))
            else:
                features["quality_avg_signal_index"] = 1.0
        else:
            features["quality_avg_signal_index"] = 1.0

        return features

    def _empty_features(self) -> Dict[str, float]:
        feats = {}
        for var in self.TRACKED_VARS:
            feats[f"quality_missing_ratio_6h_{var.lower()}"] = 1.0
        feats["quality_avg_signal_index"] = 1.0
        return feats
