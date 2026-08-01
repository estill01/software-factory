---
name: author-implementation-trackers
description: Create, restructure, amend, or quality-check implementation trackers and roadmap plans. Use when Codex must turn a goal into dependency-ordered implementation blocks, apply consistent tracker boilerplate, split or renumber blocks safely, preserve status and completion evidence, or verify a tracker before implementation begins.
---

# Author Implementation Trackers

Create an implementation-ready tracker that defines outcomes, ownership,
dependencies, acceptance, evidence, and explicit stopping boundaries. Keep
tracker authoring separate from implementation.

## Resolve the authoring request

1. Resolve the repository, requested goal or objective, tracker path, and
   whether the request creates, amends, splits, renumbers, or verifies a
   tracker.
2. Read applicable repository instructions and inspect the live tree,
   architecture, tests, existing trackers, and Git state before drafting.
3. Treat existing code and accepted work as evidence to classify, not as
   automatically complete or automatically obsolete.
4. Identify the authoritative owners to reuse. Do not design parallel writers,
   ledgers, schemas, runtimes, or status systems merely to make the tracker
   look comprehensive.
5. Ask only when a missing decision would materially change scope or ownership;
   otherwise state a bounded assumption and continue.

Read [references/block-contract.md](references/block-contract.md) before
creating or materially restructuring blocks. For a new tracker, copy and adapt
[assets/implementation-tracker-template.md](assets/implementation-tracker-template.md)
rather than recreating the document shape from memory.

## Build the tracker

1. State the intended outcome and concrete completion definition before listing
   implementation activity.
2. Describe the target architecture and existing owners narrowly enough to
   prevent duplicate authority.
3. Map predecessor work and source adaptations when they affect implementation;
   classify each as reuse, adapt, remediate, replace, retire, or not adopted.
4. Split work at real ownership, dependency, mutation, review, or stopping
   boundaries. Let block count emerge from those boundaries.
5. Use continuous integer block identifiers starting at 0 unless an inherited
   tracker already establishes another explicit convention.
6. Give every block one primary outcome and one narrow authoritative area. If
   two clauses can be accepted, reverted, reviewed, or scheduled independently,
   split them unless one is merely necessary plumbing for the other.
7. Give every full-contract block a `Scope and non-goals` section. Tie every
   proposed mechanism to the objective or an acceptance criterion; remove
   useful-looking adjacent machinery that fails that necessity test.
8. Treat global safeguards, inherited instructions, inspected source code, and
   exclusions as constraints, not authorization to add features, schemas,
   tests, fixtures, registries, or generalized frameworks.
9. Add resource or independent-review sections only when the work actually
   crosses those boundaries.
10. Keep dependencies acyclic and earlier than their consumers. Make each stop
   boundary exclude the next block's mutation or decision.
11. Add a status/order table that exactly matches the block headings and status
   values.
12. Define the execution contract, completion-evidence format, verification
   matrix, and terminal completion rule once at tracker level when several
   blocks share them.
13. Distinguish mechanical proof, substantive judgment, external approval, and
    legal or release status. Never let passing tests or populated records imply
    a higher-order outcome by themselves.
14. Define the economical normal path when a Block could otherwise repeat broad
    scans, suites, renders, provider work, review, or per-item processing. Name
    reuse inputs, batch boundaries, widening triggers, validation order, and the
    stop condition; do not add a scheduler, cache service, or telemetry system
    merely to express those constraints.
15. Require likely-mutating design or substantive review before expensive final
   mapped validation where the workflow permits it. Freeze the exact candidate
   revision before acceptance validation and exact-commit audit; any later code
   change makes prior affected proof diagnostic rather than current.
16. Keep non-delegable operator gates rare and explicit. A label such as
   `responsible human adoption`, `operator decision`, or `approval required`
   does not establish necessity. Codex should resolve and apply an ordinary
   non-reserved strategic or implementation choice under the user's standing
   imperative when current evidence, objectives, decision rights, and bounded
   judgment select a supported path. A hard gate requires new user-specific
   factual input, a material preference/trade-off not resolved by current
   objectives, a counsel-reserved choice, credential/budget authority,
   destructive ambiguity, external communication/release, or another boundary
   Codex genuinely cannot cross. For every such gate, name the exact decision,
   why Codex cannot resolve it,
   the earliest predecessor that can make a complete decision packet available,
   the dependent scope it alone blocks, and all safe work that may continue.
   Place decision readiness before the hard stop whenever dependencies permit;
   never let an ordinary implementation choice become a user gate merely
   because the tracker author did not choose a bounded default.

Use concise boilerplate. Do not duplicate a global rule inside every block;
reference the governing section and add only the block-specific consequence.

Before finalizing each Block, apply this feature-creep test:

- Is every required item necessary to make the Block objective true?
- Does an existing owner already represent it?
- Is any new abstraction justified by a reproduced supported gap rather than
  by possible future reuse?
- Are negative tests limited to supported paths and concrete invariants?
- Does the Stop clause prevent adjacent downstream work?
- Does the normal execution path reuse current accepted evidence, avoid
  per-item or whole-scope repetition, and converge after a failure instead of
  blindly retrying or widening?
- Is every user-blocking gate genuinely non-delegable, forecast at its earliest
  decision-ready point, and scoped so unrelated work does not stop with it?
- Would the requested user response contribute new information or authority, or
  merely rubber-stamp the system's single eligible reviewed recommendation? A
  rubber stamp is not a valid gate.

If any answer is no, narrow the Block, reuse the owner, defer the adjacent work,
or create a later single-focused Block when that work is genuinely required.

## Amend or renumber safely

Read [references/amendment-and-renumbering.md](references/amendment-and-renumbering.md)
before editing an existing tracker. Preserve accepted status, commit and review
evidence, historical findings, and interpretable old block references. Apply
renumbering mechanically, then inspect every dependency and semantic
cross-reference. Do not mark newly introduced work complete merely because
adjacent implementation exists.

## Record status and evidence

Read [references/evidence-and-status-rules.md](references/evidence-and-status-rules.md)
when the tracker includes accepted work, remediation, independent review,
currentness, or terminal proof. Tracker status is an implementation-planning
record, not a substitute for native product or domain authority.

## Verify before handoff

Run the read-only verifier:

```bash
python3 /Users/ethanstillman/.codex/skills/author-implementation-trackers/scripts/verify_tracker.py \
  path/to/tracker.md --profile full
```

Use `--profile core` only for an inherited tracker whose established house
style intentionally omits the full per-block sections. Use `--json` when
machine-readable diagnostics are useful.

Also run the repository's documentation checks, changed-test plan, formatting
checks, and link checks when applicable. Inspect the final diff for stale block
numbers, status drift, duplicated ownership, dependency cycles, unsupported
completion claims, and stop-boundary overlap.

## Finish at the authoring boundary

If the user asked to write the tracker, commit only the owned, validated tracker
slice when repository policy permits. Report the tracker path, block range,
material assumptions, verifier results, and first eligible block.

Do not implement a block during tracker authoring unless the user separately
requests implementation. Hand implementation to `$implement-tracker-blocks`,
which rereads the selected block and executes it one bounded block at a time.
