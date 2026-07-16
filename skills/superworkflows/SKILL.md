---
name: superworkflows
description: Route explicit requests and high-confidence complex robotics or embodied-AI tasks to initialization, session-only execution, status, adversarial review, release, or controlled learning. Use implicitly for multi-module implementation, safety or rollback work, production commissioning, independent review, or run-status inspection; ignore simple edits, generic explanations, and ordinary software tasks. Use $superworkflows for deterministic routing and direct users to $run or $init before any persistent state is created or resumed.
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

# Superworkflows

Act as a small router. Do not duplicate the complete Loop Engineering protocol here.

## Assess activation before side effects

Determine whether the request contains an explicit `$superworkflows` or child-Skill invocation. If
it does not, resolve `<plugin-root>` as two directories above this `SKILL.md` and pass the request to
`python3 <plugin-root>/scripts/triggerctl.py` through stdin. Never interpolate untrusted request text
into a shell command.

Interpret the assessment as follows:

| Decision | Required behavior |
|---|---|
| `IGNORE` | Stop routing and handle the request normally. Do not mention or mutate Superworkflows state. |
| `SUGGEST` | Offer one concise hint. Do not create, resume, or select a Run. |
| `ACTIVATE_SESSION_ONLY` | Route the task with the returned authority, but never bootstrap/start/resume `.ai` state or mutate/initialize CodeGraph. |
| `BLOCK_EXTERNAL` | Block only the external/hardware sub-action and preserve the returned local route. `$status`/`$review` may continue read-only; do not infer unrelated local writes. Explain that execution requires `$release`, a persistent ledger, and exact action-scoped authorization. |
| `EXPLICIT` | Continue through the explicit route while preserving all authority gates. |

Treat `triggerctl.py` as a deterministic advisory guard, not a semantic model. Codex metadata supplies
semantic discovery; the guard separates route, persistence, and authority and retains only a request
digest. Keyword frequency never grants authority.

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
| Install `.ai/` protocol or create a project profile | Require exact `$init`, then load `../init/SKILL.md`; the top-level router only hands off. |
| Inspect runs, evidence, findings, approvals, or the next gate read-only | `../status/SKILL.md` |
| Implement session-only, or start/continue/resume a run | Load `../run/SKILL.md`; exact `$run` is required before persistent mutation. |
| Review a plan, diff, branch, evidence set, or safety claim | `../review/SKILL.md` |
| Integrate, validate rollback, push, create PR/MR, or release | Load `../release/SKILL.md` for read-only readiness; exact `$release` or a validated persistent Run rooted in exact `$run` is required before mutation. |
| Distill lessons, consolidate procedures, or improve skills | Load `../learn/SKILL.md`; router-selected learning stays response-only unless exact `$learn` or a validated completed Run rooted in exact `$run` reaches its learning stage. |

Read the chosen sibling `SKILL.md` completely before acting. If one request spans several intents, preserve one run identity and load only the skills needed for the current gate.

An explicit `$superworkflows` call is deterministic router activation, not an alias for persistent mutation. When its assessment returns `persistence: confirm`, continue session-only and request the exact `$init` or `$run` child invocation before loading a mutating child flow, creating `.ai/`, preparing CodeGraph, starting a persistent Run, or resuming one.

## Detect project and run state

1. Find the repository root and read local instructions.
2. Do not initialize or mutate CodeGraph during implicit assessment. After activation, obey repository instructions. Implicit routes, explicit router confirmation, `$status`, and `$review` may use an existing healthy index read-only but never call `prepare`, `sync`, `index`, or `init`; if it is stale, report the limitation and verify decisive facts from current source/Git. Only an exact write-capable child route may prepare an existing index. Initialize a missing index only through exact `$init` or equivalent explicit indexing authorization when no stronger instruction prohibits it.
3. Use the plugin baseline directly; do not look for, generate, or require a project `.ai/workflow.md`.
4. Read `.ai/project-profile.json` only when present; it is an optional machine overlay for repository commands and gates.
5. Inspect runs only through read-only `loopctl.py status`; do not trust raw `run.json` alone.
6. Never auto-resume from semantic title similarity or continuation words. Require explicit `$run` plus an exact user-selected Run ID. If zero, multiple, corrupt, or ambiguous candidates exist, report them without mutation.
7. If no `.ai/` state exists, continue session-only or route to initialization when persistent state is requested.

## Non-negotiable boundaries

- Implicit selection permits only session-only routing. It does not authorize `.ai` creation, Run resume, CodeGraph mutation or initialization, delegation before scope is known, or external actions.
- Explicit `$superworkflows` permits routing and, for a large task, staged delegation. It does not authorize persistent `.ai` mutation, Run resume, or external actions; those require the exact child Skill and applicable gates.
- Require separate, action-scoped user authorization for push, PR/MR creation, tag, publish, deployment, HIL, real-robot execution, or robot actuation.
- Keep reviewers read-only. Only an independent reviewer may mark a finding `VERIFIED`.
- Never auto-edit workflow or skill safety gates from lessons learned. Stage an improvement proposal for later human approval.
- Resolve the plugin root as two directories above this `SKILL.md`. Invoke `<plugin-root>/scripts/codegraphctl.py` for CodeGraph lifecycle, `<plugin-root>/scripts/loopctl.py` for persistent state/evidence, and `<plugin-root>/scripts/sync_agents.py --check` before delegated runs; do not interpret these paths relative to the project cwd.
- Treat `.ai/runs` as project evidence, not as proof by itself. Validate hashes, commits, exit codes, and independent review.
