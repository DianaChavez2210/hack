"""
Submódulo de Extracción de Características para Signos Vitales.
Soporta ventanas móviles W in {1h, 6h, 24h}, estadísticos, pendientes y Shock Index.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


class VitalFeaturesExtractor:
    """
    Extractor de características de signos vitales en ventanas temporales.
    """
    VITAL_VARS = ["HR", "RR", "SpO2", "TEMP", "SBP", "DBP"]
    WINDOWS_HOURS = [1, 6, 24]

    def _get_time_col(self, df: pd.DataFrame) -> str:
        for c in ["available_datetime", "event_datetime", "timestamp", "result_datetime"]:
            if c in df.columns:
                return c
        return df.columns[0]

    def extract_features(
        self,
        vitals_df: pd.DataFrame,
        patient_id: str,
        decision_datetime: datetime
    ) -> Dict[str, float]:
        """
        Extrae el vector de características de signos vitales para un paciente hasta decision_datetime.
        """
        features: Dict[str, float] = {}

        if vitals_df.empty:
            return self._empty_features()

        df_pat = vitals_df[vitals_df["patient_id"] == patient_id].copy()
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

        for var in self.VITAL_VARS:
            df_var = df_pat[df_pat["variable_code"] == var].copy()
            val_col = "converted_value" if "converted_value" in df_var.columns and df_var["converted_value"].notnull().any() else "value_numeric"
            if val_col not in df_var.columns:
                val_col = "value"

            for w_hours in self.WINDOWS_HOURS:
                cutoff = decision_datetime - timedelta(hours=w_hours)
                sub_df = df_var[df_var["dt"] >= cutoff]
                prefix = f"vital_{var}_{w_hours}h"

                if sub_df.empty or val_col not in sub_df.columns:
                    features[f"{prefix}_mean"] = np.nan
                    features[f"{prefix}_min"] = np.nan
                    features[f"{prefix}_max"] = np.nan
                    features[f"{prefix}_std"] = np.nan
                    features[f"{prefix}_slope"] = np.nan
                else:
                    vals = pd.to_numeric(sub_df[val_col], errors="coerce").dropna().values
                    if len(vals) == 0:
                        features[f"{prefix}_mean"] = np.nan
                        features[f"{prefix}_min"] = np.nan
                        features[f"{prefix}_max"] = np.nan
                        features[f"{prefix}_std"] = np.nan
                        features[f"{prefix}_slope"] = np.nan
                    else:
                        features[f"{prefix}_mean"] = float(np.mean(vals))
                        features[f"{prefix}_min"] = float(np.min(vals))
                        features[f"{prefix}_max"] = float(np.max(vals))
                        features[f"{prefix}_std"] = float(np.std(vals)) if len(vals) > 1 else 0.0

                        # Pendiente Delta valor / Delta tiempo (horas)
                        if len(vals) > 1:
                            times_h = (sub_df["dt"] - sub_df["dt"].iloc[0]).dt.total_seconds() / 3600.0
                            t_vals = times_h.values
                            if len(t_vals) == len(vals) and (t_vals[-1] - t_vals[0]) > 0:
                                slope = float((vals[-1] - vals[0]) / (t_vals[-1] - t_vals[0]))
                                features[f"{prefix}_slope"] = slope
                            else:
                                features[f"{prefix}_slope"] = 0.0
                        else:
                            features[f"{prefix}_slope"] = 0.0

        # Shock Index: HR / SBP (últimos valores disponibles en 24h)
        hr_latest = features.get("vital_HR_24h_mean", np.nan)
        sbp_latest = features.get("vital_SBP_24h_mean", np.nan)

        if not np.isnan(hr_latest) and not np.isnan(sbp_latest) and sbp_latest > 0:
            features["vital_shock_index"] = float(hr_latest / sbp_latest)
        else:
            features["vital_shock_index"] = np.nan

        return features

    def _empty_features(self) -> Dict[str, float]:
        feats = {}
        for var in self.VITAL_VARS:
            for w in self.WINDOWS_HOURS:
                prefix = f"vital_{var}_{w}h"
                feats[f"{prefix}_mean"] = np.nan
                feats[f"{prefix}_min"] = np.nan
                feats[f"{prefix}_max"] = np.nan
                feats[f"{prefix}_std"] = np.nan
                feats[f"{prefix}_slope"] = np.nan
        feats["vital_shock_index"] = np.nan
        return feats
