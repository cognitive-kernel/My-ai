# Self-Development, Self-Diagnostics and Hardware Adaptation

My-AI is designed to progressively become self-maintaining while keeping the development lifecycle explicit.

## Initial and beta phase

During the initial and beta releases, self-development is report-only.

After every application startup, and periodically while the application is running, My-AI:

- checks its own Python source with compileall;
- runs the project test suite;
- checks repository state;
- records the current commit;
- records available CPU, RAM, operating system and Python information;
- stores a diagnostic report in data/diagnostics/ and SQLite;
- identifies failures and optimization opportunities;
- does not modify source code automatically.

## Hardware-aware operation

Runtime decisions must be based on the hardware actually available on the machine.

The project should prefer:

1. detecting CPU, RAM and GPU availability at runtime;
2. selecting model/context/thread/GPU-layer settings accordingly;
3. reducing background learning concurrency when resources are constrained;
4. increasing local workloads only when the machine has sufficient capacity;
5. recording detected hardware in diagnostics so optimization recommendations are reproducible.

The repository must not hard-code a hardware profile when the actual machine can be detected.

## Development lifecycle

### Phase 1 — Initial
- self-diagnostics: enabled
- bug detection: enabled
- optimization analysis: enabled
- automatic source modification: disabled
- automatic dependency/configuration changes: disabled
- report generation: enabled

### Phase 2 — Beta
The same report-only policy remains in force until the self-development subsystem has sufficient test coverage and rollback validation.

### Phase 3 — Self-maintaining release

The intended controlled workflow is:

detect → diagnose → propose → isolated test → report → approve/policy check → apply → test → rollback if needed

The existing self_repair.py is the foundation for this workflow. Future versions should reuse isolated worktrees, tests, rollback and audit records rather than editing the live tree blindly.

## Future module creation

The long-term goal is that the user can tell My-AI:

"برای خودت یک ماژول X بساز."

My-AI should then:

1. understand the requested capability;
2. inspect the current architecture and module registry;
3. determine whether a local implementation already exists;
4. design the smallest native module;
5. create the module and tests in an isolated workspace;
6. run compile/tests/security checks;
7. generate a change report;
8. after the self-development policy permits it, apply the change;
9. register the module/capability and update documentation;
10. keep rollback information.

Third-party APIs must not be introduced merely for convenience. A third-party service is acceptable only when the capability is inherently dependent on that external system or is explicitly selected as an optional provider.

## Ownership rule

New capabilities should be implemented as My-AI-owned modules with provider interfaces where useful.

Preferred order:

MY-AI native/local implementation → local open-source backend → optional external provider

not:

external API → MY-AI wrapper

LLM and Git/GitHub remain explicit exceptions where external infrastructure is currently useful or technically required.

## Safety of self-development

The initial/beta system must never silently:

- rewrite its own source;
- install arbitrary packages;
- change security policy;
- change user permissions;
- publish to GitHub;
- deploy itself;
- remove audit history.

All such operations remain explicit until a later release deliberately enables a controlled self-development policy.
