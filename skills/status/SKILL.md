---
name: status
description: Inspect Superworkflows Loop Engineering state without changing it. Use explicitly with $status or when selected session-only by the Superworkflows router to list runs, find active candidates, check stage and gate status, validate evidence integrity, summarize findings and approvals, or determine the next safe action.
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

# Superworkflows Status

Provide a read-only, evidence-grounded status view.

## Procedure

1. Resolve the repository root and read local instructions.
2. Resolve `<plugin-root>` as two directories above this `SKILL.md`. Run `python3 <plugin-root>/scripts/loopctl.py status --root <repo>` or add `--task <run-id>`.
3. Run `python3 <plugin-root>/scripts/loopctl.py validate --root <repo> --task <run-id>` for the selected run.
4. Compare the recorded base and current commit, evidence hashes, open findings, approval scope, and artifact policy.
5. Report: run identity and lineage, state/stage, latest event, P0/P1/P2 counts, evidence integrity, valid/expired approvals, blockers, and the next gate.

## Boundaries

- Do not create, resume, transition, repair, or rewrite a run.
- Do not select or resume a Run from semantic title similarity. Report exact IDs and ambiguity.
- Do not spawn write-capable agents.
- Never infer success from a document's existence. Distinguish recorded claims from independently verified evidence.
- A hash chain detects accidental or partial modification; it is not a trusted external signature against complete history replacement.
