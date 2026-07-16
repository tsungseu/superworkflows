# Security and Safety Boundaries

- Treat `.ai/runs/**` as locally tamper-evident engineering evidence, not a cryptographic trust anchor. Export or sign evidence when independent trust is required.
- Never record secrets or a complete process environment in command evidence.
- Plugin invocation is not authorization for push, PR/MR, tag, publish, deployment, HIL, real-robot execution, or actuation.
- Implicit semantic selection is session-only. It must not create `.ai/`, initialize or mutate CodeGraph, start/resume a Run, or perform an external/hardware action.
- Continuation language or semantic title similarity must never auto-select a Run. Require an exact explicitly selected Run ID and validate it before mutation.
- Declining persistent state does not create a session-only bypass for push, publish, deployment, HIL, or robot operations; those actions remain blocked.
- The local ledger cannot cryptographically attest model/subagent identity against a same-user process that can replace all local state. Read-only role configuration, structured results, hashes, and independent review are auditable controls, not an external signature.
- Trigger routing, `.ai` persistence rules, CodeGraph restrictions, and Skill authority gates are protocol and local-control-plane constraints, not an OS-level capability sandbox. Use Codex sandboxing, tool approvals, filesystem permissions, and external-system controls for hard isolation.
- Do not auto-apply learning proposals or weaken safety gates from historical outcomes.
- Report a symbolic-link, path traversal, transaction rollback, authorization, or gate-bypass issue before using the affected command in a production workflow.
