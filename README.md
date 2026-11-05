# CASO16 — Plataforma de detección de cuentas huérfanas y privilegios excesivos

MVP ejecutable derivado de `CASO16.docx` y `Prompt.docx`. Incluye una interfaz Streamlit para demostración operacional y una API FastAPI versionada. El diseño mantiene el motor determinista separado de la UI y deja preparados PostgreSQL, n8n y LangFlow como integraciones configurables.

## Qué funciona

- Inventario sintético de cuentas Demo AD/Demo LDAP (12 registros).
- Reglas R01–R06 con evidencia, estado confirmado/potencial y score 0–100.
- Dashboard con KPIs calculados desde la base, inventario filtrable y hallazgos trazables.
- Actualización de estado/responsable/comentario con bitácora append-only.
- Reportes reales XLSX, DOCX y PDF.
- API: `/api/v1/health`, `/dashboard`, `/accounts`, `/findings`, `/scans` y `PATCH /findings/{id}`.
- Plantilla exportable n8n y contrato opcional de LangFlow.
- Shell React/TypeScript/Vite en `frontend/`, con degradación offline y consumo opcional de la API; su build requiere instalar dependencias npm.

## Ejecución local rápida

Requiere Python 3.11. En Windows se recomienda `py -3.11`.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```

Abrir `http://localhost:8501`. Usuarios sintéticos: `analyst@demo.local`, `security@demo.local` o `auditor@demo.local`; contraseña: `demo`.

API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

La ejecución local crea `data/caso16.db` como fallback explícito de demostración. No usar ese fallback como persistencia productiva.

## Docker Compose / PostgreSQL

Con Docker Desktop iniciado:

```powershell
docker compose up --build
```

- UI: `http://localhost:8501`
- API documentada: `http://localhost:8000/docs`
- PostgreSQL: volumen `caso16_pgdata`

El contenedor de la app está configurado para PostgreSQL mediante `DATABASE_URL`. En la máquina de análisis Docker estaba instalado, pero el daemon no estaba activo; por eso el compose queda preparado pero no se declara verificado.

## Seguridad y alcance

La demo no conecta a AD/LDAP, no envía secretos a un LLM y no ejecuta desactivaciones, cambios de contraseña ni revocaciones. Antes de producción hay que añadir autenticación real/RBAC backend, MFA/SSO, TLS, rate limiting, gestión de secretos, migraciones Alembic, conectores LDAP/AD de solo lectura, integración n8n/LangFlow y pruebas de seguridad.

La alineación con A.8.2 es una referencia de diseño; no constituye certificación ni evaluación de conformidad ISO/IEC 27001.

## Archivos principales

- `app.py`: dashboard Streamlit y flujo operativo.
- `data_layer.py`: esquema, seed, reglas, score, auditoría y reportes fuente.
- `main.py`: API FastAPI.
- `docker-compose.yml`, `Dockerfile`, `requirements.txt`: despliegue reproducible.
- `PROGRESS.md`: estado, evidencia y bloqueos.
- `automation_n8n_scan.json`, `langflow_flow.json`: contratos de integración opcional.
