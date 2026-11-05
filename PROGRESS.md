# PROGRESS — CASO16

## Estado de esta entrega
- **VERIFICADO:** lectura de CASO16.docx y Prompt.docx; requisitos R01–R06 identificados.
- **VERIFICADO:** capa persistente SQLAlchemy con PostgreSQL como destino de Docker Compose y SQLite local explícito como fallback de demostración.
- **VERIFICADO:** seed sintético etiquetado; motor determinista de reglas R01–R06; score explicable 0–100.
- **VERIFICADO:** dashboard, inventario, filtros, hallazgos, ciclo de estados, auditoría append-only y exportación XLSX/DOCX/PDF.
- **VERIFICADO:** API FastAPI versionada para health, dashboard, cuentas, hallazgos, escaneos y actualización de hallazgos.
- **VERIFICADO:** definición JSON de automatización n8n y contrato opcional de LangFlow.
- **PARCIAL:** login/RBAC de demostración en UI; el backend API requiere integrar autenticación real antes de producción.
- **PARCIAL:** historial de tendencias, excepciones versionadas, tickets externos y adjuntos no implementados.
- **BLOQUEADO:** validación real AD/LDAP, n8n/LangFlow/LLM y Docker en esta máquina; Docker Desktop no tiene el daemon activo.

## Pruebas ejecutadas
- `python -m py_compile app.py data_layer.py main.py` — OK.
- `python -m unittest discover -s tests -v` — 3 pruebas OK.
- Smoke test de `data_layer`: seed de 12 cuentas y ejecución determinista de 22 hallazgos — OK.
- AppTest Streamlit login/dashboard/reportes — OK.
- Smoke HTTP FastAPI: health/dashboard/accounts/findings/scan/patch — OK.
- `docker compose config --quiet` — OK; ejecución de contenedores bloqueada por daemon Docker detenido.
- Frontend React shell creado; `npm install`/build no verificado porque npm fue bloqueado por permisos EPERM en su caché global.

## Limitaciones
No se declaran conexiones externas, cumplimiento ISO 27001 ni métricas de producción. La fuente demo es sintética y todas las acciones privilegiadas sobre directorios reales requieren aprobación humana.
