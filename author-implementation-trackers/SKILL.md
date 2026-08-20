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

## Own the canonical program entry point

Every compatible repository uses `docs/tracker.md` as its stable canonical
implementation-program entry point. Resolve it before creating, amending,
splitting, renumbering, or verifying any detailed tracker.

- For a new single-program repository, author the complete detailed tracker at
  `docs/tracker.md` unless a direct requirement or existing repository owner
  requires a separate detailed path. When the detailed tracker must live
  elsewhere, create `docs/tracker.md` as the canonical routing index in the
  same authoring slice.
- When multiple detailed programs or required successors exist, keep exactly
  one current program queue in the index. Name stable program-qualified Block
  identities, exact tracker paths and current hashes, accepted/current status,
  first eligible Blocks, dependency or activation boundaries, required
  successor order, terminal observable outcome, and the disposition of every
  other tracker that might otherwise look active.
- For an existing repository without the entry point, migrate narrowly.
  Preserve detailed tracker bytes, accepted status, evidence, and interpretable
  history; archive or classify displaced `docs/tracker.md` bytes explicitly;
  update only routing references that must follow the stable entry point. Do
  not renumber detailed Blocks merely to make a global-looking sequence.
- Treat assigned spans, task labels, run IDs, waves, reviewer scopes, watcher
  cursors, and automation batches as scheduling metadata, never as authority
  to narrow or complete the canonical program range.
- A canonical-index edit changes routing, not implementation status. It cannot
  accept a Block, replay or replace proof, contract direct-user scope, infer a
  successor's completion, or make a historical tracker current.

Do not finish tracker authoring while `docs/tracker.md` is missing, points to
stale tracker bytes, leaves two programs apparently active, omits a required
successor needed for the stated outcome, or conflicts with repository
instructions. Repair those defects within the bounded authoring scope and
continue without asking for manual Resume.

Read [references/block-contract.md](references/block-contract.md) before
creating or materially restructuring blocks. For a new tracker, copy and adapt
[assets/implementation-tracker-template.md](assets/implementation-tracker-template.md)
rather than recreating the document shape from memory.

## Build the tracker

1. State the intended outcome and concrete completion definition before listing
   implementation activity.
   Define one tracker-level mission frame containing the primary outcome,
   observable completion, ordinary effect classes needed to achieve it, hard
   direct authority or safety boundaries, and changes that would materially
   alter or reverse the goal. Keep the semantic frame in the tracker rather
   than duplicating it in every Block.
   For every new full-profile tracker, also reconstruct one concise
   `Target-product capability frame` from direct mission and repository sources.
   Classify its applicability as `consequential`, `routine`, or
   `not-applicable`, and state the rationale, exact sources, product thesis and
   intended effect, protected capabilities, architecture strategy, requested
   capability, proportionality, tradeoffs, and uncertainty. A routine or
   not-applicable frame may cite no product source only when its rationale says
   why no product doctrine is asserted.
   Treat work as consequential when it changes feature behavior, canonical
   representation, architecture strategy, operating model, or a protected
   capability. For each consequential Block, add only its local
   `Target-product capability delta`: intended gain, potential loss or
   regression, protected-capability effect, architecture/operating-model
   effect, and tradeoff with source evidence. Routine and not-applicable Blocks
   need only a posture and concrete justification. Do not repeat the global
   frame in each Block.
   Reconstruct the supported capability before decomposing requested feature
   wording: a literal button, endpoint, command, or file is not the whole
   capability when direct sources establish a broader user effect. Conversely,
   do not invent product ethos, platform doctrine, generalized infrastructure,
   or future operating modes that direct sources and the immediate or evident
   adjacent need do not support. Prefer neither the lower-power local path nor
   a platform automatically; record the supported proportional tradeoff and
   remaining uncertainty.
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
17. Make every genuine input gate continuation-first. Define the exact blocked
    subject set and descendant dependency closure, the independent safe-work
    frontier, work that may be prepared provisionally or across alternatives,
    authoritative effects that remain forbidden, and the revisit trigger. A
    pending fact, preference, or reserved action blocks only its mapped closure.
    Keep the Block `in-progress` or `completed-with-open-items` while independent
    work continues; do not claim `blocked` while a nonempty safe frontier exists.
    For supervised runs, require one bounded Sol Max resolution attempt before
    requesting user input. Only if it remains unresolved should the supervisor
    send the complete decision brief and open the maintained 20-minute response
    window; safe work and the remaining bounded 20-minute Sol Max attempts
    continue during that window. The final posture is a supported selection
    within delegated authority or a bounded safe deferral for an unavailable
    fact or reserved action—never a fabricated fact or unauthorized act.
18. Keep implementation progress in the active implementation thread. A tracker
    may require a bounded action handoff to a configured reviewer, supervisor,
    or executor, but it must not require routine status broadcasting to side
    conversations. In supervised runs, cross-thread sends use the supervision
    policy's exact action-routing gate; user-facing email uses only its
    maintained notification gates.
19. Make every operation-specific hold state its exact operation or Block scope,
    expiry event, successor posture, and default non-carry-forward. A satisfied
    hold remains historical evidence; it does not silently constrain a later
    operation or successor Block.

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
- If input genuinely remains necessary, does the tracker isolate its exact
  dependency cone and let every independent safe slice continue without false
  acceptance or provisional authority effects?
- Does the tracker-level mission frame keep subordinate process controls from
  changing the primary outcome, and does every temporary hold expire without
  inferred carry-forward?
- Does the target-product frame cite direct support for asserted product
  doctrine, distinguish the requested mechanism from the supported capability,
  and expose tradeoffs and uncertainty?
- For a consequential Block, does its local capability delta show the intended
  gain, possible loss, protected-capability effect, and architecture or
  operating-model effect without copying the global frame?
- Would the plan underreach by treating literal feature wording as the whole
  capability, or overreach by inventing a generalized platform or unsupported
  ethos? Either failure requires a narrower, source-backed rewrite.

If any answer is no, narrow the Block, reuse the owner, defer the adjacent work,
or create a later single-focused Block when that work is genuinely required.

## Amend or renumber safely

Read [references/amendment-and-renumbering.md](references/amendment-and-renumbering.md)
before editing an existing tracker. Preserve accepted status, commit and review
evidence, historical findings, and interpretable old block references. Apply
renumbering mechanically, then inspect every dependency and semantic
cross-reference. Do not mark newly introduced work complete merely because
adjacent implementation exists.

When implementation is already active and a learned fact invalidates the
program structure rather than one local implementation choice, also read
[references/active-program-revision.md](references/active-program-revision.md).
Use `scripts/program_revision.py` to build the exact predecessor/proposal map,
accepted-history proof, affected dependency closure, safe frontier, and resume
Block. A status edit, local implementation correction, or unsupported idea is
not a structural revision and must remain on its existing cheaper owner path.
The author produces proposal bytes and the packet; it cannot accept its own
work. The independently signed review and maintained supervision event decide
acceptance before the implementation range may advance to the new tracker.
Before building, require the supervision policy's immutable
`tracker-authoring` profile binding for the exact authoring target thread. The
binding must cite an independently accepted review of
`docs/software-factory-tracker-authoring-supervision-implementation-tracker.md`
as the bounded profile-design contract at its exact repository revision/root,
without claiming that tracker's separate Blocks are implemented, and resolve
the runtime watcher, base reviewer, reviewer, and optional fix-executor threads.
The packet and signed
review expose those exact profile and role identities. The
proposal must carry the exact active-program control section and append one
Program revision history row derived from the complete Block map, structure
root, affected closure, and resume Block. A later correction to a `revise` or
`rejected` proposal binds the predecessor review and resolves every finding;
changing only its revision ID is not a correction. The structural projection
also covers current control values, source-map and verification-matrix rows,
and tracker-wide Block/range/handoff prose, while excluding append-only history
rows from the self-root. At application, require the current single-parent
tracker-only HEAD whose parent is the packet target revision, recheck live
tracker bytes at the policy-write boundary, and return the same canonical next
action and resume state on identical retries at both owner steps.

An accepted amendment changes the plan, not the standing direct implementation
range. When the user authorized implementation of the tracker as a whole,
inserted prerequisite Blocks, splits, merges, and renumbering remain inside the
same full-tracker intent through the new terminal Block and observable outcome.
Record the old-to-new map, but never reinterpret the amendment as authorization
to implement only the newly inserted Blocks or to discard the previously
requested remainder. Only a newer exact direct-user instruction may contract
that range. Authoring Stop boundaries and authoring-review acceptance are
internal prerequisites to implementation, not outcome completion.

## Preserve replayable control convergence

For a tracker that can cross tasks, runs, groups, or internal Block Stops,
require one governing-outcome owner and one deterministic terminal-posture
reducer. Keep task, run, group, tracker, Block, transition, and outcome
identities separate. A handoff, acknowledgement, safe deferral, accepted
tracker, commit, or review is process state and cannot become outcome closure.

The demonstrated control-plane baseline is the content-minimized
`control_posture_replay_v1.json` fixture owned by `supervise-tracker-runs`.
It proves that an open transition, unavailable authority, safe deferral,
handoff/acknowledgement, current direct correction, same-task continuation, and
eventual observable completion converge without human scheduling. Authoring may
require equivalent replay coverage for a new control state, but it must not copy
private incident narrative into the tracker or infer that later adaptive
decision-control Blocks are already implemented.

## Record status and evidence

Read [references/evidence-and-status-rules.md](references/evidence-and-status-rules.md)
when the tracker includes accepted work, remediation, independent review,
currentness, or terminal proof. Tracker status is an implementation-planning
record, not a substitute for native product or domain authority.

## Verify before handoff

Run the read-only verifier:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/author-implementation-trackers/scripts/verify_tracker.py" \
  path/to/tracker.md --profile full
```

Use `--profile core` only as the documented compatibility path for an inherited
tracker whose established house style predates the current full sections,
including the target-product frame and per-Block capability-delta posture. It
checks the minimal inherited contract; it does not certify current full-profile
structure or product reasoning. Use `--json` when machine-readable diagnostics
are useful. The verifier checks structure and declared values mechanically;
substantive review must still test source support, underreach, tradeoffs, and
speculative over-architecture.

For an active structural revision, verify both tracker versions and the exact
packet in one invocation:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/author-implementation-trackers/scripts/verify_tracker.py" \
  path/to/proposed-tracker.md --profile full \
  --revision-packet path/to/program-revision.json \
  --previous-tracker path/to/current-tracker.md
```

Also run the repository's documentation checks, changed-test plan, formatting
checks, and link checks when applicable. Inspect the final diff for stale block
numbers, status drift, duplicated ownership, dependency cycles, unsupported
completion claims, and stop-boundary overlap.

Verify the canonical entry point too. When `docs/tracker.md` is itself the
detailed tracker, the normal verifier covers it. When it is a routing index,
mechanically prove that it has exactly one active program, every active or
required successor path exists, every recorded current hash matches exact file
bytes, program-qualified Block identities do not collide, the first eligible
Block agrees with detailed tracker status and dependencies, and every other
tracked implementation document has an explicit noncompeting disposition.

## Finish at the authoring boundary

If the user asked to write the tracker, commit only the owned, validated tracker
slice when repository policy permits. Report `docs/tracker.md`, the selected
detailed tracker path, program-qualified block range, material assumptions,
verifier results, and first eligible block.

Do not implement a block during tracker authoring unless the user separately
requests implementation. Hand implementation to `$implement-tracker-blocks`,
which rereads the selected block and executes it one bounded block at a time.
