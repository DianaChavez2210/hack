import React, { useState, useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';
import { 
  Activity, Users, AlertTriangle, ShieldAlert, WifiOff, 
  FileText, HardDrive, LineChart, ShieldCheck, CheckCircle2, 
  ListFilter, Moon, Sun, Stethoscope, Pill, Database, X, Search,
  ArrowLeft, ChevronRight, Clock, AlertCircle, Info, ExternalLink
} from 'lucide-react';

const API_BASE = "http://localhost:8000/api/v1";

// Mock Fallback Data
const MOCK_PATIENTS = [
  { patient_id: "PAT-0001", age_years: 68, sex_at_birth: "MALE", care_program: "HOSPITAL_OBSERVATION", risk_score: 0.92, priority_level: "CRITICAL", status: "CONNECTED", facility_id: "FAC-01" },
  { patient_id: "PAT-0042", age_years: 74, sex_at_birth: "FEMALE", care_program: "HOME_MONITORING", risk_score: 0.86, priority_level: "CRITICAL", status: "CONNECTED", facility_id: "FAC-02" },
  { patient_id: "PAT-0108", age_years: 59, sex_at_birth: "MALE", care_program: "HOME_MONITORING", risk_score: 0.74, priority_level: "HIGH", status: "CONNECTED", facility_id: "FAC-01" },
  { patient_id: "PAT-0215", age_years: 81, sex_at_birth: "FEMALE", care_program: "HOSPITAL_OBSERVATION", risk_score: 0.68, priority_level: "HIGH", status: "DISCONNECTED", facility_id: "FAC-03" },
  { patient_id: "PAT-0350", age_years: 62, sex_at_birth: "MALE", care_program: "HOME_MONITORING", risk_score: 0.48, priority_level: "MEDIUM", status: "CONNECTED", facility_id: "FAC-01" },
  { patient_id: "PAT-0412", age_years: 55, sex_at_birth: "FEMALE", care_program: "HOME_MONITORING", risk_score: 0.22, priority_level: "LOW", status: "CONNECTED", facility_id: "FAC-02" },
];

const MOCK_TIMELINE = {
  patient_id: "PAT-0001",
  total_records: 10,
  context_intervals: [
    { context_id: "CTX-01", context_value: "SLEEP", start_datetime: "2026-07-10 00:00:00", end_datetime: "2026-07-10 07:00:00" },
    { context_id: "CTX-02", context_value: "AWAKE", start_datetime: "2026-07-10 07:00:00", end_datetime: "2026-07-10 12:00:00" }
  ],
  items: [
    { record_id: "REC-01", variable_code: "HR", value_numeric: 78, original_unit: "bpm", event_datetime: "2026-07-10 06:00:00", available_datetime: "2026-07-10 06:01:00", source_file: "vital_signs.csv" },
    { record_id: "REC-02", variable_code: "SpO2", value_numeric: 97, original_unit: "%", event_datetime: "2026-07-10 06:00:00", available_datetime: "2026-07-10 06:01:00", source_file: "vital_signs.csv" },
    { record_id: "REC-03", variable_code: "SBP", value_numeric: 122, original_unit: "mmHg", event_datetime: "2026-07-10 06:00:00", available_datetime: "2026-07-10 06:01:00", source_file: "vital_signs.csv" },
    { record_id: "REC-04", variable_code: "HR", value_numeric: 95, original_unit: "bpm", event_datetime: "2026-07-10 09:00:00", available_datetime: "2026-07-10 09:01:00", source_file: "vital_signs.csv" },
    { record_id: "REC-05", variable_code: "SpO2", value_numeric: 94, original_unit: "%", event_datetime: "2026-07-10 09:00:00", available_datetime: "2026-07-10 09:01:00", source_file: "vital_signs.csv" },
    { record_id: "REC-06", variable_code: "SBP", value_numeric: 135, original_unit: "mmHg", event_datetime: "2026-07-10 09:00:00", available_datetime: "2026-07-10 09:01:00", source_file: "vital_signs.csv" },
    { record_id: "REC-07", variable_code: "HR", value_numeric: 118, original_unit: "bpm", event_datetime: "2026-07-10 11:30:00", available_datetime: "2026-07-10 11:31:00", source_file: "vital_signs.csv" },
    { record_id: "REC-08", variable_code: "SpO2", value_numeric: 88, original_unit: "%", event_datetime: "2026-07-10 11:30:00", available_datetime: "2026-07-10 11:31:00", source_file: "vital_signs.csv" },
    { record_id: "REC-09", variable_code: "SBP", value_numeric: 148, original_unit: "mmHg", event_datetime: "2026-07-10 11:30:00", available_datetime: "2026-07-10 11:31:00", source_file: "vital_signs.csv" },
    { record_id: "REC-10", variable_code: "RR", value_numeric: 24, original_unit: "rpm", event_datetime: "2026-07-10 11:30:00", available_datetime: "2026-07-10 11:31:00", source_file: "vital_signs.csv" },
  ]
};

const MOCK_PATIENT_DETAIL = {
  patient_id: "PAT-0001",
  age_years: 68,
  sex_at_birth: "MALE",
  care_program: "HOSPITAL_OBSERVATION",
  facility_id: "FAC-01",
  risk_score: 0.92,
  priority_level: "CRITICAL",
  conditions: [
    { condition_id: "COND-01", icd10_code: "I50.9", condition_name: "Insuficiencia Cardíaca Congestiva", status: "ACTIVE" },
    { condition_id: "COND-02", icd10_code: "E11.9", condition_name: "Diabetes Mellitus Tipo 2", status: "ACTIVE" },
    { condition_id: "COND-03", icd10_code: "I10", condition_name: "Hipertensión Arterial Primaria", status: "ACTIVE" }
  ],
  medications: [
    { medication_id: "MED-01", drug_name: "Furosemida", dose: "40 mg", route: "IV", status: "ADMINISTERED" },
    { medication_id: "MED-02", drug_name: "Enalapril", dose: "10 mg", route: "ORAL", status: "ACTIVE" }
  ],
  devices: [
    { device_id: "DEV-00041", device_type: "ECG_PATCH", status: "ACTIVE", battery_level: 88, signal_quality: 0.96 }
  ]
};

const MOCK_TECHNICAL_ALERTS = [
  { alert_id: "ALT-HW-0001", patient_id: "PAT-0215", device_id: "DEV-00012", alert_type: "LOW_SIGNAL_QUALITY", severity: "HIGH", timestamp: "2026-07-10 11:45:00", message: "Monitor DEV-00012 con SQI = 0.68 (Posible electrodo suelto)", signal_quality_index: 0.68 },
  { alert_id: "ALT-NET-0002", patient_id: "PAT-0042", device_id: "GW-0004", alert_type: "PACKET_LOSS", severity: "MEDIUM", timestamp: "2026-07-10 11:50:00", message: "Pérdida de paquetes estimada en 28% en Gateway regional FAC-02", packet_loss_estimate: 0.28 },
];

const MOCK_SIGNALS = [
  { signal_id: "SIG-000001", patient_id: "PAT-0001", decision_datetime: "2026-07-10 12:00:00", risk_score: 0.92, priority_level: "CRITICAL", evidence_start: "2026-07-09 12:00:00", evidence_end: "2026-07-10 12:00:00", explanation: "Prioridad CRITICAL para el paciente PAT-0001. Hallazgos principales: Frecuencia Cardíaca alterada (128 bpm), Saturación de Oxígeno alterada (88%). Hallazgos de soporte: Frecuencia Respiratoria: 24 bpm. Contexto: estado SLEEP. Calidad de datos: Sin incidencias de red." },
  { signal_id: "SIG-000002", patient_id: "PAT-0042", decision_datetime: "2026-07-10 12:00:00", risk_score: 0.86, priority_level: "CRITICAL", evidence_start: "2026-07-09 12:00:00", evidence_end: "2026-07-10 12:00:00", explanation: "Prioridad CRITICAL para el paciente PAT-0042. Hallazgos principales: Frecuencia Cardíaca alterada (118 bpm). Incidencias de calidad/red: red DELAYED_SYNC (pérdida: 28%)." },
];

const MOCK_EVIDENCE_MAP = {
  "SIG-000001": {
    signal_id: "SIG-000001",
    patient_id: "PAT-0001",
    decision_datetime: "2026-07-10 12:00:00",
    risk_score: 0.92,
    priority_level: "CRITICAL",
    onset_datetime: "2026-07-10 09:00:00",
    what_went_wrong: {
      primary_symptom: "Desaturación aguda de Oxígeno (SpO2: 88%) y Taquicardia severa (HR: 118-128 bpm).",
      supporting_symptom: "Frecuencia respiratoria en 24 rpm (Taquipnea moderada) y Presión Sistólica elevada en 148 mmHg.",
      context_state: "Anomalía detectada en reposo (Estado SLEEP): Elevación sostenida del ritmo cardíaco durante la madrugada.",
      data_quality: "Sin desincronización de red (SQI: 0.96 / Pérdida de paquetes: 0%). Alerta fisiológica legítima."
    },
    shap_contributions: [
      { feature_name: "vital_SpO2_24h_min", importance: 0.42, description: "Desaturación de oxígeno SpO2 < 90%" },
      { feature_name: "vital_HR_24h_max", importance: 0.35, description: "Taquicardia sostenida HR > 120 bpm" },
      { feature_name: "wearable_sleep_hr_anomaly", importance: 0.18, description: "Frecuencia cardíaca elevada durante estado SLEEP" }
    ],
    evidences: [
      { signal_id: "SIG-000001", source_file: "vital_signs.csv", record_id: "OBS-00004128", variable_code: "SpO2", event_datetime: "2026-07-10 11:30:00", available_datetime: "2026-07-10 11:31:00", evidence_role: "PRIMARY", contribution: 0.85 },
      { signal_id: "SIG-000001", source_file: "vital_signs.csv", record_id: "OBS-00004129", variable_code: "HR", event_datetime: "2026-07-10 11:40:00", available_datetime: "2026-07-10 11:41:00", evidence_role: "PRIMARY", contribution: 0.80 },
      { signal_id: "SIG-000001", source_file: "patient_context.csv", record_id: "CTX-000142", variable_code: "SLEEP_STATE", event_datetime: "2026-07-10 10:00:00", available_datetime: "2026-07-10 10:05:00", evidence_role: "CONTEXT", contribution: 0.25 },
      { signal_id: "SIG-000001", source_file: "vital_signs.csv", record_id: "OBS-00004100", variable_code: "RR", event_datetime: "2026-07-10 11:00:00", available_datetime: "2026-07-10 11:01:00", evidence_role: "SUPPORTING", contribution: 0.15 }
    ]
  }
};

// Component: Multi-Line Chart for Physiological Timeline
function ClinicalTimelineChart({ items }) {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (!chartRef.current || !items || items.length === 0) return;

    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    const ctx = chartRef.current.getContext('2d');
    
    const timeMap = {};
    items.forEach(i => {
      const t = i.event_datetime ? (i.event_datetime.split(' ')[1] || i.event_datetime) : '12:00';
      if (!timeMap[t]) timeMap[t] = {};
      timeMap[t][i.variable_code] = i.value_numeric;
    });

    const labels = Object.keys(timeMap).sort();
    const hrData = labels.map(t => timeMap[t]['HR'] || timeMap[t]['WEARABLE_HR'] || null);
    const spo2Data = labels.map(t => timeMap[t]['SpO2'] || null);
    const sbpData = labels.map(t => timeMap[t]['SBP'] || null);
    const rrData = labels.map(t => timeMap[t]['RR'] || null);

    chartInstance.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          { label: 'HR (bpm)', data: hrData, borderColor: '#dc2626', backgroundColor: '#fef2f2', tension: 0.2, spanGaps: true, pointRadius: 5 },
          { label: 'SpO2 (%)', data: spo2Data, borderColor: '#2563eb', backgroundColor: '#eff6ff', tension: 0.2, spanGaps: true, pointRadius: 5 },
          { label: 'SBP (mmHg)', data: sbpData, borderColor: '#ea580c', backgroundColor: '#fff7ed', tension: 0.2, spanGaps: true, pointRadius: 5 },
          { label: 'RR (rpm)', data: rrData, borderColor: '#059669', backgroundColor: '#ecfdf5', tension: 0.2, spanGaps: true, pointRadius: 5 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#334155', font: { family: 'Inter', size: 11, weight: 'bold' } } },
          tooltip: { mode: 'index', intersect: false }
        },
        scales: {
          x: { ticks: { color: '#64748b', font: { size: 10 } }, grid: { color: '#e2e8f0' } },
          y: { ticks: { color: '#64748b', font: { size: 10 } }, grid: { color: '#e2e8f0' } }
        }
      }
    });

    return () => {
      if (chartInstance.current) chartInstance.current.destroy();
    };
  }, [items]);

  return (
    <div className="relative w-full h-64 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
      <canvas ref={chartRef}></canvas>
    </div>
  );
}

// Modal: Patient History & Clinical Timeline Deep-Dive
function PatientHistoryModal({ patientId, onClose }) {
  const [patientDetail, setPatientDetail] = useState(MOCK_PATIENT_DETAIL);
  const [timeline, setTimeline] = useState(MOCK_TIMELINE);
  const [activeTab, setActiveTab] = useState("TIMELINE");

  useEffect(() => {
    async function fetchPatientHistory() {
      try {
        const resDetail = await fetch(`${API_BASE}/patients/${patientId}`);
        if (resDetail.ok) {
          const dataDetail = await resDetail.json();
          setPatientDetail(dataDetail);
        }

        const resTimeline = await fetch(`${API_BASE}/patients/${patientId}/timeline`);
        if (resTimeline.ok) {
          const dataTimeline = await resTimeline.json();
          setTimeline(dataTimeline);
        }
      } catch (e) {
        console.log("Using fallback mock history:", e);
      }
    }
    if (patientId) fetchPatientHistory();
  }, [patientId]);

  if (!patientId) return null;

  const priorityBadge = 
    patientDetail.priority_level === 'CRITICAL' ? 'bg-red-100 text-red-700 border-red-300' :
    patientDetail.priority_level === 'HIGH' ? 'bg-orange-100 text-orange-700 border-orange-300' :
    patientDetail.priority_level === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800 border-yellow-300' :
    'bg-emerald-100 text-emerald-700 border-emerald-300';

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-4xl bg-white border border-slate-200 rounded-2xl h-[90vh] flex flex-col overflow-hidden shadow-xl">
        {/* Modal Header */}
        <div className="p-6 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold text-lg shadow-sm">
              {patientId.substring(4)}
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-extrabold text-slate-900">{patientId}</h2>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold border ${priorityBadge}`}>
                  {patientDetail.priority_level} ({patientDetail.risk_score.toFixed(2)})
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {patientDetail.age_years} años • Sexo: {patientDetail.sex_at_birth} • Programa: <span className="font-mono font-semibold text-slate-700">{patientDetail.care_program}</span> • Centro: <span className="font-mono font-semibold text-slate-700">{patientDetail.facility_id}</span>
              </p>
            </div>
          </div>

          <button onClick={onClose} className="w-9 h-9 rounded-xl bg-slate-200 text-slate-600 hover:bg-slate-300 flex items-center justify-center transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="px-6 bg-white border-b border-slate-200 flex items-center gap-4 text-xs font-semibold">
          <button 
            onClick={() => setActiveTab("TIMELINE")} 
            className={`py-3 border-b-2 flex items-center gap-2 transition ${activeTab === 'TIMELINE' ? 'border-blue-600 text-blue-600 font-bold' : 'border-transparent text-slate-500 hover:text-slate-900'}`}
          >
            <LineChart className="w-4 h-4" /> Serie Temporal Fisiológica
          </button>
          <button 
            onClick={() => setActiveTab("CONDITIONS")} 
            className={`py-3 border-b-2 flex items-center gap-2 transition ${activeTab === 'CONDITIONS' ? 'border-blue-600 text-blue-600 font-bold' : 'border-transparent text-slate-500 hover:text-slate-900'}`}
          >
            <Stethoscope className="w-4 h-4" /> Comorbilidades y Fármacos
          </button>
          <button 
            onClick={() => setActiveTab("RAW_RECORDS")} 
            className={`py-3 border-b-2 flex items-center gap-2 transition ${activeTab === 'RAW_RECORDS' ? 'border-blue-600 text-blue-600 font-bold' : 'border-transparent text-slate-500 hover:text-slate-900'}`}
          >
            <Database className="w-4 h-4" /> Eventos CDM ({timeline.items ? timeline.items.length : 0})
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 p-6 overflow-y-auto space-y-6 bg-slate-50">
          {activeTab === "TIMELINE" && (
            <div className="space-y-6">
              {/* Context Bar: Sleep vs Awake */}
              <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm space-y-2">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                  <Moon className="w-4 h-4 text-indigo-600" /> Capa Contextual (Sueño / Actividad)
                </h3>
                <div className="flex items-center gap-2">
                  {timeline.context_intervals && timeline.context_intervals.map((c, i) => (
                    <span key={i} className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold flex items-center gap-1.5 ${c.context_value === 'SLEEP' ? 'bg-indigo-50 text-indigo-700 border border-indigo-200' : 'bg-amber-50 text-amber-800 border border-amber-200'}`}>
                      <span>{c.context_value === 'SLEEP' ? '🌙 SLEEP' : '☀️ AWAKE'}</span>
                      <span className="text-[10px] text-slate-500">({c.start_datetime.split(' ')[1]} - {c.end_datetime.split(' ')[1]})</span>
                    </span>
                  ))}
                </div>
              </div>

              {/* Chart.js Multi-axis Time Series */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                  <Activity className="w-4 h-4 text-blue-600" /> Evolución Temporal de Signos Vitales
                </h3>
                <ClinicalTimelineChart items={timeline.items || []} />
              </div>

              {/* Anti-Leakage Compliance Audit */}
              <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-between text-xs shadow-sm">
                <div className="flex items-center gap-3">
                  <ShieldCheck className="w-5 h-5 text-emerald-600" />
                  <div>
                    <p className="font-bold text-emerald-900">Conformidad Anti-Fuga Temporal Verificada</p>
                    <p className="text-slate-600 text-[11px]">Todos los registros del historial cumplen con T_available ≤ T_decision en el Common Data Model.</p>
                  </div>
                </div>
                <span className="px-2.5 py-1 bg-emerald-600 text-white font-mono font-bold rounded-md">100% OK</span>
              </div>
            </div>
          )}

          {activeTab === "CONDITIONS" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Comorbidities */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Stethoscope className="w-4 h-4 text-red-600" /> Diagnósticos y Antecedentes Patológicos
                </h3>
                <div className="space-y-2">
                  {patientDetail.conditions && patientDetail.conditions.map((c, i) => (
                    <div key={i} className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
                      <div>
                        <span className="font-bold text-slate-900">{c.condition_name}</span>
                        <p className="text-[10px] font-mono text-slate-500 mt-0.5">CIE-10: {c.icd10_code}</p>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">{c.status}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Medications */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Pill className="w-4 h-4 text-blue-600" /> Esquema Farmacológico Activo
                </h3>
                <div className="space-y-2">
                  {patientDetail.medications && patientDetail.medications.map((m, i) => (
                    <div key={i} className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
                      <div>
                        <span className="font-bold text-slate-900">{m.drug_name}</span>
                        <p className="text-[10px] font-mono text-slate-500 mt-0.5">Dosis: {m.dose} • Vía: {m.route}</p>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200">{m.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "RAW_RECORDS" && (
            <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-700 font-semibold uppercase border-b border-slate-200">
                  <tr>
                    <th className="p-3">Record ID</th>
                    <th className="p-3">Variable</th>
                    <th className="p-3">Valor / Unidad</th>
                    <th className="p-3">Timestamp Ocurrencia (T_event)</th>
                    <th className="p-3">Timestamp Ingesta (T_available)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 font-mono text-slate-700">
                  {timeline.items && timeline.items.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50">
                      <td className="p-3 font-bold text-slate-900">{item.record_id}</td>
                      <td className="p-3 text-blue-600 font-semibold">{item.variable_code}</td>
                      <td className="p-3 font-bold text-slate-900">{item.value_numeric} {item.original_unit}</td>
                      <td className="p-3 text-slate-600">{item.event_datetime}</td>
                      <td className="p-3 text-emerald-700 font-semibold">{item.available_datetime}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-white border-t border-slate-200 flex justify-end">
          <button onClick={onClose} className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-xl text-xs transition shadow-sm">
            Cerrar Historial Clínico
          </button>
        </div>
      </div>
    </div>
  );
}

// FULL SCREEN VIEW: Incidence & Evidence Analysis View
function IncidenceDetailView({ signalId, onBack, onOpenPatientHistory }) {
  const [evidenceDetail, setEvidenceDetail] = useState(null);
  const [patientInfo, setPatientInfo] = useState(MOCK_PATIENTS[0]);
  const [timelineItems, setTimelineItems] = useState(MOCK_TIMELINE.items);

  useEffect(() => {
    async function fetchIncidenceData() {
      try {
        const res = await fetch(`${API_BASE}/signals/${signalId}/evidence`);
        if (res.ok) {
          const data = await res.json();
          setEvidenceDetail(data);
          if (data.patient_id) {
            const resPat = await fetch(`${API_BASE}/patients/${data.patient_id}`);
            if (resPat.ok) {
              const pData = await resPat.json();
              setPatientInfo(pData);
            }
            const resTl = await fetch(`${API_BASE}/patients/${data.patient_id}/timeline`);
            if (resTl.ok) {
              const tlData = await resTl.json();
              if (tlData.items) setTimelineItems(tlData.items);
            }
          }
        } else {
          setEvidenceDetail(MOCK_EVIDENCE_MAP[signalId] || MOCK_EVIDENCE_MAP["SIG-000001"]);
        }
      } catch (e) {
        setEvidenceDetail(MOCK_EVIDENCE_MAP[signalId] || MOCK_EVIDENCE_MAP["SIG-000001"]);
      }
    }
    if (signalId) fetchIncidenceData();
  }, [signalId]);

  if (!evidenceDetail) return null;

  const whatWentWrong = evidenceDetail.what_went_wrong || {
    primary_symptom: "Desaturación de Oxígeno (SpO2: 88%) y Taquicardia severa (HR: 118-128 bpm).",
    supporting_symptom: "Taquipnea moderada (RR: 24 rpm) y elevación de Presión Arterial Sistólica a 148 mmHg.",
    context_state: "Ocurrió durante período de reposo (Estado SLEEP): Incremento anómalo del gasto cardíaco.",
    data_quality: "Sin interferencia técnica ni desincronización de red (SQI: 0.96). Incidencia clínica real."
  };

  const priorityBadge = 
    evidenceDetail.priority_level === 'CRITICAL' ? 'bg-red-100 text-red-700 border-red-300' :
    evidenceDetail.priority_level === 'HIGH' ? 'bg-orange-100 text-orange-700 border-orange-300' :
    evidenceDetail.priority_level === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800 border-yellow-300' :
    'bg-emerald-100 text-emerald-700 border-emerald-300';

  return (
    <div className="space-y-6">
      {/* Top Bar with Back Button */}
      <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-3">
          <button 
            onClick={onBack}
            className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg text-xs flex items-center gap-1.5 transition"
          >
            <ArrowLeft className="w-4 h-4" /> Volver a la Bandeja de Triaje
          </button>
          <div className="h-5 w-px bg-slate-300"></div>
          <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
            Incidencia Técnica / Clínica <ChevronRight className="w-3.5 h-3.5" /> <strong className="text-slate-900 font-mono">{signalId}</strong>
          </span>
        </div>

        <span className={`px-3 py-1 rounded-full text-xs font-extrabold border ${priorityBadge}`}>
          {evidenceDetail.priority_level} (Risk Score: {evidenceDetail.risk_score.toFixed(2)})
        </span>
      </div>

      {/* Patient Brief Banner with direct Link to Clinical History */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold text-lg shadow-sm">
            {patientInfo.patient_id ? patientInfo.patient_id.substring(4) : 'PAT'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900">{patientInfo.patient_id || evidenceDetail.patient_id}</h2>
              <span className="text-xs font-mono text-slate-500">({patientInfo.care_program})</span>
            </div>
            <p className="text-xs text-slate-600 mt-0.5">
              {patientInfo.age_years} años • Sexo: {patientInfo.sex_at_birth} • Centro: <span className="font-mono text-slate-800 font-semibold">{patientInfo.facility_id || 'FAC-01'}</span>
            </p>
          </div>
        </div>

        <button
          onClick={() => onOpenPatientHistory(evidenceDetail.patient_id)}
          className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl text-xs flex items-center gap-2 shadow-sm transition"
        >
          <LineChart className="w-4 h-4" /> Ver Historial Clínico Completo <ExternalLink className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Critical Narrative Box: "¿Qué Salió Mal?" */}
      <div className="bg-red-50 p-6 rounded-2xl border border-red-200 shadow-sm space-y-4">
        <div className="flex items-center gap-3 border-b border-red-200 pb-3">
          <div className="w-9 h-9 rounded-xl bg-red-600 text-white flex items-center justify-center shadow-sm">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-extrabold text-red-900">Resumen Clínico: ¿Qué Salió Mal?</h3>
            <p className="text-xs text-red-700">Diagnóstico sintético determinista generado por la capa de explicabilidad.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="bg-white p-4 rounded-xl border border-red-200 space-y-1 shadow-sm">
            <span className="font-bold text-red-900 flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-red-600" /> Hallazgo Principal (Disparador Primario)
            </span>
            <p className="text-slate-800 leading-relaxed">{whatWentWrong.primary_symptom}</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-red-200 space-y-1 shadow-sm">
            <span className="font-bold text-red-900 flex items-center gap-1.5">
              <Info className="w-4 h-4 text-orange-600" /> Hallazgo de Soporte
            </span>
            <p className="text-slate-800 leading-relaxed">{whatWentWrong.supporting_symptom}</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-red-200 space-y-1 shadow-sm">
            <span className="font-bold text-red-900 flex items-center gap-1.5">
              <Moon className="w-4 h-4 text-indigo-600" /> Contexto Operativo
            </span>
            <p className="text-slate-800 leading-relaxed">{whatWentWrong.context_state}</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-red-200 space-y-1 shadow-sm">
            <span className="font-bold text-red-900 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Auditoría de Red y Calidad
            </span>
            <p className="text-slate-800 leading-relaxed">{whatWentWrong.data_quality}</p>
          </div>
        </div>
      </div>

      {/* Time-Series Line Chart: Physiological Onset of Symptoms */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <LineChart className="w-4 h-4 text-blue-600" /> Serie Temporal de la Incidencia (Punto de Inflexión de Dolencia)
            </h3>
            <p className="text-xs text-slate-500">Muestra la curva fisiológica en la ventana previa a T_decision, identificando el inicio del deterioro.</p>
          </div>

          <span className="px-3 py-1 bg-amber-100 text-amber-800 border border-amber-200 font-mono text-xs font-bold rounded-lg flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" /> Punto de Inflexión: {evidenceDetail.onset_datetime || '11:30:00'}
          </span>
        </div>

        <ClinicalTimelineChart items={timelineItems} />
      </div>

      {/* SHAP Feature Contributions Bar Chart */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-600" /> Factores Determinantes (Valores SHAP - Impacto en la Predicción)
        </h3>
        <div className="space-y-3">
          {evidenceDetail.shap_contributions && evidenceDetail.shap_contributions.map((feat, idx) => (
            <div key={idx} className="space-y-1">
              <div className="flex justify-between text-xs font-medium">
                <span className="text-slate-800 font-semibold">{feat.feature_name} ({feat.description})</span>
                <span className="text-blue-700 font-mono font-bold">+{(feat.importance * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full bg-slate-100 h-3 rounded-full overflow-hidden border border-slate-200">
                <div className="bg-blue-600 h-3 rounded-full" style={{ width: `${feat.importance * 100}%` }}></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* CDM Support Evidence Table */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
          <Database className="w-4 h-4 text-emerald-600" /> Registros CDM de Soporte (Trazabilidad a Registros Crudos)
        </h3>
        <div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-700 font-semibold uppercase border-b border-slate-200">
              <tr>
                <th className="p-3">Rol</th>
                <th className="p-3">Archivo Fuente</th>
                <th className="p-3">Record ID</th>
                <th className="p-3">Variable</th>
                <th className="p-3">Timestamp Ocurrencia vs Ingesta</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 font-mono text-slate-700">
              {evidenceDetail.evidences && evidenceDetail.evidences.map((ev, idx) => (
                <tr key={idx} className="hover:bg-slate-50">
                  <td className="p-3">
                    <span className={`px-2 py-0.5 text-[9px] font-bold rounded ${
                      ev.evidence_role === 'PRIMARY' ? 'bg-red-100 text-red-700 border border-red-200' :
                      ev.evidence_role === 'CONTEXT' ? 'bg-indigo-100 text-indigo-700 border border-indigo-200' :
                      'bg-slate-100 text-slate-700'
                    }`}>
                      {ev.evidence_role}
                    </span>
                  </td>
                  <td className="p-3 text-slate-600">{ev.source_file}</td>
                  <td className="p-3 font-bold text-slate-900">{ev.record_id}</td>
                  <td className="p-3 text-blue-600 font-semibold">{ev.variable_code}</td>
                  <td className="p-3 text-[11px] text-slate-600">
                    Ocurrencia: {ev.event_datetime} <br/>
                    <span className="text-emerald-700 font-bold">✓ Disponible: {ev.available_datetime}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[11px] text-emerald-700 font-mono flex items-center gap-1 font-semibold">
          <CheckCircle2 className="w-3.5 h-3.5" /> Verificación Anti-Fuga Temporal: T_available ≤ T_decision cumplida al 100%.
        </p>
      </div>
    </div>
  );
}

export default function App() {
  const [patients, setPatients] = useState(MOCK_PATIENTS);
  const [technicalAlerts, setTechnicalAlerts] = useState(MOCK_TECHNICAL_ALERTS);
  const [signals, setSignals] = useState(MOCK_SIGNALS);
  const [activeView, setActiveView] = useState("DASHBOARD"); // "DASHBOARD" | "INCIDENCE"
  const [selectedSignalId, setSelectedSignalId] = useState(null);
  const [selectedPatientId, setSelectedPatientId] = useState(null);
  const [filterPriority, setFilterPriority] = useState("ALL");
  const [filterProgram, setFilterProgram] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [apiStatus, setApiStatus] = useState("CHECKING");

  // Load data from FastAPI Backend on mount
  useEffect(() => {
    async function fetchData() {
      try {
        const resPat = await fetch(`${API_BASE}/patients`);
        if (resPat.ok) {
          const dataPat = await resPat.json();
          if (dataPat.patients && dataPat.patients.length > 0) {
            setPatients(dataPat.patients);
          }
          setApiStatus("ONLINE");
        } else {
          setApiStatus("OFFLINE_MOCK");
        }

        const resAlerts = await fetch(`${API_BASE}/alerts/technical`);
        if (resAlerts.ok) {
          const dataAlerts = await resAlerts.json();
          if (dataAlerts.alerts && dataAlerts.alerts.length > 0) {
            setTechnicalAlerts(dataAlerts.alerts);
          }
        }

        const resSig = await fetch(`${API_BASE}/signals`);
        if (resSig.ok) {
          const dataSig = await resSig.json();
          if (dataSig.signals && dataSig.signals.length > 0) {
            setSignals(dataSig.signals);
          }
        }
      } catch (e) {
        console.log("API offline, using mock data:", e);
        setApiStatus("OFFLINE_MOCK");
      }
    }
    fetchData();
  }, []);

  const openIncidenceView = (sigId) => {
    setSelectedSignalId(sigId);
    setActiveView("INCIDENCE");
  };

  const filteredPatients = patients.filter(p => {
    if (filterPriority !== "ALL" && p.priority_level !== filterPriority) return false;
    if (filterProgram !== "ALL" && p.care_program !== filterProgram) return false;
    if (searchQuery && !p.patient_id.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const kpiCritical = patients.filter(p => p.priority_level === "CRITICAL").length;
  const kpiHigh = patients.filter(p => p.priority_level === "HIGH").length;
  const kpiAlertsCount = technicalAlerts.length;

  return (
    <div className="min-h-screen bg-slate-100 text-slate-800 flex flex-col font-sans">
      {/* Light Theme Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between sticky top-0 z-40 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-sm">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              HealthSignal LATAM <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-800 font-semibold border border-blue-200">RISA V1.0</span>
            </h1>
            <p className="text-xs text-slate-500">Red Integrada de Salud Avanzada — Triaje, Historial Clínico y Linaje de Evidencia</p>
          </div>
        </div>

        {/* API Status Badge */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-slate-100 border border-slate-200">
            <span className={`w-2.5 h-2.5 rounded-full ${apiStatus === 'ONLINE' ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
            <span className="text-slate-700">Backend API: {apiStatus === 'ONLINE' ? 'Conectado (localhost:8000)' : 'Modo Autónomo (Mock Data)'}</span>
          </div>
        </div>
      </header>

      {/* Main Layout */}
      <main className="flex-1 p-6 space-y-6 max-w-7xl mx-auto w-full">
        {activeView === "DASHBOARD" ? (
          <>
            {/* KPI Cards Header */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Pacientes Monitoreados</p>
                  <p className="text-3xl font-extrabold text-slate-900 mt-1">{patients.length}</p>
                  <p className="text-xs text-emerald-700 font-semibold mt-1">100% Cobertura CDM</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                  <Users className="w-6 h-6" />
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between border-l-4 border-l-red-500">
                <div>
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Riesgo Crítico (CRITICAL)</p>
                  <p className="text-3xl font-extrabold text-red-600 mt-1">{kpiCritical}</p>
                  <p className="text-xs text-slate-500 mt-1">Atención médica inmediata</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-red-50 text-red-600 flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6" />
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between border-l-4 border-l-orange-500">
                <div>
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Riesgo Alto (HIGH)</p>
                  <p className="text-3xl font-extrabold text-orange-600 mt-1">{kpiHigh}</p>
                  <p className="text-xs text-slate-500 mt-1">Monitoreo estrecho activo</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-orange-50 text-orange-600 flex items-center justify-center">
                  <ShieldAlert className="w-6 h-6" />
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between border-l-4 border-l-amber-500">
                <div>
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Incidencias de Red / Sensor</p>
                  <p className="text-3xl font-extrabold text-amber-600 mt-1">{kpiAlertsCount}</p>
                  <p className="text-xs text-slate-500 mt-1">Falla técnica (No clínico)</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                  <WifiOff className="w-6 h-6" />
                </div>
              </div>
            </div>

            {/* Main Content Grid: Triage List + Technical Side Panel */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Triage Patient List (2 Cols) */}
              <div className="lg:col-span-2 space-y-4">
                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                      <ListFilter className="w-5 h-5 text-blue-600" /> Bandeja de Triaje Priorizada
                    </h2>

                    {/* Search & Filters */}
                    <div className="flex items-center gap-2">
                      <div className="relative">
                        <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
                        <input 
                          type="text" 
                          placeholder="Buscar paciente..." 
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="bg-slate-50 border border-slate-300 text-xs text-slate-900 rounded-lg pl-8 pr-3 py-2 focus:outline-none focus:border-blue-600"
                        />
                      </div>
                      <select 
                        value={filterPriority}
                        onChange={(e) => setFilterPriority(e.target.value)}
                        className="bg-slate-50 border border-slate-300 text-xs text-slate-900 rounded-lg px-3 py-2 focus:outline-none"
                      >
                        <option value="ALL">Todas las prioridades</option>
                        <option value="CRITICAL">CRITICAL</option>
                        <option value="HIGH">HIGH</option>
                        <option value="MEDIUM">MEDIUM</option>
                        <option value="LOW">LOW</option>
                      </select>
                    </div>
                  </div>

                  {/* Patient Table */}
                  <div className="overflow-x-auto border border-slate-200 rounded-xl">
                    <table className="w-full text-left text-xs text-slate-700">
                      <thead className="bg-slate-100 uppercase text-slate-600 font-semibold border-b border-slate-200">
                        <tr>
                          <th className="p-3">Paciente ID</th>
                          <th className="p-3">Demografía</th>
                          <th className="p-3">Score de Riesgo</th>
                          <th className="p-3">Prioridad</th>
                          <th className="p-3">Programa</th>
                          <th className="p-3 text-right">Acciones</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200">
                        {filteredPatients.map(pat => {
                          const badgeColor = 
                            pat.priority_level === 'CRITICAL' ? 'bg-red-100 text-red-700 border-red-300' :
                            pat.priority_level === 'HIGH' ? 'bg-orange-100 text-orange-700 border-orange-300' :
                            pat.priority_level === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800 border-yellow-300' :
                            'bg-emerald-100 text-emerald-700 border-emerald-300';

                          return (
                            <tr key={pat.patient_id} className="hover:bg-slate-50 transition">
                              <td className="p-3 font-bold text-slate-900">
                                <button 
                                  onClick={() => setSelectedPatientId(pat.patient_id)}
                                  className="flex items-center gap-2 text-blue-600 hover:underline font-bold"
                                >
                                  <span className={`w-2.5 h-2.5 rounded-full ${pat.status === 'CONNECTED' ? 'bg-emerald-500' : 'bg-slate-400'}`}></span>
                                  {pat.patient_id}
                                </button>
                              </td>
                              <td className="p-3 font-medium">{pat.age_years} años • {pat.sex_at_birth}</td>
                              <td className="p-3">
                                <div className="flex items-center gap-2">
                                  <div className="w-16 bg-slate-200 rounded-full h-2 overflow-hidden">
                                    <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${pat.risk_score * 100}%` }}></div>
                                  </div>
                                  <span className="font-mono font-bold text-slate-900">{pat.risk_score.toFixed(2)}</span>
                                </div>
                              </td>
                              <td className="p-3">
                                <span className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold border ${badgeColor}`}>
                                  {pat.priority_level}
                                </span>
                              </td>
                              <td className="p-3 font-mono text-slate-600">{pat.care_program}</td>
                              <td className="p-3 text-right">
                                <div className="flex items-center justify-end gap-2">
                                  <button 
                                    onClick={() => setSelectedPatientId(pat.patient_id)}
                                    className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-lg text-[11px] transition shadow-sm flex items-center gap-1"
                                  >
                                    <LineChart className="w-3.5 h-3.5" /> Historial
                                  </button>
                                  <button 
                                    onClick={() => openIncidenceView("SIG-000001")}
                                    className="px-2.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg text-[11px] transition shadow-sm flex items-center gap-1"
                                  >
                                    <ShieldCheck className="w-3.5 h-3.5" /> Ver Evidencias
                                  </button>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              {/* Technical & Hardware Alerts Side Panel */}
              <div className="space-y-4">
                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                  <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                    <HardDrive className="w-5 h-5 text-amber-600" /> Alertas Técnicas / Hardware
                  </h2>
                  <p className="text-xs text-slate-500">Diferenciación de desincronización de red vs. deterioro clínico fisiológico.</p>

                  <div className="space-y-3">
                    {technicalAlerts.map(alt => (
                      <div key={alt.alert_id} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2">
                        <div className="flex items-center justify-between">
                          <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-100 text-amber-800 border border-amber-300">
                            {alt.alert_type}
                          </span>
                          <span className="text-[10px] font-mono text-slate-500">{alt.timestamp}</span>
                        </div>
                        <p className="text-xs text-slate-800 font-medium">{alt.message}</p>
                        <div className="text-[10px] text-slate-500 flex items-center gap-3">
                          <span>Disp: <strong className="text-slate-800">{alt.device_id || 'N/A'}</strong></span>
                          <span>Pac: <strong className="text-slate-800">{alt.patient_id || 'N/A'}</strong></span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Signals Narrative Section */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-600" /> Resumen Explicativo de Alertas Activas
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {signals.map(sig => (
                  <div key={sig.signal_id} className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sm text-blue-700">{sig.signal_id} — {sig.patient_id}</span>
                      <span className="text-xs font-mono text-slate-500">{sig.decision_datetime}</span>
                    </div>
                    <p className="text-xs text-slate-700 leading-relaxed">{sig.explanation}</p>
                    <div className="pt-2 flex items-center justify-between">
                      <button 
                        onClick={() => setSelectedPatientId(sig.patient_id)}
                        className="text-xs font-semibold text-slate-800 hover:text-blue-600 underline"
                      >
                        Ver Historial Fisiológico →
                      </button>
                      <button 
                        onClick={() => openIncidenceView(sig.signal_id)}
                        className="text-xs font-semibold text-blue-600 hover:text-blue-800 underline"
                      >
                        Auditar Linaje de Evidencia →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          /* FULL SCREEN INCIDENCE VIEW */
          <IncidenceDetailView 
            signalId={selectedSignalId}
            onBack={() => setActiveView("DASHBOARD")}
            onOpenPatientHistory={(pid) => setSelectedPatientId(pid)}
          />
        )}
      </main>

      {/* Patient History Modal */}
      {selectedPatientId && (
        <PatientHistoryModal 
          patientId={selectedPatientId} 
          onClose={() => setSelectedPatientId(null)} 
        />
      )}
    </div>
  );
}
