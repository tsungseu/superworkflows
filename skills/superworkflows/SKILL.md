---
name: superworkflows
description: Route explicit Superworkflows requests to initialization, run or resume, adversarial review, release, or learning workflows for robotics and embodied-AI projects. Use $superworkflows as the stable top-level entry point when the user wants the plugin to choose the correct Loop Engineering skill.
---

# Superworkflows

Act as a small router. Do not duplicate the complete Loop Engineering protocol here.

## Resolve authority

Apply rules in this order:

1. System, developer, and explicit user authorization.
2. Repository `AGENTS.md` and equivalent local instructions.
3. Optional project `.ai/project-profile.json` machine settings.
4. Plugin baseline under `assets/loop-engineering/`, the sole workflow protocol.
5. The selected sibling skill.

Never let a lower layer weaken safety, evidence integrity, independent review, or action-scoped authorization.

## Route the request

| Intent or state | Load and follow |
|---|---|
| Install `.ai/` protocol or create a project profile | `../init/SKILL.md` |
| Inspect runs, evidence, findings, approvals, or the next gate read-only | `../status/SKILL.md` |
| Start, continue, resume, or implement a run | `../run/SKILL.md` |
| Review a plan, diff, branch, evidence set, or safety claim | `../review/SKILL.md` |
| Integrate, validate rollback, push, create PR/MR, or release | `../release/SKILL.md` |
| Distill lessons, consolidate procedures, or improve skills | `../learn/SKILL.md` |

Read the chosen sibling `SKILL.md` completely before acting. If one request spans several intents, preserve one run identity and load only the skills needed for the current gate.

## Detect project and run state

1. Find the repository root and read local instructions.
2. Before code exploration or implementation, resolve `<plugin-root>` and run `python3 <plugin-root>/scripts/codegraphctl.py prepare --root <repo>`. It initializes a missing index, synchronizes pending changes, rebuilds incompatible/worktree-mismatched indexes, and fails closed. Pure `$status` inspection does not prepare or mutate an index.
3. Use the plugin baseline directly; do not look for, generate, or require a project `.ai/workflow.md`.
4. Read `.ai/project-profile.json` only when present; it is an optional machine overlay for repository commands and gates.
5. Inspect `.ai/runs/*/run.json` for an active or blocked run.
6. Prefer resuming a matching run over silently creating a second run.
7. If no `.ai/` state exists, continue session-only or route to initialization when persistent state is requested.

## Non-negotiable boundaries

- Explicit `$superworkflows` permits routing and, for a large task, staged delegation. It does not authorize external actions.
- Require separate, action-scoped user authorization for push, PR/MR creation, tag, publish, deployment, HIL, real-robot execution, or robot actuation.
- Keep reviewers read-only. Only an independent reviewer may mark a finding `VERIFIED`.
- Never auto-edit workflow or skill safety gates from lessons learned. Stage an improvement proposal for later human approval.
- Resolve the plugin root as two directories above this `SKILL.md`. Invoke `<plugin-root>/scripts/codegraphctl.py` for CodeGraph lifecycle, `<plugin-root>/scripts/loopctl.py` for persistent state/evidence, and `<plugin-root>/scripts/sync_agents.py --check` before delegated runs; do not interpret these paths relative to the project cwd.
- Treat `.ai/runs` as project evidence, not as proof by itself. Validate hashes, commits, exit codes, and independent review.
