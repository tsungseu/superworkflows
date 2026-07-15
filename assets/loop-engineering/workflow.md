# Portable Robotics AI Coding Loop Engineering

This file is the sole portable workflow protocol for Superworkflows. A repository may provide machine settings in `.ai/project-profile.json`; the profile may strengthen but never silently weaken higher-authority safety or authorization rules. Do not copy this workflow into project repositories.

## 1. First principles

Engineering is a feedback loop, not a long prompt:

```text
observe repository and runtime facts
  -> form an explicit contract
  -> plan and challenge the plan
  -> implement in bounded ownership
  -> challenge the implementation
  -> remediate and independently verify
  -> integrate serially
  -> validate at the highest authorized environment
  -> deliver through scoped approvals
  -> distill reviewed improvement proposals
  -> resume from durable state when interrupted
```

Before code exploration, run `python3 <plugin-root>/scripts/codegraphctl.py prepare --root <repo>`. The controller initializes a missing index, incrementally synchronizes source changes, rebuilds incompatible or worktree-mismatched indexes, verifies convergence, and fails closed. Treat `.codegraph/` as generated tooling state and exclude it from workspace, plugin-runtime hashes, and evidence freshness.

The 14 stages are a human-facing projection. Execution is the state graph in `workflow-spec.json`, including review/remediation back-edges, pause/block/cancel semantics, and external-approval boundaries.

## 2. Authority and truth

Apply authority in this order:

1. system, developer, sandbox, and explicit user authorization;
2. repository `AGENTS.md` and equivalent local instructions;
3. optional project `.ai/project-profile.json` machine settings;
4. plugin `workflow-spec.json` and this baseline, the sole workflow protocol;
5. selected skill and delegated-agent prompt.

Use one truth source per concern:

- `workflow-spec.json`: portable state and gate semantics;
- project profile: repository commands and environment-specific gates;
- `run.json` plus `events.jsonl`: current run state and lineage;
- runtime `~/.codex/agents/sw-*.toml`: active agent configuration;
- source and installed plugin hashes recorded in a run: provenance.

Markdown is explanatory evidence, not the machine control plane.

### CodeGraph lifecycle and limits

Use CodeGraph as the structural map, the model as the reasoner, direct source/Git reads as the final source check, and executed build/test/replay/simulation/HIL/robot commands as behavioral evidence.

1. Run `codegraphctl.py prepare` before exploration, planning, review, or source-sensitive release checks.
2. Let the model formulate and interpret structural questions. Prefer `codegraph_explore`/`codegraph_node` MCP tools when available; otherwise use equivalent CLI `explore`, `node`, `callers`, and `callees` queries.
3. Use `impact` before finalizing changes to central symbols or contracts.
4. After every implementation, remediation, or integration write boundary, run `codegraphctl.py sync` before another graph query or review.
5. Use `affected` to propose tests, but never replace project-profile gates or independently executed checks.
6. Re-read decisive source and current diffs. Never treat graph reachability as runtime correctness or higher-environment evidence.

## 3. Persistent run protocol

Each run lives under `.ai/runs/<run-id>/`:

```text
run.json                  atomic current checkpoint
events.jsonl              append-only, hash-chained event journal
evidence/<evidence-id>/   command metadata, stdout, stderr, hashes
00-repository-exploration.md
01-requirements-contract.md
02-initial-plan.md
03-plan-review.md
04-final-plan.md
05-ownership.md
06-implementation-log.md
07-integration-log.md
08-final-verification.md
09-delivery-report.md
10-lessons-learned.md
```

`run.json` records schema/plugin versions, lineage, repository and workspace fingerprints, current state/status, route trace, findings, evidence, approvals, external actions, event sequence, and event hash. State changes are locked, journaled, and atomically checkpointed. On recovery, reconcile journal, snapshot, Git/worktrees, and external state before retrying anything.

The hash chain detects accidental or partial mutation. It is not a trusted signature against an actor that can replace the entire run directory. High-assurance deployments should export evidence to an access-controlled external store or sign checkpoints.

## 4. Baseline stage projection

| Stage | Activity | Required output or gate |
|---|---|---|
| 1 | Repository exploration | verified scope, paths, interfaces, risks |
| 2 | Requirements and safety contract | invariants, exclusions, acceptance, evidence plan |
| 3 | Initial plan | work-item DAG, ownership, tests, rollback |
| 4 | Independent plan review | P0/P1/P2 findings and decision |
| 5 | Final plan | findings resolved or explicitly tracked |
| 6 | Ownership and worktrees | one writer per file and integration owner |
| 7 | Implementation | bounded diffs and local evidence |
| 8 | Independent code/safety review | source-grounded findings tied to commit/digest |
| 9 | Remediation | fixes tied to finding IDs |
| 10 | Remediation verification | independent `VERIFIED`, never self-closure |
| 11 | Serial integration | one merge at a time, reconcile before replay |
| 12 | Final verification | build/test/replay/sim/HIL/robot gates as authorized |
| 13 | Release readiness | rollback proof and scoped action intents |
| 14 | Delivery and learning | factual report plus pending improvement proposals |

Small low-risk work may merge activities, but never remove ownership, fresh evidence, safety review when applicable, or external authorization.

## 5. Delegation and ownership

The main/integration agent is the only run-ledger writer. A delegated assignment includes:

- run and work-item IDs;
- objective and acceptance criteria;
- input commit and artifact hashes;
- allowed files and prohibited actions;
- required commands/evidence;
- attempt, budget, and stop conditions;
- required result envelope.

Children work in isolated context/worktrees when writing, must not recursively delegate or invoke the router, and return a structured summary. Reviewer identity must be independent from the implementer. A read-only review role never patches what it judges.

## 6. Findings and remediation

- **P0**: unsafe, corrupting, irreversible, authorization-bypassing, or invalid. It blocks guarded transitions and cannot be deferred.
- **P1**: release-significant correctness, reliability, security, or evidence gap. It must be independently verified or deferred with owner, reason, and due condition.
- **P2**: bounded improvement or maintainability debt. It remains visible until verified or explicitly deferred.

The implementer may mark a finding `FIXED`; only an independent reviewer may mark it `VERIFIED`, bound to the reviewed commit/workspace digest and evidence. A material workspace change makes old verification stale.

## 7. Evidence policy

Prefer machine-captured evidence. Every command record includes argv, cwd, start/end time, exit code, commit, workspace digest, stdout/stderr SHA-256, and metadata SHA-256. Never claim an unexecuted check passed. Distinguish:

- source-only inference;
- build/unit/integration evidence;
- replay/simulation evidence;
- HIL evidence;
- real-robot observation.

No lower environment proves a higher one. Do not capture complete environments or secrets in evidence metadata.

The local evidence executor runs only exact argv arrays declared in the project profile. It rejects HIL, real-robot, rollback, and external actions; those go through separately authorized execution and reconciliation.

## 8. External actions and robot authority

Push, PR/MR creation, tag, publish, deployment, HIL, and real-robot actions require separate approval bound to action, target, commit, grantor, and expiry. Record an idempotent operation intent before execution. If a response is lost, reconcile external state; never blindly replay a pending operation.

Plugin installation, skill invocation, historical approval, or a broad request to “finish” is not external-action authorization. Real-robot execution and actuation always remain a separate gate.

## 9. Interruption, budgets, and recovery

Checkpoint after every tool-result boundary that changes engineering truth: stage, evidence, finding, approval, merge, or external-action intent/result. A timeout means `PAUSED`, `BLOCKED`, or retryable failure—not success. Approval waits never default to approval.

Project-profile budgets bound evidence-command runtime, state-route hops, agent attempts, and review/remediation cycles. Exhaustion blocks or forks the run; it never turns into an implicit pass.

Resume validates schema/plugin compatibility, event integrity, repository identity, current workspace, stale reviewer evidence, open operation intents, and agent contracts. If lineage or authority changed materially, create a child run rather than silently continuing.

## 10. Controlled learning

Learning follows:

```text
run evidence -> candidate -> offline replay/eval -> adversarial review
-> explicit human approval -> separate change -> canary/regression
-> promote or rollback
```

Write candidates only to `.ai/improvements/pending/`. Never auto-edit a production skill, safety gate, or active run. Curate with `active`, `stale`, `superseded`, and `archived`; never auto-delete.
