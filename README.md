# HealthSignal LATAM — Red Integrada de Salud Avanzada (RISA Data V1.0)

Sistema integral de **ingesta de datos multihospital multinúcleo, pipeline de calidad con 13 reglas de integridad, normalización desacoplada, prevención de fuga temporal (*temporal leakage*) y trazabilidad de evidencia** desarrollado para el reto oficial **HealthSignal LATAM**.

El sistema permite ingerir, auditar, limpiar y normalizar flujos de datos heterogéneos provenientes de múltiples instituciones de salud (hospitales de alta complejidad, clínicas, centros de atención primaria, laboratorios, telemetría y wearables), garantizando la estricta conservación de identificadores originales, integridad referencial multinivel y trazabilidad clínica explicable.

---

## 1. Requisitos Previos e Instalación

### Requisitos
- **Python 3.10** o superior (probado en Python 3.13)
- Entorno virtual recomendado (`.venv`)

### Instalación de Dependencias
Clona el repositorio e instala los paquetes necesarios:

```bash
# 1. Crear y activar entorno virtual (opcional pero recomendado)
python -m venv .venv

# En Windows:
.venv\Scripts\activate
# En Linux/macOS:
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt
```

---

## 2. Estructura del Proyecto

```text
├── Documentación/                        # Guías técnicas y arquitectura oficial
│   ├── 01_Guia_Tecnica_Oficial_Participantes_HealthSignal_LATAM.md
│   ├── 02_Arquitectura_Sistema_Ingesta.md
│   ├── 03_Arquitectura_Base_de_Datos_RISA.md
│   └── 04_Plan_Implementacion_Ingesta.md
├── ingestion/                            # Módulo de Ingesta por Chunks y Adaptadores
│   ├── models.py                         # Modelos canónicos RawRecord, CDMRecord y AuditEntry
│   ├── base_adapter.py                   # Interfaz abstracta BaseHospitalAdapter
│   ├── factory.py                        # HospitalIngestionFactory (Patrón Factory dinámico)
│   ├── csv_adapter.py                    # RISACSVAdapter (Lector por chunks de 50k registros)
│   ├── sinks.py                          # RawStorageSink, CleanStorageSink y AuditStorageSink (con append)
│   └── orchestrator.py                   # IngestionOrchestrator (Orquestador multinúcleo ProcessPoolExecutor)
├── pipeline/                             # Pipeline Común de Limpieza y Calidad (13 Reglas)
│   ├── validation.py                     # SchemaValidator (Validación de contratos de campos)
│   ├── integrity.py                      # SystemIntegrityValidator (13 Reglas de Integridad Referencial)
│   ├── cleaning.py                       # DataCleaner (Deduplicación y missingness no destructivo)
│   ├── normalization.py                  # UnitNormalizer y PlausibilityChecker
│   ├── contextualizer.py                 # Contextualizer (Cruce con estado de sueño y red con índices O(1))
│   ├── temporal.py                       # TemporalProcessor (Alineación de timelines y latencias)
│   └── leakage_guard.py                  # LeakageGuard (Prevención de fuga temporal T_available <= T_decision)
├── evidence/                             # Módulo de Explicabilidad y Trazabilidad de Evidencias
│   ├── evidence_builder.py               # EvidenceBuilder (Categorización PRIMARY, SUPPORTING, CONTEXT, QUALITY)
│   ├── explanation_builder.py            # ExplanationBuilder (Generación de narrativa clínica determinista)
│   ├── lineage.py                        # LineageTracker (Trazabilidad de características a registros crudos)
│   └── validator.py                      # SubmissionValidator (Validador oficial de señales y evidencias)
├── data/                                 # Capas de Almacenamiento Local
│   ├── raw/                              # Copias inmutables de payloads crudos (JSONL)
│   ├── clean/                            # Registros limpios en formato CDM (CSV y JSONL en data/clean/csv)
│   └── logs/                             # Log unificado de auditoría de incidencias (ingestion_processing.log)
├── results/                              # Entregables Oficiales de Salida
│   ├── signals.csv                       # Alertas de riesgo con risk_score, prioridad y explicación clínica
│   └── evidence.csv                      # Desglose de evidencias trazables por registro de origen
├── tests/                                # Suite de Pruebas Automatizadas (100% Cobertura)
│   ├── test_ingestion.py                 # Tests de adaptadores y fábrica
│   ├── test_streaming_ingestion.py       # Tests de ingesta en streaming por chunks
│   ├── test_parallel_ingestion.py        # Tests de ingesta paralela multinúcleo
│   ├── test_cleaning_and_units.py        # Tests de deduplicación y conversión de unidades
│   ├── test_temporal_leakage.py          # Tests de control de latencias y Leakage Guard
│   └── test_end_to_end.py                # Test de integración end-to-end
├── run_pipeline.py                       # CLI principal de ingesta y validación de calidad
├── generate_evidence.py                  # CLI unificado para generar y validar results/
├── validate_submission.py                # Validador oficial de los entregables finalizados
├── requirements.txt                      # Lista oficial de dependencias
└── README.md                             # Guía de uso y documentación oficial
```

---

## 3. Guía de Ejecución del Sistema

El flujo de ejecución consta de **dos comandos principales**: ingesta acelerada multinúcleo y generación/validación de entregables.

### 3.1 Paso 1: Ingesta Paralela Multinúcleo y Validación de Calidad

Ejecuta el pipeline de ingesta por lotes de 50,000 registros utilizando todos los núcleos de la CPU:

```powershell
python run_pipeline.py --data-dir 01_RISA_DATA_V1_0 --chunk-size 50000
```

#### Opciones de la CLI (`run_pipeline.py`):
| Parámetro | Tipo | Por Defecto | Descripción |
|---|---|:---:|---|
| `--data-dir` | `str` | `01_RISA_DATA_V1_0` | Ruta al directorio raíz del dataset RISA |
| `--chunk-size` | `int` | `50000` | Tamaño de lote/batch en registros por chunk |
| `--workers` | `int` | `CPU Cores` | Número de procesos paralelos de trabajo |
| `--no-parallel` | `flag` | `False` | Forzar ejecución mono-hilo secuencial |
| `--max-rows` | `int` | `0` (Sin Límite) | Muestra de filas máximas por tabla (`0` = procesar todo) |
| `--table` | `str` | `all` | Filtro de tabla (`vitals`, `wearables`, `lab`, `all`) |

---

### 3.2 Paso 2: Generación Automática de Entregables y Validación (Un solo comando)

Genera las señales de riesgo (`results/signals.csv`), construye las evidencias trazables (`results/evidence.csv`) y ejecuta el validador oficial con un solo comando:

```powershell
python generate_evidence.py
```

Salida esperada:
```text
===========================================================================
  HEALTHSIGNAL LATAM — GENERADOR DE SEÑALES Y EVIDENCIA CLINICA
  Directorio Datos Limpios: data/clean/csv
  Directorio de Salida:      results
===========================================================================
[OK] 4494733 registros cargados para 1007 pacientes.

[INFO] Generando señales y evidencias por paciente...

[OK] Generación finalizada exitosamente:
  - signals.csv:  results\signals.csv (1000 señales de riesgo)
  - evidence.csv: results\evidence.csv (59138 registros de evidencia trazables)

===========================================================================
  EJECUTANDO VALIDACION AUTOMATICA DE ENTREGABLES (SubmissionValidator)
===========================================================================
[SUCCESS] ¡Validación Exitosa! Los archivos cumplen 100% las especificaciones sin fuga temporal.
===========================================================================
```

---

### 3.3 Paso 3 (Opcional): Validación Independiente de los Entregables

Si deseas validar nuevamente la entrega generada en `results/`:

```powershell
python validate_submission.py --signals results/signals.csv --evidence results/evidence.csv
```

---

## 4. Fase 4: Servidor API Backend (FastAPI) y Dashboard Clínico (React SPA)

La **Fase 4** provee una **API REST Backend en FastAPI (`app/`)** y un **Dashboard Clínico Frontend en React (`frontend/`)** con triaje en tiempo real, alertas de red/hardware diferenciadas y auditoría de linaje de evidencias con factores SHAP.

### 4.1 Iniciar el Backend API (FastAPI + Uvicorn)

Para iniciar el servidor backend en `http://localhost:8000`:

```powershell
python run_api.py
```

- **Swagger / OpenAPI interactivo:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc interactivo:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

#### Endpoints Principales:
- `GET /api/v1/patients`: Lista priorizada de pacientes con filtros operacionales (`care_program`, `priority_level`).
- `GET /api/v1/patients/{patient_id}`: Ficha clínica maestra (demografía, comorbilidades, fármacos, dispositivos).
- `GET /api/v1/patients/{patient_id}/timeline`: Serie temporal fisiológica (vitals, wearables, labs, reposo/sueño).
- `GET /api/v1/signals`: Consulta de alertas de riesgo clínico generadas por el modelo predictivo.
- `GET /api/v1/signals/{signal_id}/evidence`: Grafo de linaje de evidencia trazable a registros CDM originales ($T_{\text{available}} \le T_{\text{decision}}$) y contribuciones SHAP.
- `GET /api/v1/alerts/technical`: Notificaciones diferenciadas de fallas de red, pérdida de paquetes y baja calidad de señal.

---

### 4.2 Abrir el Dashboard Clínico (React SPA)

El frontend está listo en **`frontend/index.html`** y no requiere compilación previa:

1. **Opción 1 (Directa):** Abre `frontend/index.html` en cualquier navegador web.
2. **Opción 2 (Servidor Vite):**
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```
   Navega a `http://localhost:5173`.

---

## 5. Las 13 Reglas de Validación e Integridad

El pipeline aplica automáticamente las 13 reglas de calidad clínica e integridad referencial:

| Dominio | Código | Nombre de la Regla | Descripción / Acción |
|---|---|---|---|
| **Estructura** | **ST-01** | Coherencia de Campos Obligatorios | Rechaza filas sin `patient_id` o `timestamp` |
| | **ST-02** | Contrato del CDM | Valida nombres y tipos de columnas estandarizadas |
| **Integridad** | **RI-01** | Existencia del Paciente | Verifica pertenencia a `patients.csv` |
| | **RI-02** | Pertenencia de Encuentro | Asocia mediciones hospitalarias a `encounters.csv` |
| | **RI-03** | Validez del Dispositivo | Mapea observaciones de gateway a `devices.csv` |
| **Unidades** | **UN-01** | Normalización de Unidades | Convierte `degF` $\rightarrow$ `degC` vía `units_catalog.csv` |
| **Plausibilidad** | **PL-01** | Rango Biológico Plausible | Evalúa límites según `variable_catalog.csv` (ej. SpO2: 50-100%) |
| | **PL-02** | Ruido e Interferencias | Penaliza el peso en evidencia de marcas `CHECK` o `LOW_SIGNAL` |
| **Temporal** | **TP-01** | Limites del Encuentro | Detecta mediciones fuera del intervalo de admisión/alta |
| | **TP-02** | Anti-Temporal Leakage | Marca `TEMPORAL_LEAKAGE` si $T_{\text{available}} < T_{\text{event}}$ |
| | **TP-03** | Cronología de Diagnósticos | Valida que fecha de inicio $\le$ fecha de registro |
| **Contexto** | **CX-01** | Interrupción de Red | Etiqueta `NETWORK_INTERRUPTED` ante desincronización de red |
| | **CX-03** | Sueño vs Actividad | Detecta taquicardia o pasos anómalos durante estado `SLEEP` |

---

## 5. Salidas y Almacenamiento de Datos

Tras la ejecución, los datos se encuentran estructurados en:

1. **Capa RAW Inmutable (`data/raw/`)**: Copias inmutables de payloads crudos en formato JSONL con timestamps de recepción.
2. **Capa CLEAN Normalizada (`data/clean/csv/`)**: Datos limpios estandarizados al Common Data Model (CDM).
3. **Log de Auditoría (`data/logs/ingestion_processing.log`)**: Log persistente que detalla el motivo de cada ajuste o bandera de calidad asignada.
4. **Resultados Oficiales (`results/`)**:
   - `signals.csv`: 1,000 alertas de riesgo con severidad y explicaciones narrativas.
   - `evidence.csv`: 59,138 registros de evidencia categorizados (`PRIMARY`, `SUPPORTING`, `CONTEXT`, `QUALITY`).

---

## 6. Ejecución de Pruebas Automatizadas

La suite completa de pruebas unitarias y de integración se ejecuta con:

```bash
# Ejecutar todas las pruebas con pytest
pytest tests/ -v
```

---

## 7. Documentación Adicional

Para más detalles sobre las especificaciones y reglas del reto, consulta la carpeta `Documentación/`:
- [01_Guia_Tecnica_Oficial_Participantes_HealthSignal_LATAM.md](file:///c:/Users/jose/Desktop/Proyectos/Personales/JIDA/UDAPI/Documentaci%C3%B3n/01_Guia_Tecnica_Oficial_Participantes_HealthSignal_LATAM.md)
- [02_Arquitectura_Sistema_Ingesta.md](file:///c:/Users/jose/Desktop/Proyectos/Personales/JIDA/UDAPI/Documentaci%C3%B3n/02_Arquitectura_Sistema_Ingesta.md)
- [03_Arquitectura_Base_de_Datos_RISA.md](file:///c:/Users/jose/Desktop/Proyectos/Personales/JIDA/UDAPI/Documentaci%C3%B3n/03_Arquitectura_Base_de_Datos_RISA.md)
- [04_Plan_Implementacion_Ingesta.md](file:///c:/Users/jose/Desktop/Proyectos/Personales/JIDA/UDAPI/Documentaci%C3%B3n/04_Plan_Implementacion_Ingesta.md)