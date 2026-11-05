# Arquitectura CASO16 (MVP)

```mermaid
flowchart LR
  UI[Streamlit SOC UI] --> API[FastAPI /api/v1]
  UI --> DL[Data layer SQLAlchemy]
  API --> DL
  DL --> PG[(PostgreSQL en Compose)]
  DL -. fallback demo .-> SQLITE[(SQLite local explícito)]
  N8N[n8n opcional] --> API
  API -. contrato opcional .-> LF[LangFlow / LLM]
  AD[AD/LDAP read-only futuro] -. adaptador pendiente .-> DL
```

El motor determinista es la fuente de verdad para las evidencias y el score. Un modelo LLM, cuando se configure, solo puede explicar/priorizar y debe registrar modelo, prompt, ejecución y validación. Las integraciones externas están preparadas como contratos, no declaradas como conectadas.

Entidades implementadas en el MVP: `directory_accounts`, `findings`, `detection_runs` y `audit_logs`. La ampliación empresarial debe añadir usuarios/RBAC persistente, fuentes, grupos, membresías, tickets, reportes y excepciones con migraciones Alembic.
