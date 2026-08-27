"""
Módulo de Explicabilidad Clínica (ExplanationBuilder).
Genera explicaciones locales, estructuradas y deterministas en español a partir del CDM y pesos de características / SHAP.
"""

from typing import List, Dict, Any, Optional
import numpy as np


class ExplanationBuilder:
    """
    Generador local y determinista de justificaciones clínicas en español.
    Soporta valores SHAP y rankings de importancia de características para explicabilidad médica.
    """
    def __init__(self):
        # Mapeo de códigos a términos clínicos claros en español
        self.var_names = {
            "HR": "Frecuencia Cardíaca",
            "WEARABLE_HR": "Frecuencia Cardíaca (Wearable)",
            "RR": "Frecuencia Respiratoria",
            "SpO2": "Saturación de Oxígeno (SpO2)",
            "TEMP": "Temperatura Corporal",
            "SBP": "Presión Arterial Sistólica",
            "DBP": "Presión Arterial Diastólica",
            "GLUCOSE": "Glucosa",
            "STEPS": "Pasos",
            "WBC": "Leucocitos",
            "LACTATE": "Lactato",
            "CREATININE": "Creatinina"
        }

    def generate_explanation(
        self,
        patient_id: str,
        priority_level: str,
        decision_datetime: str,
        evidence_entries: List[Dict[str, Any]],
        cdm_records: List[Any],
        top_features: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Construye una explicación clínica detallada a partir de las evidencias y las principales características predictivas (SHAP).
        """
        primary_findings = []
        supporting_findings = []
        context_findings = []
        quality_findings = []

        # Mapa de búsqueda rápido para los registros CDM
        record_map = {rec.record_id: rec for rec in cdm_records}

        for ev in evidence_entries:
            rec_id = ev["record_id"]
            role = ev["evidence_role"]
            rec = record_map.get(rec_id)
            if not rec:
                continue

            val = rec.converted_value if rec.converted_value is not None else rec.value_numeric
            unit = rec.canonical_unit or rec.original_unit or ""
            var_desc = self.var_names.get(rec.variable_code, rec.variable_code)

            if role == "PRIMARY":
                if val is not None:
                    primary_findings.append(f"{var_desc} alterado ({val} {unit})")
                else:
                    primary_findings.append(f"{var_desc} (valor faltante/implausible)")
            elif role == "SUPPORTING":
                if val is not None:
                    supporting_findings.append(f"{var_desc}: {val} {unit}")
            elif role == "CONTEXT":
                p_state = rec.context_info.get("patient_state")
                if p_state:
                    context_findings.append(f"estado {p_state}")
                elif rec.source_file in ("patients.csv", "01_master/patients.csv"):
                    age = rec.header_fields.get("age_years") if rec.header_fields else None
                    sex = rec.header_fields.get("sex_at_birth") if rec.header_fields else None
                    if age is not None:
                        context_findings.append(f"paciente de {age} años ({sex or 'desconocido'})")
            elif role == "QUALITY":
                net_status = rec.context_info.get("network_status")
                loss = rec.context_info.get("packet_loss")
                sig_quality = rec.signal_quality
                
                if net_status:
                    quality_findings.append(f"red {net_status} (pérdida: {loss or 0}%)")
                if sig_quality is not None:
                    quality_findings.append(f"calidad señal wearable: {sig_quality}")
                if not rec.is_observed:
                    quality_findings.append(f"ausencia de observación en {rec.variable_code}")

        # Redacción de la explicación determinista
        parts = [f"Prioridad {priority_level} para el paciente {patient_id} a las {decision_datetime}."]

        if top_features:
            shap_desc = []
            for feat in top_features[:3]:
                fname = feat.get("feature_name", "")
                fval = feat.get("value")
                if fval is not None:
                    shap_desc.append(f"{fname}={fval:.2f}")
            if shap_desc:
                parts.append("Factores predictivos clave (SHAP): " + ", ".join(shap_desc) + ".")

        if primary_findings:
            parts.append("Hallazgos principales: " + ", ".join(primary_findings) + ".")
        
        if supporting_findings:
            parts.append("Hallazgos de soporte: " + ", ".join(supporting_findings) + ".")

        if context_findings:
            parts.append("Contexto: " + "; ".join(context_findings) + ".")

        if quality_findings:
            parts.append("Incidencias de calidad/red: " + "; ".join(list(set(quality_findings))) + ".")
        else:
            parts.append("Calidad de datos: Sin incidencias de red o de señal.")

        return " ".join(parts)
