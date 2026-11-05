# Matriz de trazabilidad resumida

| Requisito CASO16 | Evidencia en MVP | Estado |
|---|---|---|
| R01 inactividad >=90 días | `data_layer.py`, `run_detection` | VERIFICADO |
| R02 admin sin justificación | `data_layer.py`, `run_detection` | VERIFICADO |
| R03 administradores duplicados | `data_layer.py`, `run_detection` | VERIFICADO |
| R04 servicio sin expiración | `data_layer.py`, `run_detection` | VERIFICADO |
| R05 privilegios inconsistentes | política `ALLOWED_PRIVILEGES` | VERIFICADO |
| R06 riesgo alto sin revisión | `data_layer.py`, `run_detection` | VERIFICADO |
| Score transparente 0–100 | `compute_score` + UI | VERIFICADO |
| Inventario y dashboard | `app.py` | VERIFICADO |
| Hallazgos y remediación | `update_finding` + UI/API | VERIFICADO |
| Bitácora append-only | `audit_logs` + `audit_event` | VERIFICADO |
| Reportes PDF/DOCX/XLSX | `render_reports` | VERIFICADO |
| FastAPI/OpenAPI | `main.py` | VERIFICADO |
| PostgreSQL | Compose y `DATABASE_URL` | PARCIAL (Docker no validado aquí) |
| AD/LDAP real | Adaptador pendiente | BLOQUEADO sin credenciales/red |
| LangChain/LangFlow/LLM | Contrato opcional, fallback determinista | PARCIAL |
| n8n real | JSON exportable, integración externa pendiente | PARCIAL |
| React/TypeScript | Shell en `frontend/` si se incorpora | PARCIAL |
| SSO, MFA, TLS, rate limiting | No incluido en demo | NO IMPLEMENTADO |
