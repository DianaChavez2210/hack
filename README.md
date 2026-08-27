# HealthSignal LATAM — Red Integrada de Salud Avanzada (RISA Data V1.0)

Sistema integral de **ingesta de datos multihospital, pipeline de calidad, normalización desacoplada y trazabilidad de evidencia** desarrollado para el reto oficial **HealthSignal LATAM**.

El sistema permite ingerir, auditar, limpiar y normalizar flujos de datos heterogéneos provenientes de múltiples instituciones de salud (hospitales de alta complejidad, clínicas, centros de atención primaria, laboratorios, telemetría y wearables), garantizando la conservación de identificadores originales y la estricta prevención de fuga temporal (*temporal leakage*).

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
├── ingestion/                            # Módulo de Ingesta y Adaptadores
│   ├── models.py                         # Modelos canónicos RawRecord, CDMRecord y AuditEntry
│   ├── base_adapter.py                   # Interfaz abstracta BaseHospitalAdapter
│   ├── factory.py                        # HospitalIngestionFactory (Patrón Factory dinámico)
│   ├── csv_adapter.py                    # RISACSVAdapter (Lector universal UTF-8 BOM)
│   ├── mock_adapter.py                   # MockHospitalAdapter (Simulación para tests)
│   ├── sinks.py                          # RawStorageSink, CleanStorageSink y AuditStorageSink
│   └── orchestrator.py                   # IngestionOrchestrator (Coordinador del flujo)
├── pipeline/                             # Pipeline Común de Limpieza y Calidad
│   ├── validation.py                     # SchemaValidator (Validación de contratos)
│   ├── cleaning.py                       # DataCleaner (Deduplicación y missingness no destructivo)
│   ├── normalization.py                  # UnitNormalizer y PlausibilityChecker
│   ├── contextualizer.py                 # Contextualizer (Cruce con sueño y red)
│   ├── temporal.py                       # TemporalProcessor (Alineación de timelines)
│   └── leakage_guard.py                  # LeakageGuard (Prevención de fuga temporal)
├── data/                                 # Capas de Almacenamiento Local
│   ├── raw/                              # Copias inmutables de payloads crudos (JSONL)
│   └── clean/                            # Registros limpios en formato CDM (CSV y JSONL)
├── tests/                                # Suite de Pruebas Automatizadas
│   ├── test_ingestion.py                 # Tests de adaptadores y fábrica
│   ├── test_cleaning_and_units.py        # Tests de deduplicación y conversión de unidades
│   ├── test_temporal_leakage.py          # Tests de control de latencias y Leakage Guard
│   ├── test_end_to_end.py                # Test de integración del orquestador
│   └── test_audit_logging.py             # Test del log de auditoría de decisiones
├── run_pipeline.py                       # CLI principal de ejecución del pipeline
├── requirements.txt                      # Lista oficial de dependencias
└── README.md                             # Guía de uso y documentación
```

---

## 3. Guía de Uso del Programa

El punto de entrada principal es `run_pipeline.py`, el cual permite ejecutar la ingesta completa o selectiva de las tablas de RISA Data V1.0.

### 3.1 Ejecución Básica (Procesamiento Completo de Datos)
Ejecuta la ingesta de **todos los registros** de todas las tablas del dataset RISA Data V1.0 sin truncamiento:

```bash
python run_pipeline.py
```

### 3.2 Ejecución con Opciones Personalizadas

```bash
# Limitar a una muestra de filas por tabla (ej. 1000 filas para pruebas rápidas)
python run_pipeline.py --max-rows 1000

# Procesar una tabla específica (vitals, wearables, lab_results, conditions, medications, etc.)
python run_pipeline.py --table vitals

# Procesar desde una ruta de datos personalizada
python run_pipeline.py --data-dir 01_RISA_DATA_V1_0
```

### 3.3 Parámetros Disponibles en la CLI

| Parámetro | Tipo | Por Defecto | Descripción |
|---|---|:---:|---|
| `--data-dir` | `str` | `01_RISA_DATA_V1_0` | Directorio raíz donde reside el dataset RISA |
| `--max-rows` | `int` | `0` (Sin Límite) | Número máximo de filas por tabla (`0` = procesar **todos** los datos) |
| `--table` | `str` | `all` | Filtro de tabla (`vitals`, `wearables`, `lab`, `conditions`, `medications`, `all`) |

---

## 4. Salidas y Almacenamiento de Datos

Tras ejecutar la ingesta, los datos se organizan en dos capas persistentes:

1. **Capa RAW Inmutable (`data/raw/`)**:
   - `raw_vital_signs.jsonl`, `raw_wearables.jsonl`, `raw_lab_results.jsonl`, etc.
   - Guarda una copia exacta del payload recibido junto con metadatos de auditoría (`ingestion_timestamp`, `source_file`, `facility_id`).

2. **Capa CLEAN Normalizada (`data/clean/`)**:
   - `vital_signs.csv` / `.jsonl`, `wearables.csv` / `.jsonl`, `lab_results.csv` / `.jsonl`, etc.
   - Registros estandarizados al **Common Data Model (CDM)** con timestamps fisiológicos y operacionales unificados.

3. **Registro de Auditoría de Decisiones (`data/clean/audit_*.csv` y `.jsonl`)**:
   - `audit_vital_signs.csv`, `audit_lab_results.csv`, etc.
   - Registra el **porqué** de cada decisión tomada en el pipeline (duplicados descartados, conversión de unidades, valores biológicamente implausibles, señales ruidosas, datos bloqueados por fuga temporal).

---

## 5. Reglas de Calidad y Principios de Diseño

1. **Missingness No Destructivo**:
   - Los datos faltantes (`null` / `None`) **nunca** se sustituyen por ceros ni por valores normales ficticios. Se preserva el estado nulo con el flag `is_observed = False` para permitir calcular ratios de completitud por paciente.
2. **Normalización de Unidades**:
   - Utiliza `units_catalog.csv` para convertir unidades heterogéneas a estándares canónicos (ej. $\text{degF} \rightarrow \text{degC}$ con factor $0.5556$ y offset $-17.7778$).
3. **Plausibilidad Biológica**:
   - Utiliza `variable_catalog.csv` para evaluar límites biológicos (ej. HR: 20-220 bpm, SpO2: 50-100%). Los valores fuera de rango se etiquetan como `OUT_OF_RANGE` sin ser eliminados ciegamente.
4. **Prevención de Fuga Temporal (*Temporal Leakage Guard*)**:
   - Diferenciación estricta entre $T_{\text{event}}$ (momento fisiológico o toma de muestra) y $T_{\text{available}}$ (momento de resultado o sincronización).
   - Regla de oro: En cualquier decisión en tiempo $T$, solo se puede utilizar evidencia con $T_{\text{available}} \le T$.

---

## 6. Ejecución de Pruebas Automatizadas

El proyecto incluye una suite de pruebas unitarias y de integración:

```bash
# Ejecutar todas las pruebas con pytest
pytest tests/ -v

# O ejecutar individualmente con Python:
python tests/test_ingestion.py
python tests/test_cleaning_and_units.py
python tests/test_temporal_leakage.py
python tests/test_end_to_end.py
python tests/test_audit_logging.py
```

---

## 7. Documentación Adicional

Para más detalles técnicos y especificaciones arquitectónicas, consulta la carpeta `Documentación/`:
- [01_Guia_Tecnica_Oficial_Participantes_HealthSignal_LATAM.md](file:///c:/Users/jose/Desktop/Proyectos/Personales/JIDA/UDAPI/Documentaci%C3%B3n/01_Guia_Tecnica_Oficial_Participantes_HealthSignal_LATAM.md): Reglas oficiales del reto.
- [02_Arquitectura_Sistema_Ingesta.md](file:///c:/Users/jose/Desktop/Proyectos/Personales/JIDA/UDAPI/Documentaci%C3%B3n/02_Arquitectura_Sistema_Ingesta.md): Diseño arquitectónico modular end-to-end.
- [03_Arquitectura_Base_de_Datos_RISA.md](file:///c:/Users/jose/Desktop/Proyectos/Personales/JIDA/UDAPI/Documentaci%C3%B3n/03_Arquitectura_Base_de_Datos_RISA.md): Catálogo y esquema de las 17 tablas de RISA Data V1.0.
- [04_Plan_Implementacion_Ingesta.md](file:///c:/Users/jose/Desktop/Proyectos/Personales/JIDA/UDAPI/Documentaci%C3%B3n/04_Plan_Implementacion_Ingesta.md): Plan técnico de implementación del pipeline.