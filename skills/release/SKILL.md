---
name: release
description: Integrate and validate a robotics Superworkflows run, prove rollback readiness, and gate push, PR/MR, tag, publish, deployment, HIL, or real-robot actions with explicit scoped authorization. Use only when explicitly invoked with $release or selected from an already explicit persistent workflow; never use implicit semantic selection as external or hardware authority.
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

# Superworkflows Release

Separate readiness assessment from external execution. The release engineer advises and verifies read-only; the main agent performs only explicitly authorized actions.

## Entry boundary

Preserve router provenance, persistence, and authority. A router-selected release request without an exact `$release` invocation or a validated persistent Run whose lineage records exact `$run` activation is readiness-only: query an existing healthy CodeGraph index read-only, do not prepare/sync the index, integrate, mutate the ledger, or perform external/hardware actions, and hand off the exact `$release` invocation required for the guarded flow. Even exact `$release` remains readiness-only when no persistent Run can be validated.

## Integration and release gate

1. Resolve `<plugin-root>` as two directories above this `SKILL.md`; verify repository state, exact Run identity, base/current commits, ownership, and serial merge order read-only. Stop at readiness if the persistent Run is missing or invalid.
2. After the entry boundary and Run validation pass, prepare an existing CodeGraph index; initialize a missing one only through exact `$init` or equivalent explicit indexing authorization and never against repository instructions.
3. Integrate one branch or change set at a time. After each merge, run `python3 <plugin-root>/scripts/codegraphctl.py sync --root <repo>`, inspect `codegraph impact` for changed central symbols, use `codegraph affected` to challenge test scope, and rerun required checks.
4. Validate with:

```bash
python3 <plugin-root>/scripts/loopctl.py validate --root <repo> --task <run-id> --gate release
```

5. Require no open P0, no unexplained P1, current-commit evidence, applicable project-profile gates, and a tested rollback procedure.
6. Record unexecuted replay/simulation/HIL/robot gates as `UNVERIFIED` with reason. Never promote simulation evidence to real-robot evidence.

## Action-scoped authorization

Before an external or hardware action, obtain explicit user authorization bound to the exact action, target, and commit. Record it with `loopctl.py authorize`. Distinct actions require distinct approvals:

Implicit router selection, semantic keywords, session-only work, and declining `.ai` persistence can never satisfy this gate. Without a persistent validated Run, perform readiness analysis only and report the action `BLOCKED`.

- push;
- create PR/MR;
- tag;
- publish package or model;
- deploy to simulation service;
- HIL execution;
- deploy to robot;
- real-robot execution or actuation.

Recheck the approval immediately before acting. A changed commit, target, action, or expired approval invalidates it. Installation, plugin invocation, a prior run, and generic phrases such as “finish it” do not broaden authorization.

Before the authorized action, record an intent with `loopctl.py action-begin --operation-id <stable-id> --expected-before-state <state>`. After execution or a lost response, reconcile the remote/hardware state and record `action-complete --result SUCCESS|FAILED|UNKNOWN`. Never replay a `PENDING` or `UNKNOWN` operation blindly.

## Rollback proof and delivery

The rollback record must name the artifact/config/model to restore, command or operator procedure, trigger conditions, estimated recovery time, and evidence that the procedure works in the highest authorized environment. Report readiness separately from actions actually performed.
