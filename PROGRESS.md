# PROGRESS — CASO16

## Estado de esta entrega
- **VERIFICADO:** lectura de `CASO16.docx` y `Prompt.docx`; requisitos `R01`–`R06` identificados e implementados.
- **VERIFICADO:** integración y corrida completa sobre **Dataset Público SharpHound / BloodHound Active Directory Telemetry** (`PHANTOM.CORP`, `WRAITH.CORP`, `GHOST.CORP` y `ESC1.LOCAL`, con **113 cuentas de directorio únicas** y sus membresías de grupos LDAP/AD en `data/`).
- **VERIFICADO:** ejecución determinista del motor `R01`–`R06` sobre el dataset público generando **269 hallazgos reales** (`44 Críticos`, `107 Altos`, `118 Medios`; `117 confirmados` y `152 potenciales`) y un riesgo acumulado de **6,671 puntos**.
- **VERIFICADO:** capa persistente SQLAlchemy con PostgreSQL como destino de Docker Compose y SQLite local (`data/caso16.db`) pre-poblada con la corrida del dataset público.
- **VERIFICADO:** dashboard, inventario filtrable, gestión de hallazgos, bitácora append-only y exportación nativa XLSX/DOCX/PDF.
- **VERIFICADO:** API FastAPI versionada (`/api/v1/health`, `/dashboard`, `/accounts`, `/findings`, `/scans` y `PATCH /findings/{id}`).
- **VERIFICADO:** definición JSON de automatización n8n y contrato opcional de LangFlow.

## Resultados de la corrida sobre el Dataset Público (SharpHound / BloodHound AD)
- **Cuentas inventariadas:** 113 (`PHANTOM.CORP`: 53, `WRAITH.CORP`: 40, `ESC1.LOCAL`: 14, `GHOST.CORP`: 6 únicas)
- **Cuentas inactivas / huérfanas (`R01` >= 90 días o `lastLogon=0`):** 81
- **Cuentas con riesgo alto o crítico (`score >= 60`):** 64
- **Cuentas de servicio con contraseña sin expiración (`R04`):** 17
- **Total de hallazgos detectados:** 269
  - `R01` (Inactividad prolongada): 81
  - `R02` (Privilegio administrativo sin justificación): 32
  - `R03` (Cuenta administrativa duplicada): 37
  - `R04` (Contraseña de servicio no expira): 17
  - `R05` (Privilegios inconsistentes): 44
  - `R06` (Riesgo alto sin revisión): 58

## Pruebas ejecutadas
- `python -m py_compile app.py data_layer.py main.py` — OK.
- `python -m unittest discover -s tests -v` — 3 pruebas OK (113 cuentas procesadas).
- `python test_smoke.py`, `python test_reports.py`, `python test_ui.py` — OK.
