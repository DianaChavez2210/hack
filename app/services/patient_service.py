"""
Servicio de Gestión y Consulta de Pacientes (Patient Service).
Conectado a la base de datos PostgreSQL local risa_db.
"""

from typing import List, Dict, Any, Optional
from app.services.data_loader import DataLoaderService
from app.schemas.patients import PatientBase, PatientDetail


def safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        s = str(val).strip()
        if not s or s.lower() in ("none", "null", "nan"):
            return default
        return float(s)
    except Exception:
        return default


class PatientService:
    """
    Servicio de lógica de negocio para pacientes y timeline desde PostgreSQL risa_db.
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
        Retorna la lista de pacientes con nivel de riesgo y prioridad desde PostgreSQL risa_db.
        """
        patient_list = []

        try:
            sql = """
                SELECT 
                    p.patient_id, p.age_years, p.sex_at_birth, p.care_program, p.region_type,
                    COALESCE(s.risk_score, 0.15) AS risk_score,
                    COALESCE(s.priority_level, 'LOW') AS priority_level
                FROM risa_raw.patients p
                LEFT JOIN risa_raw.signals s ON p.patient_id = s.patient_id
                ORDER BY s.risk_score DESC NULLS LAST;
            """
            rows = self.loader.query_db(sql)
            for r in rows:
                pid = str(r.get("patient_id", ""))
                if not pid:
                    continue

                pat = PatientBase(
                    patient_id=pid,
                    age_years=safe_float(r.get("age_years"), default=50.0),
                    sex_at_birth=str(r.get("sex_at_birth") or "UNKNOWN"),
                    facility_id="FAC-01",
                    care_program=str(r.get("care_program") or "HOME_MONITORING"),
                    risk_score=safe_float(r.get("risk_score"), default=0.15),
                    priority_level=str(r.get("priority_level") or "LOW"),
                    status="CONNECTED"
                )

                if care_program and pat.care_program != care_program:
                    continue
                if priority_level and pat.priority_level != priority_level:
                    continue
                if search_query and search_query.lower() not in pid.lower():
                    continue

                patient_list.append(pat)
        except Exception as e:
            print(f"[WARN] Error al consultar pacientes en PostgreSQL: {e}")

        # Fallback a CSV si la consulta DB no trajo registros
        if not patient_list:
            patients_raw = self.loader.load_csv_records("patients.csv")
            signals_raw = self.loader.load_csv_records("signals.csv", is_results=True)
            signals_map = {s.get("patient_id"): s for s in signals_raw if s.get("patient_id")}

            for p in patients_raw:
                pid = p.get("patient_id")
                if not pid:
                    continue

                sig = signals_map.get(pid, {})
                pat = PatientBase(
                    patient_id=pid,
                    age_years=safe_float(p.get("age_years"), default=50.0),
                    sex_at_birth=p.get("sex_at_birth", "UNKNOWN"),
                    facility_id=p.get("facility_id", "FAC-01"),
                    care_program=p.get("care_program") or "HOME_MONITORING",
                    risk_score=safe_float(sig.get("risk_score"), default=0.15),
                    priority_level=sig.get("priority_level", "LOW"),
                    status="CONNECTED"
                )

                if care_program and pat.care_program != care_program:
                    continue
                if priority_level and pat.priority_level != priority_level:
                    continue
                if search_query and search_query.lower() not in pid.lower():
                    continue

                patient_list.append(pat)

        patient_list.sort(key=lambda x: x.risk_score, reverse=True)
        return patient_list

    def get_patient_detail(self, patient_id: str) -> Optional[PatientDetail]:
        """
        Retorna el detalle maestro del paciente desde PostgreSQL risa_db.
        """
        try:
            p_rows = self.loader.query_db("SELECT * FROM risa_raw.patients WHERE patient_id = %s LIMIT 1;", (patient_id,))
            if p_rows:
                pat_info = p_rows[0]
                sig_rows = self.loader.query_db("SELECT risk_score, priority_level FROM risa_raw.signals WHERE patient_id = %s LIMIT 1;", (patient_id,))
                sig = sig_rows[0] if sig_rows else {}

                conditions = self.loader.query_db("SELECT * FROM risa_raw.conditions WHERE patient_id = %s;", (patient_id,))
                medications = self.loader.query_db("SELECT * FROM risa_raw.medication_administrations WHERE patient_id = %s;", (patient_id,))
                devices = self.loader.query_db("SELECT * FROM risa_raw.devices WHERE assigned_patient_id = %s;", (patient_id,))
                encounters = self.loader.query_db("SELECT * FROM risa_raw.encounters WHERE patient_id = %s;", (patient_id,))

                return PatientDetail(
                    patient_id=patient_id,
                    age_years=safe_float(pat_info.get("age_years"), default=50.0),
                    sex_at_birth=str(pat_info.get("sex_at_birth") or "UNKNOWN"),
                    facility_id="FAC-01",
                    care_program=str(pat_info.get("care_program") or "HOME_MONITORING"),
                    risk_score=safe_float(sig.get("risk_score"), default=0.15),
                    priority_level=str(sig.get("priority_level") or "LOW"),
                    status="CONNECTED",
                    conditions=conditions,
                    medications=medications,
                    devices=devices,
                    encounters=encounters
                )
        except Exception as e:
            print(f"[WARN] Error consultando detalle paciente {patient_id} en DB: {e}")

        # Fallback CSV
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
            age_years=safe_float(pat_info.get("age_years"), default=50.0),
            sex_at_birth=pat_info.get("sex_at_birth", "UNKNOWN"),
            facility_id=pat_info.get("facility_id", "FAC-01"),
            care_program=pat_info.get("care_program") or "HOME_MONITORING",
            risk_score=safe_float(sig.get("risk_score"), default=0.15),
            priority_level=sig.get("priority_level", "LOW"),
            status="CONNECTED",
            conditions=conditions,
            medications=medications,
            devices=devices,
            encounters=encounters
        )

    def get_patient_timeline(self, patient_id: str) -> Dict[str, Any]:
        """
        Retorna la serie temporal consolidada del paciente desde PostgreSQL risa_db.
        """
        items = []
        context = []

        try:
            v_sql = "SELECT observation_id AS record_id, patient_id, variable_code, value AS value_numeric, unit AS original_unit, timestamp AS event_datetime, timestamp AS available_datetime, 'vital_signs' AS source_file, quality_flag FROM risa_raw.vital_signs WHERE patient_id = %s ORDER BY timestamp DESC LIMIT 150;"
            w_sql = "SELECT wearable_observation_id AS record_id, patient_id, variable_code, value AS value_str, unit AS original_unit, timestamp AS event_datetime, sync_datetime AS available_datetime, 'wearable_observations' AS source_file, measurement_quality AS quality_flag FROM risa_raw.wearable_observations WHERE patient_id = %s ORDER BY timestamp DESC LIMIT 150;"
            l_sql = "SELECT lab_result_id AS record_id, patient_id, test_code AS variable_code, result_value AS value_numeric, unit AS original_unit, sample_datetime AS event_datetime, result_datetime AS available_datetime, 'laboratory_results' AS source_file, quality_flag FROM risa_raw.laboratory_results WHERE patient_id = %s ORDER BY sample_datetime DESC LIMIT 50;"
            c_sql = "SELECT * FROM risa_raw.patient_context WHERE patient_id = %s;"

            vitals = self.loader.query_db(v_sql, (patient_id,))
            wearables = self.loader.query_db(w_sql, (patient_id,))
            labs = self.loader.query_db(l_sql, (patient_id,))
            context = self.loader.query_db(c_sql, (patient_id,))

            for r in vitals + labs:
                items.append({
                    "record_id": str(r.get("record_id", "REC-0")),
                    "patient_id": patient_id,
                    "variable_code": str(r.get("variable_code", "VITAL")),
                    "value_numeric": safe_float(r.get("value_numeric")),
                    "original_unit": r.get("original_unit"),
                    "event_datetime": str(r.get("event_datetime", "")),
                    "available_datetime": str(r.get("available_datetime", "")),
                    "source_file": str(r.get("source_file", "vital_signs.csv")),
                    "quality_flag": str(r.get("quality_flag", "OK")),
                    "signal_quality": 1.0,
                    "patient_state": None
                })

            for w in wearables:
                val_str = w.get("value_str")
                items.append({
                    "record_id": str(w.get("record_id", "REC-0")),
                    "patient_id": patient_id,
                    "variable_code": str(w.get("variable_code", "WEARABLE")),
                    "value_numeric": safe_float(val_str) if val_str and str(val_str).replace('.', '', 1).isdigit() else None,
                    "original_unit": w.get("original_unit"),
                    "event_datetime": str(w.get("event_datetime", "")),
                    "available_datetime": str(w.get("available_datetime", "")),
                    "source_file": "wearable_observations",
                    "quality_flag": str(w.get("quality_flag", "OK")),
                    "signal_quality": 1.0,
                    "patient_state": None
                })
        except Exception as e:
            print(f"[WARN] Error obteniendo timeline de PostgreSQL para paciente {patient_id}: {e}")

        # Fallback CSV si no hubo datos de DB
        if not items:
            vitals = [v for v in self.loader.load_csv_records("vital_signs.csv") if v.get("patient_id") == patient_id]
            wearables = [w for w in self.loader.load_csv_records("wearables.csv") if w.get("patient_id") == patient_id]
            labs = [l for l in self.loader.load_csv_records("lab_results.csv") if l.get("patient_id") == patient_id]
            context = [c for c in self.loader.load_csv_records("patient_context.csv") if c.get("patient_id") == patient_id]

            for r in vitals + wearables + labs:
                val_num = r.get("converted_value") or r.get("value_numeric") or r.get("value") or r.get("result_value")
                ts = r.get("event_datetime") or r.get("timestamp") or r.get("result_datetime") or r.get("sample_datetime")
                avail_ts = r.get("available_datetime") or r.get("sync_datetime") or ts

                items.append({
                    "record_id": r.get("record_id") or r.get("observation_id") or r.get("lab_result_id") or "REC-0",
                    "patient_id": patient_id,
                    "variable_code": r.get("variable_code") or r.get("test_code") or "VITAL",
                    "value_numeric": safe_float(val_num),
                    "original_unit": r.get("original_unit") or r.get("unit"),
                    "event_datetime": str(ts),
                    "available_datetime": str(avail_ts),
                    "source_file": r.get("source_file", "vital_signs.csv"),
                    "quality_flag": r.get("quality_flag", "OK"),
                    "signal_quality": safe_float(r.get("signal_quality"), default=1.0),
                    "patient_state": None
                })

        items.sort(key=lambda x: str(x["event_datetime"]))

        return {
            "patient_id": patient_id,
            "total_records": len(items),
            "context_intervals": context,
            "items": items[-200:]
        }

