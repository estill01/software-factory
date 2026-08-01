# {{TRACKER_TITLE}}

- Tracker status: `planning`
- Tracker sequence: Blocks 0–{{TERMINAL_BLOCK}}
- Repository: `{{REPOSITORY}}`
- Governing objective: `{{OBJECTIVE_REFERENCE}}`

## 1. Purpose and intended outcome

{{State the user or product outcome. Do not substitute implementation activity
for the intended result.}}

Completion means:

- {{observable completion condition}}
- {{observable completion condition}}

## 2. Target architecture and authority boundaries

{{Describe the target flow, authoritative owners, derived views, and the
boundaries that prevent duplicate authority.}}

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| {{concern}} | `{{path or authority}}` | reuse/adapt/remediate |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| {{source}} | `{{revision}}` | reuse/adapt/remediate/replace/retire/not-adopted | 0 | {{work}} |

Omit this section when there is no predecessor or external translation basis.

## 5. Scope, non-goals, and proportionality

### In scope

- {{required capability}}

### Out of scope

- {{explicit adjacent capability}}

### Proportionality

A finding authorizes the narrowest correction of its concrete invariant. Reuse
existing owners and omit optional hardening that has no reproduced, in-scope
failure tied to this tracker's objective.

## 6. Block execution contract

1. Execute Blocks 0–{{TERMINAL_BLOCK}} in dependency order.
2. Re-read the selected Block and inspect the live repository before editing.
3. Preserve unrelated and in-flight work.
4. Implement through the narrowest existing owner and stop at the Block's
   boundary.
5. A global safeguard, inspected source, existing owner, or exclusion constrains
   work only when the Block crosses that boundary; it does not authorize new
   machinery, fields, tests, or a separate audit dimension.
6. Optional hardening requires a reproduced supported failure tied to the
   Block's objective. Otherwise omit it.
7. Run focused validation, mapped validation, and required independent review.
8. Before expensive final validation, finish all known in-scope work and any
   review permitted to change the candidate. Freeze the candidate revision;
   later changes stale only the affected validation and review evidence.
9. Reuse exact current artifacts and cheap currentness checks before deep scans;
   batch coherent work and widen only on a declared trigger.
10. Record only exact current evidence. Label aborted, pre-correction, or
    changed-during-validation runs diagnostic.
11. Audit and accept one Block before advancing, then stop rather than search
    for optional hardening.
12. A genuine input dependency blocks only its exact subjects and descendant
    closure. Record its decision packet, blocked-scope root, safe-frontier root,
    permitted provisional/common work, prohibited authority effects, and revisit
    trigger; continue every dependency-independent slice. Do not mark a Block or
    run blocked while the safe frontier is nonempty.
13. For supervised input gates, run one bounded 20-minute Sol Max resolution
    attempt before requesting user guidance. If it remains unresolved, send the
    complete decision brief, open a 20-minute response window, and continue safe
    work plus the remaining bounded attempts during that window. Select and
    proceed only within delegated authority; otherwise use a bounded safe
    deferral with the missing fact or reserved action explicit.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
- External/domain revision or root: `<value or not-applicable with reason>`
- Inputs: `<paths, IDs, versions, hashes>`
- Outputs: `<paths, IDs, versions, hashes>`
- Focused validation: `<commands and results>`
- Mapped validation: `<plan, commands, and results>`
- Candidate freeze: `<commit/content root and whether it changed afterward>`
- Remediation closure: `<finding-to-change-to-proof matrix or not-applicable>`
- Resource posture: `<bounds, actual use, widening or not-applicable>`
- Independent review: `<evidence or not-applicable with reason>`
- Retained open work: `<items or none>`
- Decision/continuation posture: `<decision packet, blocked scope, safe frontier,
  timed attempts, handoff, resumed evidence, or not-applicable>`
- Post-block audit: `<accepted, reopened, or blocked with reason>`
- Git durability: `<commit and push posture>`
```

## 7. Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | {{BLOCK_0_TITLE}} | — | `not-started` |
| 1 | {{BLOCK_1_TITLE}} | 0 | `not-started` |

Required order:

`0 → 1`

## Block 0 — {{BLOCK_0_TITLE}}

Status: `not-started`

### Objective

{{One primary outcome.}}

### Inputs and dependencies

- {{Exact inputs; use none for the initial Block when appropriate.}}

### Required work

- {{Owned implementation change.}}
- {{Existing owner reused.}}

### Scope and non-goals

- In scope: {{the one narrow authoritative area this Block changes}}.
- Not in scope: {{adjacent capability owned later or intentionally excluded}}.
- New machinery is permitted only when the objective cannot be met through an
  existing owner and the acceptance-critical need is stated here.

### Deliverables and recorded state

- {{Concrete code, schema, record, artifact, or read view.}}

### Resource and economy contract

{{State deterministic bounds, formulas, and widening rules, or write
`Not applicable: <reason>`.}}

### QA and independent review

{{State focused mechanical proof and substantive review separation, or write
`Not applicable: <reason>`.}}

### Acceptance

- {{Observable acceptance condition.}}

### Negative tests

- Reject {{representative supported failure}}.

### Completion evidence

Pending.

### Stop

Stop before {{the first downstream action owned by Block 1}}.

---

## Block 1 — {{BLOCK_1_TITLE}}

Status: `not-started`

### Objective

{{One primary outcome.}}

### Inputs and dependencies

- Block 0.

### Required work

- {{Owned implementation change.}}

### Scope and non-goals

- In scope: {{the one narrow authoritative area this Block changes}}.
- Not in scope: {{adjacent capability owned elsewhere}}.
- Do not generalize this Block for hypothetical future use.

### Deliverables and recorded state

- {{Concrete output.}}

### Resource and economy contract

{{Bounds or not-applicable reason.}}

### QA and independent review

{{Required proof and reviewer posture or not-applicable reason.}}

### Acceptance

- {{Observable acceptance condition.}}

### Negative tests

- Reject {{representative supported failure}}.

### Completion evidence

Pending.

### Stop

Stop before {{work outside this tracker or its next phase}}.

## 8. Verification matrix

| Capability/invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| {{invariant}} | 0 | 1 | 1 |

## 9. Final completion definition

The tracker is complete only when every Block is accepted at exact current
revisions, required evidence and independent reviews are current, retained open
work is accurately represented, the verification matrix passes, and no Block
crossed its declared stop boundary.
