---
name: learn
description: Distill completed Superworkflows runs into human-reviewed improvement proposals for project workflows, profiles, templates, agents, or skills. Use only when explicitly invoked with $learn or selected from an explicit completed workflow to curate recurring lessons, corrections, recovered dead ends, or controlled Loop Engineering updates without self-modifying the active run.
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

# Superworkflows Learn

Learning is proposal-driven: observe, distill, challenge, approve, apply in a later change, and verify. Never let a successful run silently rewrite its own rules.

## Entry boundary

Preserve router provenance. Router-selected session-only learning may summarize candidate lessons in the response but must not create `.ai/` or write a proposal. Writing `.ai/improvements/pending/` requires exact `$learn` or selection as the learning stage of a validated completed Run whose lineage records exact `$run` activation, plus the normal approval and review gates below.

## Distillation loop

1. Select completed or intentionally stopped runs with valid lineage and evidence.
2. Separate stable patterns from project accidents, model preferences, and unverified claims.
3. Identify repeated failures, successful recovery from dead ends, explicit user corrections, manual recovery steps, stale guidance, duplicate skills, missing gates, and useful templates. Require recurrence across multiple runs or label a one-run candidate as provisional; tool-call count alone is not evidence of generality.
4. Create a proposal under `.ai/improvements/pending/` with source Run IDs, evidence hashes, observation count, correction provenance, counterexamples, privacy review, affected files, expected benefit, safety impact, migration, offline evaluation, canary, rollback, and expiry/review date. Do not retain raw prompts when a structured digest is sufficient.
5. Obtain an independent adversarial review. Safety gates may be strengthened by proposal; weakening or deleting one requires explicit human justification and approval.
6. Apply only after explicit approval, in a separate run/change set. Revalidate affected triggers, state migrations, scripts, and safety gates.

## Curation policy

Track candidate procedures as active, stale, superseded, or archived. Never auto-delete. Prefer consolidation when several skills encode the same authority boundary; preserve separate skills when permissions or intent differ.

## Prohibited self-improvement

- no editing the active run's workflow, findings, or evidence to make it pass;
- no automatic skill or agent installation;
- no learning secrets, transient paths, or robot-specific unsafe defaults;
- no converting historical success into a production or real-robot safety claim;
- no applying a proposal without human approval and independent validation.
- no weakening repository-instruction precedence, implicit persistence/CodeGraph-write prohibition, external/hardware authority, reviewer independence, or stale-evidence gates without a named safety exception, adversarial review, regression suite, canary, rollback, and explicit human approval.
