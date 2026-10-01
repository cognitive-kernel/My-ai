# My-AI — Advanced Agent Maturity Roadmap

Version: 2026-10-01
Status: official execution roadmap

## Goal

Transform My-AI from a local assistant with many capabilities into a general software agent that is reliable, auditable, self-evaluating and self-repairing, while remaining offline-first. Normal behavior must not depend on trigger phrases, keywords or a specific provider.

Target pipeline:

Request -> Semantic Understanding -> Context/Memory -> Plan -> Policy/Authorization -> Transactional Execution -> Validation -> Critique -> Repair -> Re-validation -> Evidence/Trace -> Response

## Non-negotiable principles

1. Normal operation is local/offline.
2. Internet is allowed only for explicit research/learning and explicitly confirmed prerequisite acquisition.
3. Operational decisions must not be based on keyword lists or fixed sentences.
4. Every side effect requires capability, policy, actor and audit trail.
5. Model output is not proof of execution or validation.
6. Multi-step operations need transaction/rollback.
7. Self-repair is bounded, observable and cancellable.
8. Self-update remains deny-by-default and approval-gated.
9. Memory has a lifecycle and stale knowledge is revalidated.
10. Every task has a reconstructable trace.
11. Project workspaces are isolated.
12. Policy, tools, models and configuration are versioned and reversible.
13. Sensitive layers are typed, deterministic and dependency-light.
14. New capabilities require unit, integration and scenario/E2E acceptance tests.

## Phase A — Agent Behavioral Contract

### A1. Unified execution contract
- One standard pipeline for all task types.
- Hard separation of understanding, planning, authorization, execution, validation and response.
- No legacy path may bypass execution policy.
- Each stage has a schema and explicit status.

### A2. Task state machine
- received, understood, planned, authorized, running, validating, repairing, completed, failed, blocked, rolled_back.
- Invalid transitions fail closed.
- State transitions are persisted in trace.

## Phase B — Self-Evaluation and Repair

### B1. Verify -> Critique -> Repair -> Verify
- Check real acceptance criteria after important execution.
- Critique independently from the initial response.
- Repair only evidence-backed defects.
- Bound repair iterations and resource budget.
- Re-validation is mandatory after repair.

### B2. Independent repair engine
- Repair is not merely retrying the same plan.
- Store failure cause, evidence, patch proposal and validation result.
- Stop repeated ineffective repairs and report clearly.
- Store reusable failure lessons.

## Phase C — Safe Execution

### C1. Real sandbox
- Container sandbox by default.
- Network disabled unless an explicit capability permits it.
- Filesystem limited to the task workspace.
- CPU, RAM, PID, timeout and output limits.
- no-new-privileges and dropped capabilities.
- Host subprocess only when explicitly policy-gated.

### C2. Transaction and rollback
- Multi-step operations are atomic or compensatable.
- SQLite transactions/savepoints for state.
- Filesystem changes use journal/snapshot rollback.
- Failed tasks clean or restore partial artifacts.
- Rollback is traced and audited.

### C3. Workspace isolation
- Every project/task has an independent root.
- Path traversal and symlink escape are blocked.
- Artifacts are associated with project/task.
- Temporary workspace cleanup is defined.

## Phase D — Memory and Knowledge Lifecycle

### D1. Memory lifecycle
- temporary -> candidate -> validated -> trusted -> stale -> archived.
- Promotion/demotion requires evidence or policy.
- Category and provenance remain available to retrieval.
- Critical answers must not silently rely on stale knowledge.

### D2. Semantic retrieval quality
- Hybrid retrieval with semantic similarity, lexical evidence and provenance.
- Confidence is explainable and calibratable.
- Retrieval judgments and regression benchmarks are retained.

## Phase E — Observability and Evidence

### E1. Full task trace
- Connect request, plan, model, capabilities, tools, inputs/outputs, validations, repairs, evidence and final response.
- Trace is queryable and summarizable.
- Secrets and tokens are redacted.

### E2. Auditability
- Actor, timestamp, operation, risk, authorization, outcome and error.
- Write/execute/system operations require audit.
- Audit trail is append-oriented and tamper-evident where practical.

## Phase F — Evaluation

### F1. Scenario-based E2E
Executable scenarios must cover:
- context continuation
- ambiguity
- tool approval
- sandbox execution
- failed validation plus repair
- rollback
- research-to-code
- conflicting evidence
- offline enforcement
- multi-session
- resource-aware model selection
- trace completeness

### F2. Regression gate
- Relevant runtime changes execute the local benchmark.
- Baseline and current result are recorded.
- Regression blocks acceptance.

## Phase G — Tool and Capability Architecture

### G1. Unified tool contract
Every tool declares:
- name/version
- input/output schema
- risk
- permissions
- offline/online mode
- resource limits
- timeout
- validation hook
- audit policy

### G2. Capability registry
- Discovery comes from registry.
- Authorization precedes execution.
- Unknown tools are denied.
- Online capabilities are opt-in.
- Provider-specific code remains behind adapters.

## Phase H — Local Model Lifecycle

- Discovery and health checks.
- Resource and context-window fit.
- Model fallback.
- Version/change detection.
- Per-model benchmarks.
- Unhealthy/stale model quarantine.
- Fully functional without remote dependency in offline mode.

## Phase I — Task and Trace UI

- Active and historical tasks.
- State and progress.
- Plan and acceptance criteria.
- Tool calls and authorization.
- Validation and repair iterations.
- Evidence graph and completion report.
- Clear blocked/failed/rolled-back reasons.
- Trace UI is read-only unless a route explicitly performs a mutation.

## Phase J — Plugin and Tool Extensibility

- Standard tool-provider interface.
- Manifest versioning.
- Capability declarations.
- Sandbox boundary.
- Lifecycle and health.
- Compatibility checks.
- Plugins cannot bypass policy.

## Phase K — Project Isolation and Configuration Versioning

### K1. Project isolation
- Configuration, memory, artifacts and traces are project-scoped.
- Cross-project retrieval requires explicit policy.

### K2. Versioned agent configuration
- Policy, tool manifests, model routing, runtime modes and limits are versioned.
- Diff, activate, rollback and audit are available.

## Phase L — Operational Resilience

- Bounded retries.
- Circuit breaker for unhealthy backends.
- Cancellation.
- Graceful shutdown.
- Orphan cleanup.
- Recovery after process restart.
- Health/readiness endpoints.
- No silent background mutation.

## Phase M — Completion Standard

A capability is complete only when it has:
- semantic path
- policy boundary
- appropriate sandbox/transaction
- independent validation
- evidence and trace
- defined failure/repair/rollback behavior
- regression and scenario tests
- documentation and operational UI

## Execution priority

1. Agent Behavioral Contract + Task State Machine
2. Verify/Critique/Repair/Verify
3. Transaction/Rollback + Workspace Isolation
4. Sandbox hardening
5. Full Task Trace + Audit
6. Scenario E2E benchmark
7. Memory lifecycle
8. Unified Tool/Capability contract
9. Configuration versioning
10. Task/Trace UI
11. Plugin architecture
12. Model lifecycle
13. Operational resilience

## Definition of Done

- No normal path depends on keyword/trigger phrases.
- No write/execute operation bypasses policy and audit.
- Strict offline blocks normal outbound network.
- Every task is reconstructable from trace.
- Every important defect is validated, repaired, or clearly reported as blocked/failed.
- Multi-step rollback is reliable.
- Local scenario benchmarks are executable.
- Sensitive code is typed, testable and deterministic.
- Configuration, tools and model routing are versioned and reversible.
