"""
Submódulo de Extracción de Características de Línea Base y Comorbilidades.
Extrae perfil comórbido (conditions.csv) y conteo de condiciones crónicas.
"""

from typing import List, Dict, Any
import pandas as pd
import numpy as np


class BaselineFeaturesExtractor:
    """
    Extractor de antecedentes y línea base histórica del paciente.
    """
    HIGH_RISK_CONDITIONS = ["I50", "E11", "J44", "N18", "I10", "HEART_FAILURE", "DIABETES", "COPD", "HYPERTENSION"]

    def extract_features(
        self,
        conditions_df: pd.DataFrame,
        patients_df: pd.DataFrame,
        patient_id: str
    ) -> Dict[str, float]:
        """
        Extrae características de comorbilidad y perfil demográfico.
        """
        features: Dict[str, float] = {}

        # 1. Comorbilidades
        comorbidity_count = 0.0
        high_risk_flag = 0.0

        if not conditions_df.empty:
            df_pat = conditions_df[conditions_df["patient_id"] == patient_id]
            if not df_pat.empty:
                comorbidity_count = float(len(df_pat))
                flat_vals = [str(x) for x in df_pat.values.flatten() if pd.notnull(x)]
                codes_str = " ".join(flat_vals).upper()
                for h_cond in self.HIGH_RISK_CONDITIONS:
                    if h_cond in codes_str:
                        high_risk_flag = 1.0
                        break

        features["baseline_comorbidity_count"] = comorbidity_count
        features["baseline_high_risk_condition"] = high_risk_flag

        # 2. Edad y Sexo
        age_years = np.nan
        sex_female = 0.0

        if not patients_df.empty:
            pat_row = patients_df[patients_df["patient_id"] == patient_id]
            if not pat_row.empty:
                r = pat_row.iloc[0]
                if "age_years" in r and pd.notnull(r["age_years"]):
                    age_years = pd.to_numeric(r["age_years"], errors="coerce")
                if "sex_at_birth" in r and str(r["sex_at_birth"]).upper() in ("F", "FEMALE"):
                    sex_female = 1.0

        features["baseline_age_years"] = float(age_years) if pd.notnull(age_years) else 50.0
        features["baseline_sex_female"] = sex_female

        return features
