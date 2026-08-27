"""
Servicio de Trazabilidad y Linaje de Evidencia (Evidence Service).
Integrado con ClinicalSummaryService para análisis clínico exacto y auditoría de falsos positivos técnicos.
"""

from typing import List, Dict, Any, Optional
from app.services.clinical_summary_service import ClinicalSummaryService
from app.schemas.evidence import SignalEvidenceResponse, EvidenceRecordSchema


class EvidenceService:
    """
    Servicio de trazabilidad y linaje de evidencia desde PostgreSQL risa_db.
    """
    def __init__(self):
        self.summary_service = ClinicalSummaryService()

    def get_signal_evidence(self, signal_id: str) -> Optional[SignalEvidenceResponse]:
        analysis = self.summary_service.analyze_signal(signal_id, signal_id)
        if not analysis:
            return None

        records_list = []
        for e in analysis.get("evidences", []):
            records_list.append(EvidenceRecordSchema(
                signal_id=analysis["signal_id"],
                source_file=str(e.get("source_file", "")),
                record_id=str(e.get("record_id", "")),
                variable_code=str(e.get("variable_code", "")),
                event_datetime=str(e.get("event_datetime", "")),
                available_datetime=str(e.get("available_datetime", "")),
                evidence_role=str(e.get("evidence_role", "SUPPORTING")),
                contribution=float(e.get("contribution") or 0.0),
                value_numeric=e.get("value_numeric"),
                original_unit=e.get("original_unit"),
                canonical_unit=e.get("original_unit")
            ))

        return SignalEvidenceResponse(
            signal_id=analysis["signal_id"],
            patient_id=analysis["patient_id"],
            decision_datetime=analysis["decision_datetime"],
            risk_score=analysis["risk_score"],
            priority_level=analysis["priority_level"],
            onset_datetime=analysis["onset_datetime"],
            explanation=analysis["explanation"],
            what_went_wrong=analysis["what_went_wrong"],
            shap_contributions=analysis["shap_contributions"],
            evidences=records_list
        )


