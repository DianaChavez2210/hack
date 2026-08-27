"""
Orquestador Principal de Feature Engineering (FeatureBuilder).
Aplica LeakageGuard para cada evaluación temporal y consolida la matriz de características.
Optimizado con vectorización C y pre-parsing de fechas para alto rendimiento.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

from pipeline.leakage_guard import LeakageGuard
from features.vital_features import VitalFeaturesExtractor
from features.wearable_features import WearableFeaturesExtractor
from features.lab_features import LabFeaturesExtractor
from features.temporal_features import TemporalFeaturesExtractor
from features.quality_features import QualityFeaturesExtractor
from features.baseline_features import BaselineFeaturesExtractor


class FeatureBuilder:
    """
    Orquestador para construir vectores y matrices de características tabulares a partir del CDM.
    """
    def __init__(self):
        self.leakage_guard = LeakageGuard()
        self.vital_ext = VitalFeaturesExtractor()
        self.wearable_ext = WearableFeaturesExtractor()
        self.lab_ext = LabFeaturesExtractor()
        self.temporal_ext = TemporalFeaturesExtractor()
        self.quality_ext = QualityFeaturesExtractor()
        self.baseline_ext = BaselineFeaturesExtractor()

    def build_features_for_patient(
        self,
        patient_id: str,
        decision_datetime: datetime,
        vitals_df: pd.DataFrame,
        wearables_df: pd.DataFrame,
        labs_df: pd.DataFrame,
        conditions_df: pd.DataFrame,
        patients_df: pd.DataFrame,
        context_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Extrae un vector de características completo para un paciente en un instante T_decision,
        garantizando cero fuga temporal vía LeakageGuard.
        """
        # Aplicar el Guardián Anti-Fuga Temporal sobre cada conjunto de datos
        v_safe = self.leakage_guard.filter_available_records(vitals_df, decision_datetime)
        w_safe = self.leakage_guard.filter_available_records(wearables_df, decision_datetime)
        l_safe = self.leakage_guard.filter_available_records(labs_df, decision_datetime)

        dfs_to_concat = [df for df in [v_safe, w_safe, l_safe] if not df.empty]
        all_safe = pd.concat(dfs_to_concat, ignore_index=True) if dfs_to_concat else pd.DataFrame()

        feats: Dict[str, Any] = {
            "patient_id": patient_id,
            "decision_datetime": decision_datetime.strftime("%Y-%m-%d %H:%M:%S")
        }

        feats.update(self.vital_ext.extract_features(v_safe, patient_id, decision_datetime))
        feats.update(self.wearable_ext.extract_features(w_safe, context_df, patient_id, decision_datetime))
        feats.update(self.lab_ext.extract_features(l_safe, patient_id, decision_datetime))
        feats.update(self.temporal_ext.extract_features(all_safe, patient_id, decision_datetime))
        feats.update(self.quality_ext.extract_features(v_safe, w_safe, patient_id, decision_datetime))
        feats.update(self.baseline_ext.extract_features(conditions_df, patients_df, patient_id))

        return feats

    def build_feature_matrix(
        self,
        clean_dir: str = "data/clean/csv",
        output_parquet: str = "data/features/features_matrix.parquet"
    ) -> pd.DataFrame:
        """
        Carga la capa CLEAN y genera la matriz de características consolidada para todos los pacientes.
        Vectorización C y pre-parsing de fechas para ejecución instantánea.
        """
        clean_path = Path(clean_dir)
        out_path = Path(output_parquet)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        print("[INFO] Cargando datos limpios para Feature Matrix...", flush=True)

        def _load_csv(filename: str) -> pd.DataFrame:
            fp = clean_path / filename
            if fp.exists():
                try:
                    df = pd.read_csv(fp, encoding="utf-8-sig", low_memory=False)
                    for col in ["available_datetime", "event_datetime", "timestamp", "result_datetime", "sample_datetime"]:
                        if col in df.columns:
                            df[col] = pd.to_datetime(df[col], format="mixed", errors="coerce")
                    return df
                except Exception:
                    return pd.DataFrame()
            return pd.DataFrame()

        vitals_df = _load_csv("vital_signs.csv")
        wearables_df = _load_csv("wearables.csv")
        labs_df = _load_csv("lab_results.csv")
        conditions_df = _load_csv("conditions.csv")
        patients_df = _load_csv("patients.csv")
        context_df = _load_csv("patient_context.csv")

        print("[INFO] Indexando DataFrames por patient_id O(1)...", flush=True)

        def _group_by_pat(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
            if df.empty or "patient_id" not in df.columns:
                return {}
            return dict(tuple(df.groupby("patient_id")))

        vitals_by_pat = _group_by_pat(vitals_df)
        wearables_by_pat = _group_by_pat(wearables_df)
        labs_by_pat = _group_by_pat(labs_df)
        conditions_by_pat = _group_by_pat(conditions_df)
        patients_by_pat = _group_by_pat(patients_df)
        context_by_pat = _group_by_pat(context_df)

        pids = sorted(list(set(vitals_by_pat.keys()) | set(wearables_by_pat.keys()) | set(labs_by_pat.keys()) | set(patients_by_pat.keys())))

        print(f"[INFO] Extrayendo vector de características para {len(pids)} pacientes...", flush=True)

        rows = []
        for pid in pids:
            v_pat = vitals_by_pat.get(pid, pd.DataFrame())
            w_pat = wearables_by_pat.get(pid, pd.DataFrame())
            l_pat = labs_by_pat.get(pid, pd.DataFrame())
            c_pat = conditions_by_pat.get(pid, pd.DataFrame())
            p_pat = patients_by_pat.get(pid, pd.DataFrame())
            ctx_pat = context_by_pat.get(pid, pd.DataFrame())

            # Determinar T_decision
            patient_dts = []
            for df_sub in [v_pat, w_pat, l_pat]:
                if not df_sub.empty:
                    col_t = "available_datetime" if "available_datetime" in df_sub.columns else ("event_datetime" if "event_datetime" in df_sub.columns else "timestamp")
                    if col_t in df_sub.columns:
                        if pd.api.types.is_datetime64_any_dtype(df_sub[col_t]):
                            dts = df_sub[col_t].dropna()
                        else:
                            dts = pd.to_datetime(df_sub[col_t], errors="coerce").dropna()
                        if not dts.empty:
                            patient_dts.append(dts.max())

            if not patient_dts:
                t_decision = datetime.now()
            else:
                t_decision = max(patient_dts)

            row_feat = self.build_features_for_patient(
                patient_id=pid,
                decision_datetime=t_decision,
                vitals_df=v_pat,
                wearables_df=w_pat,
                labs_df=l_pat,
                conditions_df=c_pat,
                patients_df=p_pat,
                context_df=ctx_pat
            )
            rows.append(row_feat)

        feat_matrix = pd.DataFrame(rows)

        # Exportar Parquet y CSV
        feat_matrix.to_parquet(out_path, index=False)
        csv_out = out_path.with_suffix(".csv")
        feat_matrix.to_csv(csv_out, index=False, encoding="utf-8-sig")

        print(f"[OK] Matriz de características generada: {feat_matrix.shape[0]} filas, {feat_matrix.shape[1]} columnas.", flush=True)
        print(f"     Parquet: {out_path}", flush=True)
        print(f"     CSV:     {csv_out}", flush=True)

        return feat_matrix
