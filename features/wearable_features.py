"""
Submódulo de Extracción de Características para Telemetría y Wearables.
Agregaciones de frecuencia cardíaca de wearable, pasos, nivel de actividad y cruce con estado de sueño.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


class WearableFeaturesExtractor:
    """
    Extractor de características para datos de wearables y sensores portátiles.
    """
    WINDOWS_HOURS = [1, 6, 24]

    def _get_time_col(self, df: pd.DataFrame) -> str:
        for c in ["available_datetime", "event_datetime", "timestamp", "result_datetime"]:
            if c in df.columns:
                return c
        return df.columns[0]

    def extract_features(
        self,
        wearables_df: pd.DataFrame,
        context_df: pd.DataFrame,
        patient_id: str,
        decision_datetime: datetime
    ) -> Dict[str, float]:
        """
        Extrae características agregadas de wearables y su relación con estados contextuales.
        """
        features: Dict[str, float] = {}

        if wearables_df.empty:
            return self._empty_features()

        df_pat = wearables_df[wearables_df["patient_id"] == patient_id].copy()
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

        val_col = "converted_value" if "converted_value" in df_pat.columns and df_pat["converted_value"].notnull().any() else "value_numeric"
        if val_col not in df_pat.columns:
            val_col = "value"

        # 1. Agregaciones por ventana para WEARABLE_HR y STEPS
        for var in ["WEARABLE_HR", "STEPS", "ACTIVITY_LEVEL"]:
            df_var = df_pat[df_pat["variable_code"] == var]
            for w in self.WINDOWS_HOURS:
                cutoff = decision_datetime - timedelta(hours=w)
                sub_df = df_var[df_var["dt"] >= cutoff]
                prefix = f"wearable_{var.lower()}_{w}h"

                if sub_df.empty or val_col not in sub_df.columns:
                    features[f"{prefix}_mean"] = np.nan
                    features[f"{prefix}_sum"] = np.nan
                    features[f"{prefix}_max"] = np.nan
                else:
                    vals = pd.to_numeric(sub_df[val_col], errors="coerce").dropna().values
                    if len(vals) == 0:
                        features[f"{prefix}_mean"] = np.nan
                        features[f"{prefix}_sum"] = np.nan
                        features[f"{prefix}_max"] = np.nan
                    else:
                        features[f"{prefix}_mean"] = float(np.mean(vals))
                        features[f"{prefix}_sum"] = float(np.sum(vals))
                        features[f"{prefix}_max"] = float(np.max(vals))

        # 2. Cruce con Estados de Reposo / Sueño (patient_context.csv)
        sleep_hr_elevated = 0.0
        sleep_active_steps = 0.0

        if not context_df.empty:
            ctx_pat = context_df[context_df["patient_id"] == patient_id].copy()
            if not ctx_pat.empty:
                ctx_pat["s_dt"] = pd.to_datetime(ctx_pat["start_datetime"], errors="coerce")
                ctx_pat["e_dt"] = pd.to_datetime(ctx_pat["end_datetime"], errors="coerce")

                cutoff_24h = decision_datetime - timedelta(hours=24)
                ctx_24h = ctx_pat[(ctx_pat["s_dt"] <= decision_datetime) & (ctx_pat["e_dt"] >= cutoff_24h)]

                for _, ctx_row in ctx_24h.iterrows():
                    if ctx_row.get("context_value") == "SLEEP":
                        s_t = ctx_row["s_dt"]
                        e_t = ctx_row["e_dt"]
                        df_sleep_hr = df_pat[(df_pat["variable_code"] == "WEARABLE_HR") & (df_pat["dt"] >= s_t) & (df_pat["dt"] <= e_t)]
                        if not df_sleep_hr.empty and val_col in df_sleep_hr.columns:
                            vals_hr = pd.to_numeric(df_sleep_hr[val_col], errors="coerce").dropna()
                            if (vals_hr > 100.0).any():
                                sleep_hr_elevated = 1.0

                        df_sleep_steps = df_pat[(df_pat["variable_code"] == "STEPS") & (df_pat["dt"] >= s_t) & (df_pat["dt"] <= e_t)]
                        if not df_sleep_steps.empty and val_col in df_sleep_steps.columns:
                            vals_steps = pd.to_numeric(df_sleep_steps[val_col], errors="coerce").dropna()
                            if (vals_steps > 10.0).any():
                                sleep_active_steps = 1.0

        features["wearable_sleep_hr_anomaly"] = sleep_hr_elevated
        features["wearable_sleep_steps_anomaly"] = sleep_active_steps

        return features

    def _empty_features(self) -> Dict[str, float]:
        feats = {}
        for var in ["wearable_hr", "steps", "activity_level"]:
            for w in self.WINDOWS_HOURS:
                prefix = f"wearable_{var}_{w}h"
                feats[f"{prefix}_mean"] = np.nan
                feats[f"{prefix}_sum"] = np.nan
                feats[f"{prefix}_max"] = np.nan
        feats["wearable_sleep_hr_anomaly"] = 0.0
        feats["wearable_sleep_steps_anomaly"] = 0.0
        return feats
