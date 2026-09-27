# My-AI Architecture

## Runtime layers

1. API/UI — FastAPI routes, authentication, static UI and streaming.
2. Application — use-case composition and dependency injection.
3. Domain — pure intent/business decisions with no infrastructure imports.
4. Core — protocols and stable contracts.
5. Infrastructure — LLM, persistence and host/network adapters.
6. Capabilities — learning, memory, coding, files, voice, GitHub and security services.
7. Execution — sandboxed Python/project tooling and the remote executor service.
8. Maintenance — diagnostics, self-repair proposals and deny-by-default self-update.

## Request flow

HTTP request -> authentication -> central access policy -> application service -> domain/capability -> persistence -> audit

Chat follows:

message -> history/attachments -> application router service -> domain structured intent -> policy -> hybrid memory retrieval -> selected LLM -> response

The router is advisory and never grants permission.

## Dependency rules

- Domain imports only core contracts and standard-library code.
- Application depends on domain/core and injects infrastructure adapters through protocols.
- Infrastructure never depends on application or API layers.
- API is the composition/transport boundary and may call application services and capabilities.
- Legacy top-level router.py, llm.py and db.py are compatibility facades only.
- tests/test_architecture_boundaries.py statically enforces these rules on every CI run.

## Structured routing

Routing is provider-backed structured output with a strict JSON Schema. Ollama uses its schema-constrained format; OpenAI-compatible Responses uses strict text.format.type=json_schema. No keyword/regex classifier or free-form JSON fallback is used.

## Security boundaries

- File paths are resolved and constrained to approved roots.
- SQL integrations expose read-only query validation.
- Code execution is sandboxed/remote when configured.
- External security operations are policy constrained.
- Self-update is deny-by-default and requires isolated tests, approval, snapshot and health/rollback supervision.
