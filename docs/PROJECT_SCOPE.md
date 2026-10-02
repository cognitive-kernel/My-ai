# My-AI Product Scope

## In scope

- Local-first chat with persistent memory.
- Curriculum-based learning and evidence-backed skills.
- Coding, project tooling and sandboxed execution.
- Read-only database inspection/query analysis.
- Local files and multimodal inspection.
- Voice adapters for offline STT/TTS.
- Authorized security analysis.
- GitHub integration behind explicit permissions.
- Scheduler/resource controls, diagnostics, backup and recovery.
- Tested self-repair proposals and deny-by-default self-update.

## Explicitly out of scope

- Autonomous destructive actions.
- Arbitrary writes outside approved workspace/tool policies.
- Silent privilege escalation.
- External security operations without authorization and policy checks.
- Treating model output as proof of execution or verification.
- Adding a new product subsystem solely because an LLM suggested it.

## Change control

A new capability must define:
1. owner module and API boundary;
2. permission class;
3. read/write/execute behavior;
4. audit requirements;
5. regression tests;
6. documentation;
7. resource and failure limits.

This scope is the feature-creep guardrail for the project.
