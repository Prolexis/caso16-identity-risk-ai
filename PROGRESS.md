# PROGRESS — CASO16

## Estado de esta entrega

### 1. Motor de Entrenamiento de Inteligencia Artificial (NUEVO)
- **VERIFICADO:** Implementación del módulo integral de entrenamiento y evaluación en `training_engine.py`, `eda_engine.py`, `training_reports.py` y `training_routes.py`.
- **VERIFICADO:** Análisis Exploratorio de Datos (**EDA**) exhaustivo: resumen estructural, detección de nulos, duplicados, outliers mediante rango intercuartílico (IQR), desbalance de clases de severidad y diagnóstico explícito sobre atributos temporales de Active Directory (`lastLogon` no replicado vs `lastLogonTimestamp` con latencia de hasta 14 días).
- **VERIFICADO:** Limpieza y Preprocesamiento antifuga: imputación de mediana (`SimpleImputer`) y normalización (`StandardScaler`) ajustados **únicamente** sobre el conjunto de entrenamiento (Train). Exclusión estricta de identificadores únicos (`username`, `external_id`, `email`, `id`) y etiquetas normativas de la matriz de características.
- **VERIFICADO:** Partición reproducible **70 % Entrenamiento, 15 % Validación y 15 % Prueba (Blind Test)** con control matemático de no superposición (fuga cero).
- **VERIFICADO:** Parametrización y entrenamiento independiente de 3 modelos:
  - **M1 (Random Forest Classifier):** Supervisado, baseline multiclase, pesos balanceados, búsqueda de hiperparámetros con Optuna (100–600 árboles, profundidad 4–24, hojas 1–10). Condición de parada al completar árboles o presupuesto de tiempo/trials.
  - **M2 (XGBoost Classifier):** Supervisado, boosting con regularización L2 y fallback transparente a `GradientBoostingClassifier`. Búsqueda Optuna (tasa de aprendizaje logarítmica, profundidad 3–10, subsample 0.6–1.0, lambda 1e-3–20). Condición de parada por `early_stopping_rounds=30` en validación.
  - **M3 (Isolation Forest):** Detección no supervisada de anomalías de identidades y privilegios. Generación de score normalizado de anomalía y ranking priorizado de cuentas atípicas. Distinción metodológica estricta: no se reportan métricas supervisadas inventadas.
- **VERIFICADO:** Optimización de hiperparámetros con **Optuna** (sampler TPE, semilla fija 42, registro por trial y curva de convergencia).
- **VERIFICADO:** Evaluación y Comparación rigurosa: matrices de confusión, curvas ROC y Precision-Recall por clase, cálculo de Accuracy, F1-Macro, F1-Ponderado, Precision, Recall y MCC en el conjunto de prueba ciego (15%).
- **VERIFICADO:** Generación y descarga directa de reportes ejecutivos con trazabilidad criptográfica (SHA-256):
  - 📄 **PDF** (ReportLab con gráficos y tablas).
  - 📝 **Word (.docx)** (python-docx con ficha técnica y metodología).
  - 📊 **Excel (.xlsx)** (openpyxl con pestañas de Resumen, Comparativa, M1, M2, M3 y Metodología).
- **VERIFICADO:** Integración full-stack:
  - **Backend FastAPI:** Endpoints REST en `/api/v1/training/eda`, `/api/v1/training/config/defaults`, `/api/v1/training/start`, `/api/v1/training/jobs`, `/api/v1/training/jobs/{job_id}/cancel`, `/api/v1/training/jobs/{job_id}/report`.
  - **Frontend React:** Nueva interfaz interactiva en `frontend/src/TrainingEngine.tsx` con navegación por pestañas, diagrama metodológico visual interactivo, monitorización en vivo, matrices de confusión interactivas y botones de descarga de reportes.
  - **PostgreSQL / SQLite:** Persistencia de experimentos, estados de Optuna y artefactos versionados.

### 2. Módulos Previos Conservados Intactos
- **VERIFICADO:** Requisitos `R01`–`R06` identificados e implementados sobre el Dataset Público SharpHound / BloodHound AD (113 cuentas, 269 hallazgos).
- **VERIFICADO:** Capa persistente SQLAlchemy con PostgreSQL y SQLite local (`data/caso16.db`).
- **VERIFICADO:** Tablero SOC original en React accesible mediante selector superior ("Tablero SOC e Identidades" vs "Motor de Entrenamiento IA").
- **VERIFICADO:** Endpoints `/api/v1/health`, `/dashboard`, `/accounts`, `/findings`, `/scans`, `/policies`, `/audit`, `/tickets`.
- **VERIFICADO:** Automatizaciones n8n y contratos opcionales LangFlow.

## Pruebas Ejecutadas
- `python -m py_compile main.py eda_engine.py training_engine.py training_reports.py training_routes.py` — OK.
- `cd frontend; npm run build` — Build de Vite + TypeScript compilado exitosamente (261ms).
- `pytest -v` — **27 pruebas ejecutadas y 27 aprobadas (100% OK)**:
  - `tests/test_eda_engine.py` (2 tests OK).
  - `tests/test_training_engine.py` (2 tests OK).
  - `tests/test_training_api.py` (3 tests OK).
  - `tests/test_api_v1.py` (1 test OK).
  - `tests/test_reports.py` (5 tests OK).
  - `tests/test_analytics_ui.py` (4 tests OK).
  - `tests/test_core.py` (3 tests OK).
  - `tests/test_ml_engine.py` (7 tests OK).
