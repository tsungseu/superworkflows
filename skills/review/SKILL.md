---
name: review
description: Perform an independent, read-only adversarial review of a robotics plan, implementation, diff, branch, run ledger, safety claim, validation result, or release candidate. Use when explicitly invoked with $review or selected session-only by the Superworkflows router because evidence, failure paths, or P0/P1/P2 findings must be challenged.
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

# Superworkflows Review

Assume the plan, implementation, and recorded evidence may be wrong. Seek disconfirming evidence while staying source-grounded.

## Review procedure

1. Establish scope, claimed behavior, applicable project gates, base/current commits, and reviewer independence.
2. Resolve `<plugin-root>` and obey repository CodeGraph instructions. Check and query an existing healthy `.codegraph/` index read-only; neither implicit nor explicit review may prepare, synchronize, rebuild, or initialize it. If stale, report the limitation and verify decisive facts from current source/Git. Index maintenance requires exact `$init` or separate explicit indexing authorization and remains outside the read-only review.
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

The local ledger records reviewer identity and evidence but does not cryptographically prove model identity against a process that can rewrite the whole Run. Do not treat a changed `--actor` string or `--independent` flag alone as proof; require an actual fresh read-only reviewer result in the orchestration trace.

Do not execute HIL, real-robot tests, deployment, or actuation merely to obtain stronger evidence. Those require separate action-scoped authorization.

CodeGraph establishes structural reachability and likely blast radius, not runtime correctness. Never close a finding from graph output alone.
