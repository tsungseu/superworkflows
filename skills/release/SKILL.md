---
name: release
description: Integrate and validate a robotics Superworkflows run, prove rollback readiness, and gate push, PR/MR, tag, publish, deployment, HIL, or real-robot actions with explicit scoped authorization. Use explicitly for serial integration, release readiness, or approved release execution.
---

# Superworkflows Release

Separate readiness assessment from external execution. The release engineer advises and verifies read-only; the main agent performs only explicitly authorized actions.

## Integration and release gate

1. Resolve `<plugin-root>` as two directories above this `SKILL.md`; verify repository state, run identity, base/current commits, ownership, and serial merge order. Before source inspection, run `python3 <plugin-root>/scripts/codegraphctl.py prepare --root <repo>`.
2. Integrate one branch or change set at a time. After each merge, run `python3 <plugin-root>/scripts/codegraphctl.py sync --root <repo>`, inspect `codegraph impact` for changed central symbols, use `codegraph affected` to challenge test scope, and rerun required checks.
3. Validate with:

```bash
python3 <plugin-root>/scripts/loopctl.py validate --root <repo> --task <run-id> --gate release
```

4. Require no open P0, no unexplained P1, current-commit evidence, applicable project-profile gates, and a tested rollback procedure.
5. Record unexecuted replay/simulation/HIL/robot gates as `UNVERIFIED` with reason. Never promote simulation evidence to real-robot evidence.

## Action-scoped authorization

Before an external or hardware action, obtain explicit user authorization bound to the exact action, target, and commit. Record it with `loopctl.py authorize`. Distinct actions require distinct approvals:

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
