# My-AI Architecture Boundaries

## Runtime layers

- API layer (my_ai/api.py): authentication, request validation, HTTP status mapping, and route composition only.
- Domain/services (learner.py, scheduler.py, platform.py, skill_engine.py, dynamic_learning.py, self_update.py): business rules and orchestration.
- Persistence (db.py, settings_store.py): SQLite access and schema management.
- UI (my_ai/static/): browser HTML/CSS/JavaScript. Python only serves the static page and API.
- Infrastructure (runtime_prerequisites.py, network.py, watchdog.py, self_diagnostics.py): environment and process concerns.

## Dependency rules

1. UI communicates with the application through HTTP APIs; it must not import Python modules.
2. API routes may call domain services, but domain services must not import FastAPI request/response objects.
3. Persistence helpers own database connections; services use fetch_all/execute rather than creating ad-hoc global connections.
4. Write-capable services must honor the central read-only/write policy before filesystem or repository mutations.
5. Admin-only operations are enforced at the route boundary and audited.
6. External retrieval and model access remain behind the platform/web/LLM service boundaries.

## Acceptance surfaces

/admin/readiness, /eval/retrieval, /skills/reviews, /self-update/status, and the browser E2E suite expose the operational acceptance state without requiring local hardware-specific checks.

Self-update is deliberately disabled by default; enabling it requires both the explicit runtime enable flag and an explicit approval flag.
