---
name: run
description: Start or resume a persistent, multi-stage robotics AI coding loop with isolated delegation, evidence capture, adversarial review, remediation, and resumable state. Use explicitly for large multi-file implementation, robot-runtime, embodied-AI, data, control, RL, sim2real, or commissioning tasks that need more than a simple edit.
---

# Superworkflows Run

Run the engineering loop as a state machine. The main/integration agent owns state; delegated agents return structured results and never edit the ledger.

## Start or resume

1. Resolve `<plugin-root>` as two directories above this `SKILL.md`. Read repository instructions and use `<plugin-root>/assets/loop-engineering/workflow.md` as the sole workflow protocol. Never require or generate project `.ai/workflow.md`.
2. Run `python3 <plugin-root>/scripts/codegraphctl.py prepare --root <repo>` before code exploration. Stop if it cannot initialize, synchronize, rebuild, and validate a healthy index.
3. Read `.ai/project-profile.json` only when persistent machine-captured evidence is requested. Initialize it through `$init` when absent; otherwise continue session-only without inventing `.ai/` files.
4. Run `python3 <plugin-root>/scripts/sync_agents.py --check` before delegation. Missing runtime agents are a setup issue, not permission to install silently.
5. Inspect existing state with `loopctl.py status`. Resume a matching active or blocked run instead of creating a duplicate.
6. Start only when needed:

```bash
python3 <plugin-root>/scripts/loopctl.py start --root <repo> --task <run-id> --title "<task>"
```

Use `--parent-run <id>` when the work continues or remediates an earlier run.

## Closed loop

Follow `<plugin-root>/assets/loop-engineering/workflow.md` and the project profile. The baseline stages are:

1. repository exploration;
2. requirements and safety contract;
3. initial plan;
4. independent plan review;
5. final plan;
6. ownership and isolated worktrees;
7. parallel implementation where write sets are disjoint;
8. independent code and safety review;
9. remediation;
10. remediation verification;
11. serial integration;
12. final verification across applicable replay, simulation, HIL, and robot gates;
13. release readiness and rollback proof;
14. delivery report and reviewed lessons.

Collapse stages for small, low-risk changes, but record why. Never collapse independent review for safety-relevant behavior.

## Delegation contract

Each child receives objective, allowed files, prohibited actions, required tests, evidence format, and stop conditions. Prefer namespaced `sw-*` agents. Children must not delegate further, invoke the router, push, deploy, operate hardware, or claim a gate they did not execute.

## CodeGraph checkpoints

- Prefer the `codegraph_explore`/`codegraph_node` MCP tools when available; otherwise use the equivalent `codegraph explore`/`node` CLI plus `callers` and `callees`. Let the model choose and interpret queries, then re-read the decisive source and current Git diff. Graph output is navigation evidence, not behavioral proof.
- Before finalizing a plan, run `codegraph impact <symbol> --path <repo>` for changed contracts or central symbols and record unresolved blast-radius gaps.
- After every writer result, remediation, or serial integration that changes indexed files, run `python3 <plugin-root>/scripts/codegraphctl.py sync --root <repo>` before review or further graph queries.
- Use `codegraph affected --path <repo> <changed-files...>` to propose relevant tests. Project-profile gates and independently executed tests remain authoritative; affected-test selection cannot waive them.

## State, evidence, and findings

- Transition with `loopctl.py transition`; state is atomically checkpointed in `run.json` and events append to `events.jsonl`.
- Capture executable evidence with `loopctl.py evidence ... --command-key <profile-key>`. It executes only the exact local argv declared under `.ai/project-profile.json`; HIL, real-robot, rollback, and external actions are rejected by this executor. Preserve command, cwd, commit, timestamps, exit code, stdout/stderr hashes, and artifact hashes.
- Record findings with `finding-open`; only an independent reviewer may use `finding-update ... --status VERIFIED`.
- P0 blocks progression and completion. P1 requires remediation or explicit deferral with owner, reason, and due condition. P2 is tracked debt and never silently disappears.

## Interruption and completion

Checkpoint after every stage, finding change, evidence capture, and authorization. On interruption, stop children and leave the run resumable. Before completion, run `loopctl.py validate --gate complete`; report unexecuted gates as unverified, not passed.

Invocation does not authorize push, PR/MR, tag, publish, deployment, HIL, real-robot execution, or actuation.
