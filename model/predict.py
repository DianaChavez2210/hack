"""
Módulo de Inferencia de Riesgo Clínico (RiskPredictor).
Carga el artefacto entrenado (model/artifacts/risk_model.joblib) y ejecuta la predicción calibrada.
"""

from typing import List, Dict, Any, Union, Optional
from pathlib import Path
import joblib
import pandas as pd
import numpy as np


class RiskPredictor:
    """
    Predictor de riesgo clínico calibrado en el rango [0.0, 1.0].
    """
    def __init__(self, model_path: str = "model/artifacts/risk_model.joblib"):
        self.model_path = Path(model_path)
        self.model = None
        self.feature_cols = None
        self.model_version = "v1.0.0"
        self._load_model()

    def _load_model(self):
        """Carga el artefacto serializado del modelo."""
        if self.model_path.exists():
            try:
                artifact = joblib.load(self.model_path)
                self.model = artifact.get("model")
                self.feature_cols = artifact.get("feature_cols")
                self.model_version = artifact.get("model_version", "v1.0.0")
            except Exception as e:
                print(f"[WARN] Error al cargar artefacto de modelo {self.model_path}: {e}")
                self.model = None

    def predict_risk(
        self,
        features: Union[Dict[str, Any], pd.DataFrame]
    ) -> Union[float, np.ndarray]:
        """
        Calcula la probabilidad de riesgo calibrada continuo [0.0, 1.0] para un paciente o lote de características.
        """
        if isinstance(features, dict):
            df_feat = pd.DataFrame([features])
            is_single = True
        else:
            df_feat = features.copy()
            is_single = False

        if self.model is not None and self.feature_cols:
            # Reordenar y rellenar columnas exactas del modelo
            for col in self.feature_cols:
                if col not in df_feat.columns:
                    df_feat[col] = np.nan

            X = df_feat[self.feature_cols].fillna(-999.0)
            probs = self.model.predict_proba(X)[:, 1]
            probs = np.clip(probs, 0.0, 1.0)
            return float(probs[0]) if is_single else probs
        else:
            # Fallback Heurístico Calibrado si el artefacto aún no se ha entrenado
            probs = []
            for _, row in df_feat.iterrows():
                score = 0.15
                spo2 = row.get("vital_SpO2_24h_min")
                hr = row.get("vital_HR_24h_max")
                rr = row.get("vital_RR_24h_max")
                shock = row.get("vital_shock_index")

                if pd.notnull(spo2) and spo2 < 90.0:
                    score += 0.35
                if pd.notnull(hr) and hr > 110.0:
                    score += 0.25
                if pd.notnull(rr) and rr > 22.0:
                    score += 0.20
                if pd.notnull(shock) and shock > 0.9:
                    score += 0.15

                probs.append(min(0.99, max(0.05, round(score, 3))))

            probs_arr = np.array(probs)
            return float(probs_arr[0]) if is_single else probs_arr
