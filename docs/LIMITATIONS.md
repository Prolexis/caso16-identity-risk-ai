# Limitaciones y controles

- Los registros `Demo AD` y `Demo LDAP` son sintéticos y no representan indicadores reales.
- No se declara conexión, disponibilidad ni funcionamiento correcto de AD/LDAP, n8n, LangFlow o un LLM.
- La ausencia de `last_activity` se clasifica como `potential`, no como incumplimiento confirmado.
- No se ejecutan desactivaciones, cambios de contraseña ni revocaciones sobre directorios.
- El fallback SQLite es solo para ejecución local sin infraestructura; PostgreSQL es el destino de Compose.
- La autenticación de la UI es un acceso de demostración. Antes de producción debe sustituirse por OIDC/SSO, MFA, RBAC persistente y rate limiting backend.
- Deben añadirse Alembic, secretos gestionados, TLS, CSRF/CORS endurecido, observabilidad, backups y pruebas de seguridad.
- La alineación de diseño con A.8.2 de ISO/IEC 27001:2022 no es una certificación ni una evaluación de conformidad.
