---
name: init
description: Initialize or audit CodeGraph plus optional persistent .ai run state for a robotics, embodied-AI, robot-runtime, data, control, RL, sim2real, or real-robot repository. Use explicitly when a project needs indexed code exploration, resumable run artifacts, a project profile, or evidence rules.
---

# Superworkflows Init

Prepare CodeGraph and optional project-local persistent state. The plugin's bundled workflow is the sole protocol.

## Preflight

1. Resolve the repository root and read all applicable `AGENTS.md` files.
2. Resolve `<plugin-root>` as two directories above this `SKILL.md`, then run `python3 <plugin-root>/scripts/codegraphctl.py prepare --root <repo>` before broad code exploration. Stop if the fail-closed controller cannot produce a healthy, current index.
3. Inspect `.ai/`, `.gitignore`, build and test entry points, CI, deployment scripts, and safety guidance using CodeGraph first where applicable.
4. Run `python3 <plugin-root>/scripts/loopctl.py bootstrap --root <repo> --dry-run` first.
5. Report conflicts before writing. Never change `.gitignore` automatically.

## Initialize

With user authorization to edit the repository, run:

```bash
python3 <plugin-root>/scripts/loopctl.py bootstrap --root <repo>
```

The command creates only the optional `.ai/project-profile.json`, `.ai/runs/`, and `.ai/improvements/pending/` when missing. It does not create `.ai/workflow.md`, project-local workflow templates, or `.ai/project-profile.md`. Customize the JSON profile from verified repository facts: commands, replay/simulation/HIL/robot gates, performance budgets, artifact policy, release provider, and worktree conventions. Unknowns remain explicit `TBD`; do not invent them.

## Audit and handoff

Run:

```bash
python3 <plugin-root>/scripts/loopctl.py audit --root <repo>
```

Explain whether `.ai/runs/**` is committed, local-only, or externally retained. A local-only policy is valid, but it cannot be described as repository-auditable evidence. Do not start a run unless the user also requested execution.

## Safety boundaries

- Initialization does not authorize push, PR/MR, publish, deployment, HIL, real-robot execution, or actuation.
- Preserve stronger project safety gates.
- Do not copy project-specific facts from another repository.
- Treat `.codegraph/` as a generated local index, not engineering evidence. Do not include its changes in workspace or evidence freshness claims.
