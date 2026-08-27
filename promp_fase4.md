# PROMPT MAESTRO: Implementación de la API de Servicios y Dashboard Clínico con Linaje de Evidencia (Fase 4)

## 1. Contexto y Objetivo del Sistema
- **Proyecto:** HealthSignal LATAM — Red Integrada de Salud Avanzada (RISA Data V1.0)[cite: 1, 2]
- **Estado Actual:** 
  - La **Fase 1** (Ingesta, RAW, Limpieza y CDM en `data/clean/`) está completada[cite: 2].
  - Las **Fases 2 y 3** (Feature Engineering, Modelo Predictivo, Priorización y generación de `results/signals.csv` y `results/evidence.csv`) están operativas[cite: 2].
- **Objetivo:** Construir la **Capa de Visualización y API (Fase 4)**[cite: 2] compuesta por un backend en **FastAPI (`app/`)** y un frontend moderno e interactivo en **React / Vite (`frontend/`)**[cite: 2].
- **Propósito Clínico:** Proveer a los profesionales de la salud un panel de control en tiempo real para:
  1. Monitorear pacientes priorizados por nivel de riesgo (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)[cite: 2].
  2. Diferenciar alertas clínicas (fisiológicas) de alertas técnicas/humanas (desconexión de red, artefactos de señal, batería o pérdida de paquetes)[cite: 1].
  3. Visualizar la serie temporal de signos vitales, analítica de laboratorio y telemetría de wearables con su contexto (ej. sueño/reposo)[cite: 1].
  4. Inspeccionar la **trazabilidad completa y explicabilidad (XAI)** de cada predicción, permitiendo auditar el registro fuente (`record_id`, `source_file`) que detonó la señal clínica[cite: 1, 2].

---

## 2. Especificación Técnica de la API Backend (`app/`)

Implementar los controladores, servicios y esquemas Pydantic en FastAPI según la estructura de carpetas oficial[cite: 2]:

### A. Endpoints Requeridos (`app/api/`)
* **`GET /api/v1/patients`** (`app/api/patients.py`[cite: 2]):
  * Lista pacientes con filtros por `care_program`, `region_type`, `digital_maturity` de la institución y nivel de riesgo actual[cite: 1].
* **`GET /api/v1/patients/{patient_id}`**:
  * Detalle maestro del paciente: demografía (`age_years`, `sex_at_birth`), antecedentes patológicos (`conditions.csv`), medicación activa (`medication_administrations.csv`) y dispositivos asignados[cite: 1].
* **`GET /api/v1/patients/{patient_id}/timeline`**:
  * Serie temporal consolidada que combina signos vitales (`vital_signs.csv`), mediciones de wearables (`wearable_observations.csv`), resultados de laboratorio (`laboratory_results.csv`) e intervalos de contexto (`patient_context.csv`)[cite: 1].
* **`GET /api/v1/signals`** (`app/api/signals.py`[cite: 2]):
  * Consulta de señales de riesgo generadas (`results/signals.csv`), filtrables por `priority_level` (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), rango de fechas y estado de revisión[cite: 2].
* **`GET /api/v1/signals/{signal_id}/evidence`** (`app/api/evidence.py`[cite: 2]):
  * Retorna el grafo de linaje y la lista de registros de soporte desde `results/evidence.csv`[cite: 2]:
    * Cruce directo con el CDM para mostrar `record_id`, `source_file`, `variable_code`, `value_numeric`, `original_unit`, `event_datetime`, `available_datetime` y `evidence_role` (`PRIMARY`, `SUPPORTING`, `CONTEXT`, `QUALITY`)[cite: 1, 2].
* **`GET /api/v1/alerts/technical`**:
  * Lista incidencias de conectividad (`connectivity_events.csv`: `DISCONNECTED`, `DELAYED_SYNC`, `packet_loss_estimate`) y baja calidad de señal (`device_observations.csv`: `SIGNAL_QUALITY_INDEX < 0.85` o `reliability_class == 'R3_VARIABLE'`)[cite: 1].

### B. Servicios y Schemas (`app/services/`, `app/schemas/`[cite: 2])
* Lectura optimizada sobre DuckDB/SQLite apuntando a `data/clean/`, `data/features/` y `results/`[cite: 2].
* Modelos Pydantic con validación estricta de tipos para respuestas y serialización ISO de fechas (`YYYY-MM-DDTHH:MM:SS`)[cite: 2].

---

## 3. Especificación Técnica del Frontend (`frontend/`)

Desarrollar una aplicación SPA en **React + TypeScript + Tailwind CSS / Shadcn UI + Lucide Icons + Recharts/ECharts**[cite: 2]:

### Vista 1: Centro de Mando y Triaje de Pacientes (Triage Dashboard)
* **KPIs Globales en la cabecera:** Total de pacientes monitoreados, pacientes en estado `CRITICAL`/`HIGH`, alertas técnicas activas (desconexiones) y tasa de sincronización de red[cite: 1, 2].
* **Bandeja de Pacientes Priorizados:**
  * Tabla/Tarjetas ordenadas descendentemente por `risk_score` (0.0 a 1.0) con código de colores (Rojo: `CRITICAL`, Naranja: `HIGH`, Amarillo: `MEDIUM`, Verde: `LOW`)[cite: 2].
  * Indicadores de estado: Dispositivo conectado vs. desconectado, última sincronización, programa de atención (`HOME_MONITORING`, `HOSPITAL_OBSERVATION`)[cite: 1].
* **Panel Lateral de Alertas Técnicas / Hardware:**
  * Notificaciones diferenciadas de **falla técnica vs. deterioro clínico**:
    * *"Alerta de Hardware: Monitor DEV-00123 con SQI < 0.80 (posible electrodo suelto)"*[cite: 1].
    * *"Alerta de Red: Pérdida de paquetes estimada en 35% en Centro FAC-03"*[cite: 1].

### Vista 2: Detalle Clínico del Paciente (Patient Deep-Dive & Timeline)
* **Perfil del Paciente:** Resumen demográfico, comorbilidades activas (badges para antecedentes cardiovasculares, metabólicos o respiratorios) y esquema farmacológico vigente[cite: 1].
* **Gráficas Multi-Eje de Series Temporales (Timeline Fisiológico):**
  * Gráficas interactivas sincronizadas con zoom y cursor compartido:
    * *Signos Vitales y Wearables:* Curvas de `HR` y `WEARABLE_HR`, `SpO2`, `RR`, Presión Arterial (`SBP`/`DBP`) y Temperatura[cite: 1].
    * *Capa Contextual:* Sombras/bandas visuales de fondo que indiquen períodos de `SLEEP` vs. `AWAKE` según `patient_context.csv`[cite: 1].
    * *Línea de Disponibilidad:* Marcar visualmente el desfase entre el momento de ocurrencia ($T_{\text{event}}$) y el momento de ingesta/disponibilidad ($T_{\text{available}}$)[cite: 1, 2].
  * *Marcadores de Laboratorio:* Puntos discretos en la línea de tiempo con tooltips que muestren valores fuera de rango de referencia (`reference_low` / `reference_high`)[cite: 1].

### Vista 3: Drawer / Modal de Explicabilidad y Linaje de Evidencia (Audit Trail)
Al hacer clic en cualquier `signal_id` o alerta de riesgo[cite: 2]:
* **Factores Determinantes (SHAP / Feature Contribution):** Gráfico de barras horizontales que detalle las variables de mayor impacto en la predicción (ej. *"SpO2_trend_negative_6h (+0.32)", "HR_variability (+0.18)", "History_Cardiovascular (+0.12)"*)[cite: 1, 2].
* **Tabla de Linaje a la Fuente (Evidence Table):**
  * Desglose exacto de los registros que componen la alerta[cite: 2]:
    * Rol (`PRIMARY`, `SUPPORTING`, `CONTEXT`, `QUALITY`)[cite: 1, 2].
    * `source_file` (ej. `vital_signs.csv`, `laboratory_results.csv`)[cite: 1, 2].
    * `record_id` original (ej. `OBS-0000123456`, `LABR-0000089`)[cite: 1, 2].
    * Valor normalizado y unidad (`bpm`, `%`, `degC`, `mmHg`)[cite: 1].
    * Timestamps exactos ($T_{\text{event}}$ vs $T_{\text{available}}$) demostrando cumplimiento de la regla anti-fuga temporal: $T_{\text{available}} \le T_{\text{decision}}$[cite: 1, 2].

---

## 4. Requerimientos de Calidad del Código y Ejecución
1. **API FastAPI:** Código estructurado en arquitectura en capas (`api/`, `services/`, `schemas/`), tipado estricto con Pydantic V2, manejo centralizado de excepciones y documentación Swagger/OpenAPI interactiva en `/docs`[cite: 2].
2. **Frontend React:** Componentes modulares, tipado completo en TypeScript, estados manejados mediante React Query (@tanstack/react-query) para caching y sincronización eficiente con la API.
3. **Mocking y Fallback:** Si la base de datos local está en reposo, proveer datos mock estructurados que sigan exactamente el esquema RISA Data V1.0 para pruebas de UI autónomas[cite: 1, 2].
4. **Instrucciones de Despliegue:** Incluir scripts de ejecución local tanto para backend (`uvicorn app.main:app --reload`) como frontend (`npm run dev`)[cite: 2].