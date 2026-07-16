---
name: run
description: Execute a multi-stage robotics AI coding loop with isolated delegation, evidence capture, adversarial review, remediation, and optional resumable state. Use only when explicitly invoked with $run or selected by the Superworkflows router for a high-confidence multi-file robot-runtime, embodied-AI, data, control, RL, sim2real, or commissioning task.
---
<!--
Superworkflows - persistent robotics AI Coding Loop Engineering.
Copyright (c) 2026 Tsung Xu

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

Dual-licensed: AGPL-3.0-only OR a separate commercial license.
-->

# Superworkflows Run

Run the engineering loop as a state machine. The main/integration agent owns state; delegated agents return structured results and never edit the ledger.

## Start or resume

1. Resolve `<plugin-root>` as two directories above this `SKILL.md`. Read repository instructions and use `<plugin-root>/assets/loop-engineering/workflow.md` as the sole workflow protocol. Never require or generate project `.ai/workflow.md`.
2. Preserve the router's activation assessment and provenance. An implicit `ACTIVATE_SESSION_ONLY` route or explicit-router `persistence: confirm` route may perform repository source changes explicitly requested by the user within the current session, but must not call `loopctl.py bootstrap`, `start`, or `resume`, create `.ai/`, or claim resumability. To upgrade it, require a new exact `$run` or `$init` request.
3. Obey repository CodeGraph instructions. For an implicit session-only or explicit-router confirmation route, check and query an existing healthy index read-only; never call `prepare`, `sync`, `index`, or `init`. If it is stale, report the limitation and verify decisive facts from current source/Git. Only exact `$run` or an already validated explicit persistent Run whose lineage records exact `$run` activation may prepare an existing index. Initialize a missing index only through exact `$init` or equivalent explicit indexing authorization and never against a stronger repository rule.
4. Read `.ai/project-profile.json` only for explicitly requested persistent machine-captured evidence. Initialize it through `$init` when absent; otherwise continue session-only without inventing `.ai/` files.
5. Run `python3 <plugin-root>/scripts/sync_agents.py --check` before delegation. Missing runtime agents are a setup issue, not permission to install silently.
6. Inspect existing state with `loopctl.py status`. Never select a Run by title similarity. Resume only an exact Run ID selected in an explicit request; otherwise list candidates and stop before mutation.
7. Start only after an exact `$run` invocation:

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

Each child starts from fresh, bounded context and receives objective, acceptance criteria, allowed files, prohibited actions, input commit/workspace digest, referenced artifact hashes, allowed tools, required tests, evidence format, authority, and stop conditions. Prefer namespaced `sw-*` agents. Children must not delegate further, invoke the router, write `.ai/runs/**`, push, deploy, operate hardware, or claim a gate they did not execute. Only the structured final result returns to the parent; do not leak the full parent conversation as substitute context.

Treat `max_agent_attempts_per_work_item` and `max_review_cycles_per_work_item` as orchestration limits, but do not claim the current local ledger cryptographically enforces subagent identity or dispatch. Stop at exhaustion. A future dispatch broker must bind reservations, context hashes, actor instances, and results before these limits can be described as hard enforcement.

## CodeGraph checkpoints

- Prefer the `codegraph_explore`/`codegraph_node` MCP tools when available; otherwise use the equivalent `codegraph explore`/`node` CLI plus `callers` and `callees`. Let the model choose and interpret queries, then re-read the decisive source and current Git diff. Graph output is navigation evidence, not behavioral proof.
- Before finalizing a plan, run `codegraph impact <symbol> --path <repo>` for changed contracts or central symbols and record unresolved blast-radius gaps.
- After every writer result, remediation, or serial integration that changes indexed files under exact `$run` or a validated persistent lineage rooted in exact `$run`, run `python3 <plugin-root>/scripts/codegraphctl.py sync --root <repo>` before review or further graph queries. An implicit session-only or explicit-router confirmation route must not mutate the index; after a source write, treat graph output as stale and use current source/Git until an exact write-capable child route authorizes synchronization.
- Use `codegraph affected --path <repo> <changed-files...>` to propose relevant tests. Project-profile gates and independently executed tests remain authoritative; affected-test selection cannot waive them.

## State, evidence, and findings

- Transition with `loopctl.py transition`; state is atomically checkpointed in `run.json` and events append to `events.jsonl`.
- Capture executable evidence with `loopctl.py evidence ... --command-key <profile-key>`. It executes only the exact local argv declared under `.ai/project-profile.json`; HIL, real-robot, rollback, and external actions are rejected by this executor. Preserve command, cwd, commit, timestamps, exit code, stdout/stderr hashes, and artifact hashes.
- Record findings with `finding-open`; only an independent reviewer may use `finding-update ... --status VERIFIED`.
- P0 blocks progression and completion. P1 requires remediation or explicit deferral with owner, reason, and due condition. P2 is tracked debt and never silently disappears.

## Interruption and completion

Checkpoint after every stage, finding change, evidence capture, and authorization. On interruption, stop children and leave the run resumable. Before completion, run `loopctl.py validate --gate complete`; report unexecuted gates as unverified, not passed.

Invocation does not authorize push, PR/MR, tag, publish, deployment, HIL, real-robot execution, or actuation.
