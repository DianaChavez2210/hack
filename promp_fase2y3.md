# PROMPT MAESTRO: Implementación de Feature Engineering, Modelado Predictivo y Evidencia Trazable (Fases 2 y 3)

## 1. Contexto del Proyecto y Estado Actual
- **Proyecto:** HealthSignal LATAM — Red Integrada de Salud Avanzada (RISA Data V1.0)
- **Estado Actual:** La **Fase 1 (Ingesta, RAW inmutable, Limpieza, Normalización y CDM)** ya está completada. Los datos limpios residen estructurados en `data/clean/`.
- **Objetivo:** Implementar los módulos correspondientes a las **Fases 2 y 3**:
  1. `pipeline/leakage_guard.py`
  2. Capa `features/` (ingeniería de características multivariables con ventanas temporales).
  3. Capa `model/` (entrenamiento, inferencia, calibración de `risk_score` y `prioritization.py`).
  4. Capa `evidence/` (construcción del grafo de linaje y generación de `results/signals.csv` y `results/evidence.csv`).
  5. Script de orquestación `run_pipeline.py` (actualización para fases analíticas) y pruebas en `tests/`.

---

## 2. Especificación Técnica de los Módulos a Implementar

### A. Guardián Anti-Fuga Temporal (`pipeline/leakage_guard.py`)
- Implementar la clase `LeakageGuard` con el método estricto:
  `filter_available_records(records_df, decision_datetime: datetime) -> pd.DataFrame`
- **Regla inmutable:** Bloquear todo registro donde `available_datetime > decision_datetime`, sin importar el valor de `event_datetime`.

### B. Capa de Feature Engineering (`features/`)
Estructurar la extracción modular de características a partir de `data/clean/`:
- `features/vital_features.py`: Ventanas deslizantes ($W \in \{1\text{h}, 6\text{h}, 24\text{h}\}$) para signos vitales (`HR`, `RR`, `SpO2`, `TEMP`, `SBP`, `DBP`): media, mín, máx, desviación estándar, pendientes ($\Delta \text{valor} / \Delta t$) e índices de shock (ej. $\text{HR} / \text{SBP}$).
- `features/wearable_features.py`: Agregaciones de `WEARABLE_HR`, pasos y conteo de actividad en ventanas equivalentes, cruzando con estados de reposo/sueño (`patient_context.csv`).
- `features/lab_features.py`: Último valor disponible de cada analítica antes de $T_{\text{decision}}$, diferencia contra el rango de referencia (`reference_low`, `reference_high`) y tiempo transcurrido desde el reporte (`result_datetime`).
- `features/temporal_features.py`: Recency de las observaciones (minutos transcurridos desde el último registro de cada variable).
- `features/quality_features.py`: Ratios de missingness por variable en las últimas 6h y promedio de `SIGNAL_QUALITY_INDEX` de los dispositivos involucrados.
- `features/baseline_features.py`: Desviación del paciente respecto a su propia línea base histórica o perfil comórbido (`conditions.csv`).
- `features/feature_builder.py`: Clase `FeatureBuilder` que orquesta los submódulos, aplica el `LeakageGuard` para cada instante de evaluación y genera el dataset consolidado en `data/features/features_matrix.parquet`.

### C. Capa de Modelado y Priorización (`model/`)
- `model/train.py`: Entrenamiento de un modelo clasificador/regresor tabular (**XGBoost** o **LightGBM**) con validación cruzada temporal (*Time-Series Split* o validación por paciente agrupado para evitar filtración entre cortes).
- `model/predict.py`: Clase `RiskPredictor` que carga el artefacto entrenado (`model/artifacts/risk_model.joblib`), ejecuta la inferencia sobre el vector de features y retorna `risk_score` calibrado continuo en el rango $[0.0, 1.0]$.
- `model/prioritization.py`: Función determinista `classify_priority(risk_score: float) -> str` mapeando a:
  - `CRITICAL`: $\ge 0.80$ (o activación de umbrales clínicos de fallo inminente)
  - `HIGH`: $[0.60, 0.80)$
  - `MEDIUM`: $[0.35, 0.60)$
  - `LOW`: $< 0.35$

### D. Trazabilidad de Evidencia y Linaje (`evidence/`)
- `evidence/lineage.py`: Estructura de datos que rastrea qué variables y registros primitivos (`record_id` y `source_file`) construyeron cada feature utilizada por el modelo en el instante $T_{\text{decision}}$.
- `evidence/explanation_builder.py`: Cálculo de valores SHAP (TreeSHAP) o pesos de contribución por feature para extraer los principales factores de riesgo determinantes por paciente.
- `evidence/evidence_builder.py`: Generador de los entregables oficiales:
  1. `results/signals.csv`: Columnas `signal_id`, `patient_id`, `decision_datetime`, `risk_score`, `priority_level`, `primary_reason`.
  2. `results/evidence.csv`: Columnas `signal_id`, `record_id`, `source_file`, `variable_code`, `event_datetime`, `available_datetime`, `evidence_role` (`PRIMARY`, `SUPPORTING`, `CONTEXT`, `QUALITY`).
  - **Validación obligatoria:** Comprobar que en cada fila de `evidence.csv`: `available_datetime <= decision_datetime`.

### E. Pruebas y Validación (`tests/`)
- `tests/test_leakage.py`: Tests unitarios que inyectan registros con $T_{\text{available}} > T_{\text{decision}}$ y validan que el sistema lance excepción o los excluya al 100%.
- `tests/test_features.py`: Validación de consistencia matemática en ventanas móviles y cálculo de pendientes.
- `tests/test_evidence.py`: Validación de integridad referencial entre `signals.csv` y `evidence.csv` (todo `signal_id` debe tener al menos una evidencia `PRIMARY`).

---

## 3. Requerimientos de Salida y Formato del Código
1. Escribir código Python 3.10+ limpio, modular, completamente tipado (`typing`) y documentado.
2. Utilizar `pandas`, `numpy`, `polars` / `duckdb`, `scikit-learn`, `xgboost`, `shap` y `joblib`.
3. Mantener el desacoplamiento estricto según la estructura de carpetas oficial definida en `02_Arquitectura_Sistema_Ingesta.md`.
4. Incluir el script actualizado `run_pipeline.py` que permita ejecutar de principio a fin las fases analíticas y generar los CSVs en `results/`.