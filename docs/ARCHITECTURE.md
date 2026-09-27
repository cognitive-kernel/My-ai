# My-AI Architecture

## Runtime layers

1. **API/UI** — FastAPI routes, authentication, static UI and streaming.
2. **Policy** — centralized route/tool authorization and global read-only enforcement.
3. **Agent/Router** — structured intent classification; routing never grants permission.
4. **Capabilities** — domain services such as learning, memory, coding, files, voice, GitHub and security analysis.
5. **Persistence** — SQLite today, with explicit repository boundaries for knowledge, sessions, audit and learning state.
6. **Execution** — sandboxed Python/project tooling and the remote executor service.
7. **Maintenance** — diagnostics, self-repair proposals and deny-by-default self-update.

## Request flow

HTTP request -> authentication -> central access policy -> route/service -> audit -> persistence

Chat follows:

message -> history/attachments -> structured router -> hybrid memory retrieval -> selected LLM -> response

Routing is advisory. High-risk actions still require the permission layer and explicit confirmation where configured.

## Security boundaries

- File paths are resolved and constrained to approved roots.
- SQL integrations expose read-only query validation.
- Code execution is sandboxed/remote when configured.
- External security operations are policy constrained.
- Self-update is deny-by-default and requires isolated tests, approval, snapshot and health/rollback supervision.

## Extension rule

New write or execution endpoints must be registered in `my_ai/access_policy.py` and covered by a permission regression test. This prevents silent privilege expansion.

## Dependency source

`pyproject.toml` is the dependency source of truth. `requirements.txt` is only a compatibility entry point that installs the local project.