# Security and Safety Boundaries

- Treat `.ai/runs/**` as locally tamper-evident engineering evidence, not a cryptographic trust anchor. Export or sign evidence when independent trust is required.
- Never record secrets or a complete process environment in command evidence.
- Plugin invocation is not authorization for push, PR/MR, tag, publish, deployment, HIL, real-robot execution, or actuation.
- Do not auto-apply learning proposals or weaken safety gates from historical outcomes.
- Report a symbolic-link, path traversal, transaction rollback, authorization, or gate-bypass issue before using the affected command in a production workflow.
