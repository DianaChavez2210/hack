"""
Servicio de Gestión y Consulta de Pacientes (Patient Service).
"""

from typing import List, Dict, Any, Optional
from app.services.data_loader import DataLoaderService
from app.schemas.patients import PatientBase, PatientDetail


class PatientService:
    """
    Servicio de lógica de negocio para pacientes y timeline.
    """
    def __init__(self):
        self.loader = DataLoaderService()

    def get_patients(
        self,
        care_program: Optional[str] = None,
        priority_level: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[PatientBase]:
        """
        Retorna la lista de pacientes con nivel de riesgo y prioridad cruzados de signals.csv.
        """
        patients_raw = self.loader.load_csv_records("patients.csv")
        signals_raw = self.loader.load_csv_records("signals.csv", is_results=True)

        # Mapa de últimas señales por paciente
        signals_map = {}
        for sig in signals_raw:
            pid = sig.get("patient_id")
            if pid:
                signals_map[pid] = sig

        patient_list = []
        for p in patients_raw:
            pid = p.get("patient_id")
            if not pid:
                continue

            sig = signals_map.get(pid, {})
            risk_score = float(sig.get("risk_score", 0.15))
            priority = sig.get("priority_level", "LOW")

            pat = PatientBase(
                patient_id=pid,
                age_years=float(p.get("age_years")) if p.get("age_years") else 50.0,
                sex_at_birth=p.get("sex_at_birth", "UNKNOWN"),
                facility_id=p.get("facility_id", "FAC-01"),
                care_program=p.get("care_program") or "HOME_MONITORING",
                risk_score=risk_score,
                priority_level=priority,
                status="CONNECTED"
            )

            # Aplicar filtros
            if care_program and pat.care_program != care_program:
                continue
            if priority_level and pat.priority_level != priority_level:
                continue
            if search_query and search_query.lower() not in pid.lower():
                continue

            patient_list.append(pat)

        # Ordenar descendentemente por risk_score
        patient_list.sort(key=lambda x: x.risk_score, reverse=True)
        return patient_list

    def get_patient_detail(self, patient_id: str) -> Optional[PatientDetail]:
        """
        Retorna el detalle maestro del paciente (condiciones, medicaciones, dispositivos, encuentros).
        """
        patients_raw = self.loader.load_csv_records("patients.csv")
        pat_info = next((p for p in patients_raw if p.get("patient_id") == patient_id), None)
        if not pat_info:
            return None

        signals_raw = self.loader.load_csv_records("signals.csv", is_results=True)
        sig = next((s for s in signals_raw if s.get("patient_id") == patient_id), {})

        conditions = [c for c in self.loader.load_csv_records("conditions.csv") if c.get("patient_id") == patient_id]
        medications = [m for m in self.loader.load_csv_records("medications.csv") if m.get("patient_id") == patient_id]
        devices = [d for d in self.loader.load_csv_records("devices.csv") if d.get("patient_id") == patient_id or d.get("assigned_patient_id") == patient_id]
        encounters = [e for e in self.loader.load_csv_records("encounters.csv") if e.get("patient_id") == patient_id]

        return PatientDetail(
            patient_id=patient_id,
            age_years=float(pat_info.get("age_years")) if pat_info.get("age_years") else 50.0,
            sex_at_birth=pat_info.get("sex_at_birth", "UNKNOWN"),
            facility_id=pat_info.get("facility_id", "FAC-01"),
            care_program=pat_info.get("care_program") or "HOME_MONITORING",
            risk_score=float(sig.get("risk_score", 0.15)),
            priority_level=sig.get("priority_level", "LOW"),
            status="CONNECTED",
            conditions=conditions,
            medications=medications,
            devices=devices,
            encounters=encounters
        )

    def get_patient_timeline(self, patient_id: str) -> Dict[str, Any]:
        """
        Retorna la serie temporal consolidada del paciente (vitals, wearables, labs, context).
        """
        vitals = [v for v in self.loader.load_csv_records("vital_signs.csv") if v.get("patient_id") == patient_id]
        wearables = [w for w in self.loader.load_csv_records("wearables.csv") if w.get("patient_id") == patient_id]
        labs = [l for l in self.loader.load_csv_records("lab_results.csv") if l.get("patient_id") == patient_id]
        context = [c for c in self.loader.load_csv_records("patient_context.csv") if c.get("patient_id") == patient_id]

        items = []
        for r in vitals + wearables + labs:
            val_num = r.get("converted_value") or r.get("value_numeric") or r.get("value") or r.get("result_value")
            ts = r.get("event_datetime") or r.get("timestamp") or r.get("result_datetime") or r.get("sample_datetime")
            avail_ts = r.get("available_datetime") or r.get("sync_datetime") or ts

            items.append({
                "record_id": r.get("record_id") or r.get("observation_id") or r.get("lab_result_id") or "REC-0",
                "patient_id": patient_id,
                "variable_code": r.get("variable_code") or r.get("test_code") or "VITAL",
                "value_numeric": float(val_num) if val_num is not None and str(val_num).strip() not in ("", "None") else None,
                "original_unit": r.get("original_unit") or r.get("unit"),
                "event_datetime": str(ts),
                "available_datetime": str(avail_ts),
                "source_file": r.get("source_file", "vital_signs.csv"),
                "quality_flag": r.get("quality_flag", "OK"),
                "signal_quality": float(r.get("signal_quality")) if r.get("signal_quality") else 1.0,
                "patient_state": None
            })

        items.sort(key=lambda x: x["event_datetime"])

        return {
            "patient_id": patient_id,
            "total_records": len(items),
            "context_intervals": context,
            "items": items[-200:]  # Retornar los 200 eventos más recientes
        }
