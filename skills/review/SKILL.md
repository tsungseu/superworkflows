---
name: review
description: Perform an independent, read-only adversarial review of a robotics plan, implementation, diff, branch, run ledger, safety claim, validation result, or release candidate. Use explicitly when evidence must be challenged, findings classified P0/P1/P2, or remediation independently verified.
---

# Superworkflows Review

Assume the plan, implementation, and recorded evidence may be wrong. Seek disconfirming evidence while staying source-grounded.

## Review procedure

1. Establish scope, claimed behavior, applicable project gates, base/current commits, and reviewer independence.
2. Resolve `<plugin-root>` and run `python3 <plugin-root>/scripts/codegraphctl.py prepare --root <repo>` before source inspection. Treat initialization, rebuild, or synchronization as tooling state, not a source change or review finding.
3. Resolve `<plugin-root>` as two directories above this `SKILL.md`; validate the run with `python3 <plugin-root>/scripts/loopctl.py validate --root <repo> --task <run-id>` when state exists.
4. Independently query CodeGraph with `explore`, `callers`, `callees`, and `impact`; use `affected` to challenge test scope. Re-read decisive source and the current diff, then inspect tests, interfaces, safety limits, failure recovery, observability, rollout, and rollback.
5. Challenge each important claim with a concrete counterexample, fault injection, alternate execution path, or independent command when safe.
6. Classify findings:
   - **P0**: unsafe, corrupting, irreversible, authorization-bypassing, or fundamentally invalid; blocks progress.
   - **P1**: release-significant correctness, reliability, security, or evidence gap; remediate or explicitly defer with owner and due condition.
   - **P2**: bounded improvement or maintainability debt; track it.
7. For every finding provide evidence, impact, reproduction or reasoning, affected scope, and closure criteria.
8. Return `PASS`, `REVISE`, or `BLOCKED`. Absence of observed failure is not proof of safety.

## Independence and closure

Reviewers are read-only and do not patch the code they judge. The implementer may report `FIXED`; only a separate reviewer may mark `VERIFIED`, after checking the diff and rerunning relevant evidence. Reopen findings when evidence no longer matches the current commit.

Do not execute HIL, real-robot tests, deployment, or actuation merely to obtain stronger evidence. Those require separate action-scoped authorization.

CodeGraph establishes structural reachability and likely blast radius, not runtime correctness. Never close a finding from graph output alone.
