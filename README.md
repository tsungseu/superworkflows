# Superworkflows

[English](README.md) | [简体中文](README.zh-CN.md)

Superworkflows is a Robotics and Embodied-AI Coding Loop Engineering methodology for Codex. It combines one discoverable top-level router, six explicit stage skills, specialized `sw-*` agents, optional durable run state, adversarial review, machine-captured evidence, conditional CodeGraph-assisted exploration, release gates, and approval-controlled learning.

It is designed for robot runtimes, brain and cerebellum software, locomotion and reinforcement learning, sim2real, real-robot data collection, robotics datasets, and production commissioning where “the code looks right” is not enough.

## Quickstart

For a complex robotics request, the router can be discovered from normal language and execute user-requested repository source changes in a session-only workflow without creating persistent workflow state:

```text
Add model OTA and rollback to this robot runtime, with an adversarial safety review.
```

Invoke the router explicitly when you want deterministic activation:

```text
$superworkflows add model OTA and rollback to this robot runtime
```

Invoke the exact stage directly for persistent initialization, start, or resume:

```text
$init initialize CodeGraph and optional persistent run state
$run start or resume this implementation as an evidence-backed loop
$status inspect the active run without changing it
$review adversarially review the current plan, diff, and evidence
$release assess integration, rollback, and release readiness
$learn propose reviewed workflow improvements from completed runs
```

Only `$superworkflows` may be invoked implicitly. The six child skills remain explicit or router-selected. The protocol restricts an implicit route to session-only work and forbids it from mutating or initializing CodeGraph, creating or resuming `.ai` Run state, inferring a Run from title similarity, or treating push, PR/MR creation, publishing, deployment, HIL, real-robot execution, or actuation as authorized. Explicit router invocation is still not an alias for `$init` or `$run`.

## How It Works

Superworkflows first separates three independent decisions: **route** (which stage fits), **persistence** (session-only or durable Run), and **authority** (local analysis, repository writes, or separately approved external/hardware action). An external-action flag does not overwrite the selected local route, and required authority is reported separately from currently available authority. A side-effect-free activation assessor supports the router with auditable multilingual signals; it does not replace model reasoning or grant authority.

The engineering loop establishes repository truth, writes an explicit contract, challenges the plan, implements within bounded ownership, challenges the implementation, remediates findings, integrates serially, verifies at the highest authorized environment, and records what was actually observed.

For persistent work, the main agent is the sole run-ledger writer. Delegated agents receive a bounded work item, allowed files, required checks, and stop conditions. Reviewers remain independent and read-only. The implementer may mark a finding `FIXED`; only an independent reviewer may mark it `VERIFIED` against current evidence.

Persistent work may resume from an exact `.ai/runs/<run-id>/` only after explicit `$run` activation and validation of lineage, repository identity, event integrity, workspace freshness, agent contracts, and unresolved external-action intents. Ambiguous continuation language never selects or resumes a Run automatically.

## The Basic Workflow

1. **Repository exploration** — establish scope, entry points, call paths, interfaces, tests, and risks.
2. **Requirements and safety contract** — define invariants, exclusions, acceptance criteria, and an evidence plan.
3. **Initial plan** — create a work-item DAG, ownership map, verification strategy, and rollback plan.
4. **Independent plan review** — challenge assumptions and classify P0/P1/P2 findings.
5. **Final plan** — resolve or explicitly track findings before implementation.
6. **Ownership and isolation** — assign one writer per file and use worktrees when appropriate.
7. **Implementation** — execute bounded changes, parallelizing only disjoint write sets.
8. **Independent code and safety review** — inspect the current commit, diff, interfaces, failures, and evidence.
9. **Remediation** — fix findings without self-verifying them.
10. **Independent remediation verification** — rerun relevant checks and verify findings against fresh state.
11. **Serial integration** — integrate one change set at a time and reconcile before replay.
12. **Final verification** — run applicable build, test, replay, simulation, HIL, and robot gates as authorized.
13. **Release readiness** — prove artifact provenance, rollback readiness, and scoped action intent.
14. **Delivery and learning** — report facts and stage improvement proposals for separate approval.

Small, low-risk tasks may collapse stages, but never erase ownership, evidence integrity, applicable safety review, or external authorization boundaries.

## Skills

| Skill | Purpose |
|---|---|
| `$superworkflows` | Discoverable router that assesses activation and selects a session-only stage; persistent start or exact-ID resume remains explicit. |
| `$init` | Prepare CodeGraph and optionally create `.ai/project-profile.json` plus persistent run directories. |
| `$status` | Read-only run, evidence, finding, approval, integrity, and next-gate inspection. |
| `$run` | Start or resume implementation, delegation, review, remediation, integration, and verification. |
| `$review` | Independent adversarial review of plans, diffs, runs, safety claims, and release candidates. |
| `$release` | Gate serial integration, rollback proof, and separately authorized external or hardware actions; router selection alone is readiness-only. |
| `$learn` | Produce human-reviewed improvement proposals; router-selected learning remains response-only without exact or validated persistent provenance. |

## What’s Inside

### Durable Control Plane

[`scripts/loopctl.py`](scripts/loopctl.py) provides a fail-closed local state machine with:

- atomic `run.json` checkpoints;
- append-only, hash-chained `events.jsonl` journals;
- resumable `ACTIVE`, `PAUSED`, `BLOCKED`, `COMPLETE`, and `CANCELLED` status;
- P0/P1/P2 finding lifecycle and independent verification;
- allowlisted command evidence with commit, workspace digest, exit code, stdout/stderr, and SHA-256 metadata;
- approvals bound to action, target, commit, grantor, and expiry;
- idempotent external-action intents and reconciliation.

### CodeGraph Lifecycle

[`scripts/codegraphctl.py`](scripts/codegraphctl.py) keeps structural code retrieval current:

```bash
python3 scripts/codegraphctl.py prepare --root <repo>
python3 scripts/codegraphctl.py sync --root <repo>
python3 scripts/codegraphctl.py status --root <repo>
```

Use CodeGraph only when repository instructions require it, a `.codegraph/` index already exists, or the user explicitly requests initialization. Read repository `AGENTS.md` first. `prepare` can initialize a missing index, synchronize pending changes, rebuild incompatible or worktree-mismatched indexes, and validate convergence. Implicit routes, router confirmation, `$status`, and `$review` only query an existing healthy index; exact write-capable child routes run `prepare`/`sync` as applicable. Source writes make a read-only route's graph view stale.

The model formulates and interprets questions. `codegraph_explore` and `codegraph_node` MCP tools—or equivalent CLI commands—retrieve symbols, source, call paths, impact, and affected tests. Direct source and Git reads remain the final source check; executed build, test, replay, simulation, HIL, and robot commands remain behavioral evidence.

`.codegraph/` is generated tooling state. It is excluded from workspace freshness and plugin-runtime hashes.

### Specialized Agents

The plugin bundles ten namespaced agents:

| Agent | Responsibility |
|---|---|
| `sw-explorer` | Read-only CodeGraph-first repository exploration and blast-radius mapping. |
| `sw-robot-system-architect` | Read-only system boundaries across brain, cerebellum, data, runtime, deployment, and safety. |
| `sw-robot-brain-engineer` | Planning, navigation, perception-to-decision flow, arbitration, and downstream contracts. |
| `sw-biped-cerebellum-engineer` | Locomotion, RL policy contracts, joint mapping, control rates, gains, and sim2real safety. |
| `sw-robot-data-collector` | Real-robot teleoperation and mass autonomous collection, synchronization, storage, and quality gates. |
| `sw-robot-data-algorithm` | Brain datasets, preprocessing, curation, labeling, metrics, and training feedback. |
| `sw-worker` | Bounded implementation in assigned files and worktrees. |
| `sw-robot-safety-reviewer` | Independent read-only safety and production-readiness review. |
| `sw-robot-sim2real-validator` | Independent replay, simulation, HIL, sim2real, and real-robot evidence review. |
| `sw-robot-release-engineer` | Read-only provenance, integration, rollback, rollout, and operator-readiness advice. |

Install or validate them transactionally:

```bash
python3 scripts/sync_agents.py --check
python3 scripts/sync_agents.py --install
```

The installer validates TOML and role contracts, rejects symbolic-link targets, uses a lock, backs up replaced files, commits atomically, and supports rollback by transaction ID.

## Run Artifacts

Persistent mode creates:

```text
.ai/
├── project-profile.json          optional machine commands and gates
├── improvements/pending/         approval-required learning proposals
└── runs/<run-id>/
    ├── run.json                  atomic current checkpoint
    ├── events.jsonl              hash-chained event journal
    ├── evidence/<evidence-id>/   metadata, stdout, stderr, and hashes
    ├── 00-repository-exploration.md
    ├── 01-requirements-contract.md
    ├── 02-initial-plan.md
    ├── 03-plan-review.md
    ├── 04-final-plan.md
    ├── 05-ownership.md
    ├── 06-implementation-log.md
    ├── 07-integration-log.md
    ├── 08-final-verification.md
    ├── 09-delivery-report.md
    └── 10-lessons-learned.md
```

The plugin-bundled [`assets/loop-engineering/workflow.md`](assets/loop-engineering/workflow.md) is the sole workflow protocol. 

Session-only tasks, including every implicit activation, run without creating `.ai/`. Persistent machine-captured evidence requires explicit persistent activation and `.ai/project-profile.json`.

## Safety and Authority

Superworkflows separates readiness from execution. Under the protocol, implicit activation and declining persistence do not provide external or hardware authority. These actions require separate, explicit authorization bound to the exact action, target, and commit:

- push and PR/MR creation;
- tag, package, or model publishing;
- simulation-service deployment;
- HIL execution;
- robot deployment;
- real-robot execution or actuation.

No lower environment proves a higher one. Source inspection does not prove a build; a build does not prove replay; simulation does not prove HIL; HIL does not prove real-robot behavior. Missing evidence is `UNVERIFIED` or `BLOCKED`, never passed by implication.

See [`SECURITY.md`](SECURITY.md) and the [portable workflow](assets/loop-engineering/workflow.md) for the full boundaries.

## Installation

Superworkflows is distributed as a Codex plugin marketplace on GitHub. Register the marketplace from the remote repository:

```bash
codex plugin marketplace add tsungseu/superworkflows
```

Then enable the `superworkflows` plugin from that marketplace — use the `/plugins` picker in the Codex TUI, which writes a `[plugins."superworkflows@<marketplace>"]` entry with `enabled = true` to `~/.codex/config.toml`.

From a checkout of this repository, validate or install the runtime agents:

```bash
python3 scripts/sync_agents.py --check
python3 scripts/sync_agents.py --install
```

Start a new Codex thread after installation or update so the skill catalog and plugin cache are reloaded.

## Requirements

- Codex with local plugin support;
- Python 3.10 or newer;
- `tomli>=2.0` on Python 3.10; Python 3.11+ uses only the standard library;
- CodeGraph CLI when the target repository uses CodeGraph;
- bundled agent models available in the active Codex catalog: `gpt-5.4-mini`, `gpt-5.4`, `gpt-5.5`, and `gpt-5.6-sol`.

## Updating and Validation

For local development:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/sync_agents.py --check
python3 /path/to/plugin-creator/scripts/validate_plugin.py .
```

Update the Codex cachebuster with the plugin-creator helper, reinstall from the `personal` marketplace, and start a new thread. Build metadata such as `0.2.0+codex.<timestamp>` refreshes the local plugin cache without creating a new semantic release.

See the [English changelog](CHANGELOG.md) or [Chinese changelog](CHANGELOG.zh-CN.md) for release history.

## Hermes-Inspired Optimizations

Superworkflows adopts a small stable loop, progressive skill disclosure, fresh bounded reviewer/worker contexts, resumable state, context compaction through durable evidence, and controlled learning from repeated success, corrections, and dead ends. These ideas are adapted from the official Hermes Agent descriptions of its [architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture), [agent loop](https://hermes-agent.nousresearch.com/docs/developer-guide/agent-loop/), [skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/), [delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation), [context compression](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching/), and [security](https://hermes-agent.nousresearch.com/docs/user-guide/security).

It intentionally does not import autonomous skill mutation, recursive delegation, generic memory capture, provider fallback, messaging/cron behavior, or unrestricted tool loops. Trigger, persistence, CodeGraph, reviewer-identity, and attempt-budget rules are orchestration and local-control-plane checks on a same-user machine—not OS-level or cryptographic isolation. Hard isolation remains the responsibility of the Codex sandbox, tool approvals, repository permissions, and external systems; hard dispatch enforcement is deferred until a broker can atomically bind reservations, input capsules, results, and identities.

## Philosophy

- **Evidence over claims** — report only what source and executed checks support.
- **Independent review over self-certification** — implementers fix; reviewers verify.
- **Explicit durable state over conversational memory** — authorized persistent work resumes from exact, validated checkpoints.
- **Bounded ownership over uncontrolled parallelism** — one writer per file, serial integration.
- **Fail closed over optimistic continuation** — stale evidence, broken indexes, and missing authority block progress.
- **Higher-environment humility** — never promote lower-environment evidence into a production or real-robot claim.
- **Learning by proposal, not self-modification** — improvements require review, approval, validation, and rollback.

## License

Copyright (c) 2026 Tsung Xu. **Dual-licensed — choose one:**

- **GNU AGPL-3.0-only** — the open-source license in [`LICENSE`](LICENSE). You may use, modify, and distribute the software, including commercially, **provided that any software you build from it and expose over a network is also released under AGPL-3.0** (strong copyleft).
- **Commercial license** — for use that cannot comply with AGPL-3.0, for example embedding in a closed-source or proprietary product without open-sourcing your own code, a separate commercial license is available.

This is the dual-license (open-core) model: the project is genuine OSI-approved open source, and commercial licensing funds development for users who need to keep their own code closed.

For commercial-license terms, open an issue at <https://github.com/tsungseu/superworkflows/issues> or contact the maintainer.