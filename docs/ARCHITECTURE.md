# My-AI Architecture Boundaries

## Runtime layers

1. API/UI — my_ai/api.py and my_ai/static/; HTTP/authentication/transport only.
2. Application — my_ai/application/; dependency injection and use-case composition.
3. Domain — my_ai/domain/; pure business decisions and schemas. Domain code depends only on my_ai/core and standard-library code.
4. Core — my_ai/core/; stable protocols and shared contracts with no infrastructure/application imports.
5. Infrastructure — my_ai/infra/; LLM, persistence, network and host adapters.

Legacy top-level modules such as my_ai/router.py, my_ai/llm.py and my_ai/db.py are compatibility facades only. New code must import the layered implementation directly.

## Dependency enforcement

The dependency graph is enforced by tests/test_architecture_boundaries.py using AST import inspection:

- Domain cannot import API/UI, application, infrastructure, database, LLM or configuration adapters.
- Core cannot import application/domain/infrastructure/API packages.
- Application cannot import API/UI; external adapters are injected through core protocols.
- Infrastructure cannot import application or API layers.
- Critical flat modules are verified to contain no implementation of routing, LLM or persistence.

## Router boundary

The router is a domain service with the StructuredRouter protocol injected by the application layer. Provider adapters live in my_ai/infra/router_llm.py.

Routing uses strict schema-constrained structured output; there is no keyword/regex intent table or free-form JSON fallback. The router only returns intent data. Authorization, confirmation and execution remain separate policy concerns.

## Persistence boundary

SQLite implementation lives in my_ai/infra/persistence.py. my_ai/db.py remains a compatibility facade for existing integrations.

## Acceptance surfaces

/admin/readiness, /eval/retrieval, /skills/reviews, /self-update/status, and the browser E2E suite expose operational acceptance state.

Self-update remains disabled by default; enabling it requires the explicit runtime enable flag and explicit approval.
