---
name: status
description: Inspect Superworkflows Loop Engineering state without changing it. Use explicitly to list runs, find the active run, check stage and gate status, validate evidence integrity, summarize findings and approvals, or determine the next safe action.
---

# Superworkflows Status

Provide a read-only, evidence-grounded status view.

## Procedure

1. Resolve the repository root and read local instructions.
2. Resolve `<plugin-root>` as two directories above this `SKILL.md`. Run `python3 <plugin-root>/scripts/loopctl.py status --root <repo>` or add `--task <run-id>`.
3. Run `python3 <plugin-root>/scripts/loopctl.py validate --root <repo> --task <run-id>` for the selected run.
4. Compare the recorded base and current commit, evidence hashes, open findings, approval scope, and artifact policy.
5. Report: run identity and lineage, state/stage, latest event, P0/P1/P2 counts, evidence integrity, valid/expired approvals, blockers, and the next gate.

## Boundaries

- Do not create, resume, transition, repair, or rewrite a run.
- Do not spawn write-capable agents.
- Never infer success from a document's existence. Distinguish recorded claims from independently verified evidence.
- A hash chain detects accidental or partial modification; it is not a trusted external signature against complete history replacement.
