# HealthSignal LATAM — Red Integrada de Salud Avanzada (RISA Data V1.0)

Sistema integral de **ingesta de datos multihospital multinúcleo, integración relacional con PostgreSQL `risa_db`, pipeline de calidad con 13 reglas de integridad, normalización desacoplada, prevención de fuga temporal (*temporal leakage*), trazabilidad de evidencia con valores SHAP y servidor API Backend con Dashboard Clínico** desarrollado para el reto oficial **HealthSignal LATAM**.

El sistema permite ingerir, auditar, limpiar, persistir en PostgreSQL y normalizar flujos de datos heterogéneos provenientes de múltiples instituciones de salud (hospitales de alta complejidad, clínicas, centros de atención primaria, laboratorios, telemetría y wearables), garantizando la estricta conservación de identificadores originales, integridad referencial multinivel, detección de falsos positivos técnicos y trazabilidad clínica explicable.

---

## 🛠️ Declaración de Tecnologías Utilizadas

### **Backend & Motor Principal (Python Stack)**
- **Lenguaje:** Python 3.10+ (compatible con Python 3.13)
- **Framework API REST:** [FastAPI](https://fastapi.tiangolo.com/) `v0.141.1` con validación de contratos en [Pydantic V2](https://docs.pydantic.dev/) `v2.13.4` y servidor ASGI [Uvicorn](https://www.uvicorn.org/) `v0.52.4`.
- **Procesamiento de Datos y Data Lakes:** [Pandas](https://pandas.pydata.org/) `v3.0.5`, [PyArrow](https://arrow.apache.org/docs/python/) `v25.0.1` (formatos Parquet & CSV con encoding UTF-8 BOM), `csv` estándar en streaming por lotes.
- **Multiprocesamiento y Paralelización:** `concurrent.futures.ProcessPoolExecutor` para escalamiento lineal multinúcleo en CPU.

### **Base de Datos & Persistencia Relacional**
- **Motor BD Relacional:** [PostgreSQL 18](https://www.postgresql.org/) (instancia local `risa_db`, esquema dedicado `risa_raw`).
- **Conector y Driver SQL:** [`psycopg2-binary`](https://www.psycopg.org/) `v2.9.12` con soporte para conexiones directas, `RealDictCursor` y `execute_values` para cargas masivas por lotes.
- **Configuración Dinámica:** [`python-dotenv`](https://github.com/theskumar/python-dotenv) para gestión segura de variables de entorno ([`.env`](file:///c:/Users/jose/Desktop/Proyectos/Personales/JIDA/UDAPI/.env)).

### **Machine Learning, Feature Engineering & Explicabilidad**
- **Modelado & Análisis:** [Scikit-Learn](https://scikit-learn.org/) `v1.9.0`, [SciPy](https://scipy.org/) `v1.18.1`, [NumPy](https://numpy.org/) `v2.5.2`.
- **Explicabilidad Clínica & SHAP:** Atribución de importancia de variables (*SHAP contributions*) y análisis determinista de hallazgos.
- **Prevención de Fuga Temporal (*Anti-Leakage Guard*):** Módulo estricto `LeakageGuard` que fuerza la regla inmutable $T_{\text{available}} \le T_{\text{decision}}$.
- **Motor de Falsos Positivos:** Módulo [`ClinicalSummaryService`](file:///c:/Users/jose/Desktop/Proyectos/Personales/JIDA/UDAPI/app/services/clinical_summary_service.py) para la auditoría de calidad de señal (`SIGNAL_QUALITY_INDEX` / SQI < 0.70) y pérdida de paquetes de red (`PACKET_LOSS` / `connectivity_events`).

### **Frontend & Dashboard Clínico SPA**
- **Librería UI & Framework:** [React 18](https://react.dev/) y [Vite](https://vitejs.dev/) Dev Server.
- **Iconografía & Componentes:** [Lucide React](https://lucide.dev/) (`lucide-react`).
- **Visualización de Series Temporales:** [Chart.js](https://www.chartjs.org/) (`chart.js/auto`) para gráficos interactivos minuto a minuto.
- **Estilos:** Vanilla CSS con utilidades TailwindCSS.

### **Calidad de Código y Pruebas Automatizadas**
- **Framework de Pruebas:** [Pytest](https://docs.pytest.org/) `v9.1.1` con medición de cobertura vía `pytest-cov` `v7.1.0` y `coverage` `v7.15.4`.

---

## 1. Requisitos Previos e Instalación

### Requisitos de Sistema
- **Python 3.10+** (probado y verificado en Python 3.13)
- **Node.js 18+** y `npm` (para el servidor dev del frontend)
- **PostgreSQL 18** ejecutándose localmente en el puerto `5432` con la base de datos `risa_db`.

### Instalación de Dependencias Backend y Frontend

```bash
# 1. Crear y activar entorno virtual Python
python -m venv .venv

# En Windows PowerShell:
.\.venv\Scripts\activate
# En Linux/macOS:
source .venv/bin/activate

# 2. Instalar dependencias backend
pip install -r requirements.txt

# 3. Instalar dependencias del frontend
cd frontend
npm install
cd ..
```

---

## 2. Estructura del Proyecto

```text
├── app/                                  # Servidor API Backend FastAPI
│   ├── api/                              # Routers y Endpoints FastAPI
│   │   ├── alerts.py                     # Notificaciones técnicas (red/hardware)
│   │   ├── evidence.py                   # Linaje de evidencia y explicabilidad SHAP
│   │   └── patients.py                   # Pacientes, detalles y timeline
│   ├── schemas/                          # Contratos de Datos Pydantic V2
│   ├── services/                         # Servicios de Lógica de Negocio
│   │   ├── clinical_summary_service.py   # Motor de análisis exacto y prevención de falsos positivos
│   │   ├── data_loader.py                # Conector dinámico a PostgreSQL risa_db
│   │   ├── evidence_service.py           # Servicio de linaje de evidencias
│   │   ├── patient_service.py            # Gestión maestra de pacientes y timeline
│   │   └── signal_service.py             # Servicio de alertas de riesgo
│   └── main.py                           # Aplicación principal FastAPI
├── frontend/                             # Dashboard Clínico en React (Vite SPA)
│   ├── src/
│   │   ├── App.jsx                       # Interfaz SPA con gráficos Chart.js, triaje y evidencias
│   │   └── main.jsx                      # Punto de entrada React 18
│   ├── package.json                      # Dependencias npm
│   └── index.html                        # HTML5 semántico
├── ingestion/                            # Ingesta por Chunks y Adaptadores Multinúcleo
├── pipeline/                             # Pipeline de Limpieza y 13 Reglas de Calidad
├── scripts/                              # Scripts de Carga y Esquema PostgreSQL
│   ├── schema_postgresql.sql             # DDL SQL de las 17 tablas de RISA Data V1.0
│   └── load_risa_to_postgres.py          # Cargador masivo CSV -> PostgreSQL risa_db
├── data/                                 # Datasets Locales (clean/ y raw/)
├── results/                              # Entregables Oficiales (signals.csv, evidence.csv)
├── tests/                                # Suite de Pruebas Automatizadas Pytest
├── run_api.py                            # Lanzador del Servidor API FastAPI
├── run_pipeline.py                       # CLI Ingesta Multinúcleo y Calidad
└── generate_evidence.py                  # CLI Generación de Entregables Oficiales
```

---

## 3. Guía Completa de Compilación y Ejecución del Sistema

El sistema se puede compilar, poblar y ejecutar mediante los siguientes pasos integrales:

### 3.1 Paso 1: Configurar Base de Datos PostgreSQL (`risa_db`)

1. Asegúrate de tener PostgreSQL ejecutándose en `127.0.0.1:5432`.
2. Edita o crea el archivo [`.env`](file:///c:/Users/jose/Desktop/Proyectos/Personales/JIDA/UDAPI/.env) en la raíz del proyecto:
   ```env
   POSTGRES_HOST=127.0.0.1
   POSTGRES_PORT=5432
   POSTGRES_DB=risa_db
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=tu_contraseña
   ```
3. Ejecuta el script de creación de esquemas y carga masiva a PostgreSQL:
   ```powershell
   python scripts/load_risa_to_postgres.py --create-schema
   ```

### 3.2 Paso 2: Ingesta Paralela y Procesamiento de Calidad (Pipeline)

Ejecuta la ingesta multinúcleo para procesar el dataset completo y generar la capa CDM limpia en `data/clean/csv/`:

```powershell
python run_pipeline.py --data-dir 01_RISA_DATA_V1_0 --chunk-size 50000
```

### 3.3 Paso 3: Generación y Validación de Entregables Oficiales

Genera las alertas de riesgo (`results/signals.csv`), construye las evidencias trazables (`results/evidence.csv`) e insértalas en la base de datos PostgreSQL:

```powershell
python generate_evidence.py
```

Para actualizar los registros de `signals` y `evidence` directamente en PostgreSQL `risa_db`:
```powershell
python scratch/load_results_to_postgres.py
```

---

## 4. Ejecución del Servidor Backend y Frontend

### 4.1 Iniciar el Servidor API Backend (FastAPI)

Inicia el servidor REST en `http://localhost:8000`:

```powershell
python run_api.py
```

- **Swagger UI (Documentación interactiva):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 4.2 Iniciar el Dashboard Clínico (React Frontend)

En una terminal independiente, inicia el servidor de desarrollo de Vite:

```powershell
cd frontend
npm run dev
```

Abre tu navegador en **[http://localhost:5173](http://localhost:5173)** para interactuar con la consola de triaje clínico, auditar linajes de evidencia minuto a minuto y verificar el filtro de falsos positivos técnicos.

---

## 5. Prevención de Falsos Positivos y Auditoría Exacta

El módulo [`ClinicalSummaryService`](file:///c:/Users/jose/Desktop/Proyectos/Personales/JIDA/UDAPI/app/services/clinical_summary_service.py) analiza cada señal cruzando los datos relacionales de PostgreSQL:
- **Cifras y Tiempos Exactos:** Extrae valores numéricos precisos (`WEARABLE_HR = 52.36 bpm`, `SpO2 = 88.0%`) y marcas de tiempo de ocurrencia (`T_event`) e ingesta (`T_available`).
- **Filtro de Falsos Positivos:** Evalúa el índice de calidad de señal (`SIGNAL_QUALITY_INDEX` / SQI) y eventos de conectividad (`PACKET_LOSS`). Si el dispositivo presenta `SQI < 0.70` o desconexión de red, clasifica la alerta como **`POSSIBLE_TECHNICAL_FALSE_POSITIVE`**; si la señal es limpia (`SQI ≥ 0.75`), se valida como **`LEGITIMATE_CLINICAL_ALERT`**.

---

## 6. Las 13 Reglas de Validación e Integridad

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

## 7. Ejecución de Pruebas Automatizadas

La suite completa de pruebas unitarias e integración se ejecuta con:

```bash
pytest tests/ -v
```