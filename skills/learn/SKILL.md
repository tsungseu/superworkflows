---
name: learn
description: Distill completed Superworkflows runs into human-reviewed improvement proposals for project workflows, profiles, templates, agents, or skills. Use explicitly to curate recurring lessons, consolidate duplicate procedures, or propose a controlled Loop Engineering update without self-modifying the active run.
---

# Superworkflows Learn

Learning is proposal-driven: observe, distill, challenge, approve, apply in a later change, and verify. Never let a successful run silently rewrite its own rules.

## Distillation loop

1. Select completed or intentionally stopped runs with valid lineage and evidence.
2. Separate stable patterns from project accidents, model preferences, and unverified claims.
3. Identify repeated failures, manual recovery steps, stale guidance, duplicate skills, missing gates, and useful templates.
4. Create a proposal under `.ai/improvements/pending/` with provenance, affected files, expected benefit, safety impact, counterexamples, migration plan, validation plan, rollback, and expiry/review date.
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
