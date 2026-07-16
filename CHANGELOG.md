# Changelog

[English](CHANGELOG.md) | [简体中文](CHANGELOG.zh-CN.md)

All notable changes to Superworkflows are documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and semantic release versions exclude the local `+codex.<cachebuster>` build metadata used to refresh the Codex plugin cache.

## [0.2.5] - 2026-07-16

### Added

- Added a side-effect-free multilingual activation assessor, versioned trigger policy, and positive, negative, ambiguous, and hostile trigger regression corpus.
- Added orthogonal routing, persistence, and authority decisions so semantic activation cannot imply durable state or external permission.
- Added negated-action handling and target-aware deployment patterns to reduce both unsafe misses and implementation-task false positives.

### Changed

- Enabled implicit invocation only for the top-level `$superworkflows` router; all six child skills remain explicit or router-selected.
- Restricted every implicit activation to session-only execution: no `.ai` creation or resume, CodeGraph mutation or initialization, semantic Run selection, or external/hardware action.
- Adapted Hermes Agent ideas into fresh bounded delegation contexts, progressive skill disclosure, resumable evidence, and controlled learning from repeated success, corrections, and dead ends.
- Clarified that local reviewer identity and agent/review attempt budgets are orchestration controls, not hard or cryptographic enforcement without a dispatch broker.
- Preserved route, persistence, current authority, and required external authority as separate outputs; made exact `$init`/`$run` invocation mandatory for persistent mutation even after explicit router activation.

### Security

- Made ambiguous continuation advisory-only and required an explicit `$run` plus exact Run ID for persistent resume.
- Blocked external and hardware authority on implicit activation or when persistence is declined.
- Added privacy, provenance, counterexample, canary, rollback, and non-waivable-invariant requirements to learning proposals.
- Documented that trigger, persistence, CodeGraph, and Skill authority rules are auditable protocol controls rather than an OS capability boundary.

### Documentation

- Added maintained English and Simplified Chinese README and changelog pairs.
- Expanded the README with quickstart examples, the 14-stage workflow, skill and agent catalogs, run artifacts, CodeGraph/model/tool responsibilities, safety boundaries, requirements, and update instructions.

## [0.2.0] - 2026-07-15

### Added

- Split the original mega-skill into seven explicit skills: `superworkflows`, `init`, `status`, `run`, `review`, `release`, and `learn`.
- Added a persistent guarded state machine with atomic `run.json`, hash-chained `events.jsonl`, lineage, pause/resume, findings, evidence, approvals, and external-action reconciliation.
- Added machine-captured command evidence with commit/workspace identity, stdout/stderr hashes, freshness checks, and profile-defined complete/release gates.
- Added P0/P1/P2 finding lifecycle, independent remediation verification, and stale-verification detection.
- Added action-scoped authorization for push, PR/MR, tag, publish, simulation deployment, HIL, robot deployment, and real-robot execution.
- Added the fail-closed `codegraphctl.py` lifecycle controller with initialization, synchronization, reindex recovery, health validation, and bounded convergence.
- Added CodeGraph `explore`, `node`, `callers`, `callees`, `impact`, and `affected` checkpoints with direct-source re-read rules.
- Added ten namespaced `sw-*` robotics agents covering exploration, architecture, brain, cerebellum, data collection, data algorithms, implementation, safety, sim2real, and release.
- Added portable workflow assets, project-profile schema, run templates, JSON schemas, compatibility metadata, and proposal-only controlled learning.
- Added regression tests for control-state integrity, evidence tampering, authorization idempotency, symlink rejection, CodeGraph lifecycle failure modes, and transactional agent installation.

### Changed

- Made the plugin-bundled `assets/loop-engineering/workflow.md` the sole workflow protocol.
- Stopped generating, checking, or fingerprinting project `.ai/workflow.md`, `.ai/project-profile.md`, and copied workflow templates.
- Shortened child-skill invocation names to `$init`, `$status`, `$run`, `$review`, `$release`, and `$learn` inside the plugin namespace.
- Required CodeGraph preparation before source exploration and post-write synchronization before subsequent review or graph queries.
- Defined the model as query planner and reasoner, CodeGraph as structural retrieval, direct source/Git reads as source verification, and executed commands as behavioral evidence.
- Made architecture, exploration, safety, sim2real, and release agents read-only and independent from implementation.
- Replaced byte-only agent synchronization with semantic validation and a locked, symlink-safe, transactional installer with backup and rollback.
- Excluded `.ai/` and `.codegraph/` from workspace freshness, and excluded `.codegraph/` from plugin-runtime hashes.

### Security

- Installation and skill invocation no longer imply authorization for external systems or robot hardware.
- Approvals are bound to action, target, commit, grantor, and expiry, and are rechecked immediately before execution.
- External actions record stable intents and reconciliation results to prevent blind replay after lost responses.
- Hardware, rollback, and external commands are rejected by the local evidence executor.
- P0 findings block guarded progress; P1 findings require independent verification or explicit owner/reason/due-condition deferral.

### Fixed

- Prevented CodeGraph index maintenance from invalidating workspace evidence or persistent plugin-runtime identity.
- Added multi-step convergence for CodeGraph states that require incremental synchronization followed by full reindexing.
- Made malformed, stale, mismatched, unavailable, failed, or timed-out CodeGraph states fail closed.

## [0.1.0]

### Added

- Introduced the initial single-skill, 14-stage robotics AI coding workflow.
- Bundled the first robotics agent role snapshots.
