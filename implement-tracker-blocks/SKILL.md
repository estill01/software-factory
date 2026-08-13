---
name: implement-tracker-blocks
description: Execute implementation-plan or roadmap tracker blocks faithfully, one bounded block at a time, audit each completed block before advancing, and preserve scoped Git checkpoints with regular pushes to an available configured remote. Use when the user attaches or references a tracker and asks to implement Block N, continue with the next block, implement a block range, or review whether the previous block was fully implemented.
---

# Implement Tracker Blocks

Turn a tracker reference plus a block number or range into an evidence-bound
implementation loop. Treat the tracker as the scope and completion contract,
while treating live repository instructions and authorities as controlling.

## Resolve the request

1. Resolve the exact referenced tracker and active repository.
2. Read applicable repository instructions before changing files.
3. Extract the requested block's dependencies, objective, required work,
   deliverables, acceptance criteria, stopping point, status rules, and required
   evidence.
4. Classify and freeze the direct requested range before the first Block. An
   unbounded request to implement `this tracker`, `the tracker`, the referenced
   functionality, or a bare invocation of this skill after a tracker was
   established means the complete current tracker through its terminal Block
   and observable outcome. Only an exact one-Block or numeric range request is
   bounded to that subset. If the user requested a range, preserve the
   tracker's dependency order. If the user requested one Block, do not silently
   advance to another.
5. Treat the tracker path and requested block number or range as reusable
   inputs. Never bake a demonstrated repository path or block number into the
   workflow.

Persist that classification through the supervision owner's
`implementation-range-bind`; never use a caller-selected binding JSON file.
The canonical policy-history chain anchors one immutable genesis, direct source
record/hash, the exact request bytes whose SHA-256 matches that source,
owner-resolved tracker path/hash, and append-only amendment head.
Reuse `implementation-range-gate` at every Block transition and before every
final answer. Never recreate or replace the binding to obtain a smaller range.
A full-tracker binding dynamically includes prerequisite Blocks inserted or
renumbered by an accepted tracker amendment. It may be narrowed only by a newer
direct-user source already ingested as a hash-chained canonical owner event
with independently verified task/item provenance; the range helper may resolve
that event but cannot create it. A helper-validated delegated-authority event
and current receipt preserve the original direct-user source through the
system's target-action route and are consumed as that exact source, without
asking the user to repeat it. A caller string, tracker edit, routed supervisor
packet, unbound `codex_delegation`,
task/run/group boundary, handoff, reviewer statement, commit, push, or process
record cannot contract it.

If the user explicitly asks to monitor, babysit, supervise, periodically audit,
or prevent drift in the implementation run, use `$supervise-tracker-runs` as a
separate optional companion. Do not start supervision merely because a tracker
is present, and do not merge supervisor duties into this implementation loop.

## Bind observable outcome closure

Before the first Block, derive one compact outcome-closure contract from the
current direct goal, tracker, and repository instructions. Keep it in the active
execution brief unless the tracker requires a durable record. It must identify:

- the primary operator-visible outcome and exact completion condition;
- every ordinary effect class needed to produce it, such as authoritative
  writes, generated builds, publication artifacts, installation, or downstream
  reconciliation;
- the current identity and currentness basis for each required deliverable;
- the genuinely reserved, external, or expressly excluded work that may remain
  open; and
- the hard authority, safety, release, and destructive-action boundaries.

Reconcile each Block against this contract. A Block may stop before producing a
required final deliverable only when a later named Block owns that effect. If a
tracker's terminal boundary omits, excludes, or indefinitely defers an ordinary
effect necessary for the user's outcome, the tracker is defective: preserve
history, amend or reopen only the narrow owning slice, and continue. Do not use
tracker completion as evidence that the goal completed when the two diverge.

For every required deliverable, classify the live result as `created-current`,
`reused-current`, `stale`, `missing`, or `open`, and bind that classification to
its exact commit, authority revision/root, source hashes, and build or receipt
identity as applicable. Before terminal completion, independently rehydrate or
inspect the actual operator-visible deliverables and reconcile the complete
expected effect set against actual effects. Passing tests, audits, schemas,
hashes, populated records, reviewer counts, commits, pushes, or a terminal
ledger are process evidence; none substitutes for a current deliverable.

An unjustified early return is a **critical control failure**. In particular,
`FM-UNAUTHORIZED-EARLY-RETURN` means the implementation owner returned while a
directly requested Block, ordinary authorized effect, or current observable
outcome remained. Its common root form is unauthorized requested-range
contraction followed by false terminalization at an internal Block or
procedural boundary. Routed-authority precedence may contribute to the failure,
but cannot redefine the direct requested outcome.

`completed-with-open-items` is terminal only when every retained item is
compatible with the primary outcome and is genuinely reserved, external,
optional, or expressly excluded. It may not hide ordinary authorized work that
the tracker was meant to perform. Report implementation completion and outcome
completion separately. Describe a branch or pull request as ready to merge only
when both are current, every required operator-visible artifact is current, and
the remaining open items are compatible with the stated outcome.

## Activate one block economically

Before editing, form one compact execution brief from the live Block: governing
outcome, existing owner, exact missing delta, reusable accepted evidence,
dependency/currentness check, expected focused and mapped proof, review order,
resource/widening posture, and stop boundary. Do not create a new artifact for
the brief unless the tracker requires it. For every focused or audit test
command, freeze and reuse one repository-owned invocation envelope. The envelope
is not complete until repository-owned scripts, configuration, and instructions
resolve the exact maintained runner command chain, every launcher and executable
actually invoked, the repository-derived working directory and project or
workspace binding, the configured runtime and any required import or module
binding, the exact selection, and the intentional Git environment or its
verified absence before first execution. Prefer the maintained repository-native
command or runner, and bind an import path only when that repository requires it.
A proxy check is not an envelope check: proving Vitest while omitting the `npm`
launcher (or an analogous outer command), or guessing a workspace root instead
of deriving it from repository ownership, fails preflight. After correcting a
setup failure, retain the complete corrected command chain and envelope in the
active brief and exact audit handoff, reuse it on the next applicable first
invocation, and rerun only proof invalidated by the correction. After any other
concrete path failure is corrected, retain the corrected command, owner, or
writer path in the brief and first reuse it on the next applicable invocation.

When the tracker declares a `Target-product capability delta`, inspect its
posture before selecting the implementation path. Whether the tracker uses the
current full profile or an inherited format, read
[references/product-capability-review.md](references/product-capability-review.md)
and run its bounded review only when the Block is `consequential` or live
evidence exposes a concrete drift trigger: changed feature behavior, canonical
representation, architecture strategy, operating model, protected capability,
owner bypass, or a delta that conflicts with direct product sources. A
`routine` or `not-applicable` Block with no such trigger keeps the economical
normal path; do not repeat product-strategy analysis merely because the frame
exists.

For a triggered review, hash and read the tracker-level frame once for that
Block and reuse it in the execution brief. Compare the smallest local path, the
smallest bounded-general path supported by current or evident adjacent needs,
and the available architectural owner. Select the lowest-complexity path that
fully supplies the source-backed capability while preserving canonical owners
and protected capabilities—not automatically the local path and never the most
general architecture by default. Widen only for one named missing product fact
or affected owner. Bind the selected capability gain or preservation,
rejected alternatives, protected-capability effects, and accepted tradeoffs to
completion evidence at the frozen candidate revision.

The maintained semantic boundary for adaptive implementation decisions is
[references/adaptive-decision-control.md](references/adaptive-decision-control.md).
It defines the exact no-change, inline-correction, bounded-candidate, and
structural-amendment dispositions, their shared evidence record, and the
authority/currentness invariants used by later implementation Blocks. The
reference is a contract, not an activated runtime controller: do not create a
candidate lane, mutate a tracker, change supervision policy, or add a model or
review cycle merely because the contract exists.

## Correct a bad implementation path inline

Apply this loop inside the active Block whenever current source, repository,
test, or observable-outcome evidence exposes a materially bad implementation
decision. This is the normal adaptive path; it is part of ordinary execution,
not a new task, authoring pass, supervisor lifecycle, or approval gate.

1. Compute the Block 4 decision fingerprint and currentness root from the
   already-loaded execution brief. If both equal an accepted unchanged or
   resolved decision, return from this check to the next ordinary implementation
   action with zero model, reviewer, candidate, or authoring work. Never convert
   `continue-unchanged` into a user-facing return, lifecycle stop, or skipped
   remainder of the requested Block range.
2. Require one concrete trigger: wrong/circumvented owner, lower-power
   substitution, unnecessary abstraction, repeated blind retry, overbroad or
   invalid validation, scope widening, or protected-capability regression. A
   style preference, transient failure, local difficulty, optional refactor,
   or unproven reuse remains `continue-unchanged`.
3. Before changing the path, freeze the smallest safe checkpoint and classify
   each affected reference as reusable valid work or stale proof. Preserve
   coherent code, tests, artifacts, commits, accepted evidence, and unrelated
   dirty-tree state. Stop only the causal bad process or write owner.
4. Compare exactly the smallest local correction, the smallest
   bounded-general path supported by a named current or accepted near-term
   consumer, and the available architectural owner. Compare capability,
   protected capability, correctness, maintainability, performance,
   compatibility, reversibility, implementation/review cost, and writable
   scope without an opaque score. Select the lowest-complexity path that
   supplies the complete source-backed capability. Record why the bad shortcut
   and any unsupported generalized layer lost.
5. Select `correct-inline` only while the original objective, dependencies,
   acceptance, and Stop remain unchanged and the existing authoritative owner
   can make the correction. If implementation behavior is required to choose
   safely, route to `compare-candidate`; if the Block contract or later graph
   must change, package `amend-structure`. Do not use either escalation merely
   because the correction is difficult.
6. Implement through the selected existing owner. Run the smallest focused
   proof first, replace only proof invalidated by the correction, populate the
   Block 4 common decision record through `selected`, `implementing`,
   `validated`, and `closed`, and keep the same fingerprint for process-only
   currentness refreshes. Store it in the existing implementation/supervision
   evidence owner; do not create a correction registry or second ledger.
7. Re-run the affected capability/protected-capability check, audit the active
   Block, and immediately continue its remaining dependency-safe work. No
   tracker edit, authoring thread, separate supervision lifecycle, human prompt,
   or manual Resume is eligible for an ordinary inline correction. The Block's
   Stop remains the mutation/audit boundary and, for a multi-Block/full-tracker
   request, remains an internal checkpoint under the range gate.

Equivalent fingerprints are deduplicated. A rejected or selected path is not
reconsidered without new concrete adjudicating evidence. Read the capability
frame and affected owner once, permit at most one named widening fact, and run
focused proof before any mapped suite. If a valid incumbent remains the
lowest-complexity complete path, retain it without manufacturing a correction.

## Compare one bounded candidate when behavior must decide

Use `compare-candidate` only after the inline loop proves that current source
evidence cannot decide a material implementation choice and that an isolated
implementation will supply the missing evidence. Read
[references/bounded-candidate-lane.md](references/bounded-candidate-lane.md)
and execute its exact record and lifecycle contract.

1. Record the concrete hypothesis and affected capability, the uncertainty and
   avoidable rework, the required implementation evidence, duplicate build and
   review cost, isolation risk, and reversibility. Open no lane unless the
   named expected decision benefit exceeds its bounded cost and read-only
   evidence cannot decide. Style, novelty, optional reuse, or a merely
   different implementation is not positive decision value.
2. Freeze the coherent incumbent revision and content root before candidate
   work. It remains the sole production authority. Declare the isolated
   writable scope and every shared-resource exclusion; reject overlap with the
   incumbent writer, canonical state, deployment, release, credentials, or
   another candidate. Dependency-safe incumbent work may continue only when it
   cannot change the comparison basis.
3. Open exactly one branch, worktree, temporary repository, or equivalent lane
   for one hypothesis. Bind the normal implementation owner, capability and
   protected-capability contract, expected observable effect, file/change,
   command, elapsed-time, and review ceilings, early failure Stops, success
   criteria, and cleanup posture. The lane has no publish, production, cutover,
   tracker, policy, or second-owner authority.
4. Implement only the candidate delta through the normal target owner. Stop at
   the first exceeded ceiling, unsafe isolation, incumbent-basis drift,
   hypothesis falsification, focused failure, or protected-capability
   regression. Retain useful evidence as non-authoritative history; never make
   a failed lane production-capable.
5. Run focused candidate validation first. Only after the candidate is coherent
   and frozen may mapped comparison read both exact roots. Compare the current
   observable outcome, implementation cost, maintenance cost, reversibility,
   compatibility, and protected-capability result without a novelty bonus or
   opaque aggregate score.
6. Give the raw roots, outcomes, costs, and protected results—without an
   implementer preference—to a distinct automated reviewer. It returns exactly
   `candidate-better`, `incumbent-better`, `non-inferior-no-benefit`, or
   `inconclusive`. Local tests alone, newer code, or implementer rationale
   cannot authorize a winning disposition.
7. For `candidate-better`, freeze one non-mutating cutover handoff for the
   normal target owner and Block 9; do not cut over here. For every other
   disposition, retire the candidate as losing or inconclusive, preserve only
   useful evidence, and keep the incumbent authoritative. Never retain two
   live implementations or force adoption.
8. Record the Block 4 candidate fields and immutable stage/currentness chain.
   Deduplicate the decision fingerprint, candidate root, and review root so an
   unchanged trigger creates no new lane or reviewer cycle. Continue the
   current requested tracker range automatically after the Block Stop.

The candidate mechanism is selective evidence gathering, not routine
dependency parallelism and not a generalized experiment service. It does not
edit the tracker, change adaptive policy, cut over a winner, publish a branch,
or ask a human to choose an ordinary engineering tradeoff.

For a materially expensive read-only proof or audit with a separate reporter or
helper, cheaply preflight the maintained reporting interface and its invocation
binding before starting the expensive computation. If valid proof output
already exists and only reporting fails, freeze and reuse that output and rerun
only reporting; never rerun the producer solely for a reporting failure.

Preserve authority provenance exactly. A `codex_delegation` packet is a
transport, not a new authority source. An unbound packet cannot authorize work;
a helper-validated delegated-authority event and current receipt carry the
exact independently verified originating direct-user source and must be acted
on within that scope without a same-thread repetition or manual Resume. Before
classifying `reserved-authority`, cite the exact current controlling
user, system, repository, or tracker source and prove that it still applies.
Retire a satisfied operation- or Block-scoped containment at its stated expiry;
keep it only as history, with no inferred carry-forward across a Block,
compaction, or later operation. A frozen checkpoint normally fixes its
predecessor for proof, not every successor revision, and `do not rerun X`
constrains exact X rather than a later operation absent an exact current source.
If carried process language disables an ordinary means needed for the requested
outcome or makes the mission self-defeating, challenge the scope and provenance
before recording a decision. Tests, audits, hashes, monitoring, and process
preservation support proof; they never substitute for the requested substantive
outcome.

Preflight the current Block and its next eligible dependent Block for an
actually non-delegable decision. Tracker wording that assigns `responsible
human adoption` or requests confirmation is not by itself controlling proof of
necessity. Do not stop for an ordinary non-reserved choice Codex can resolve
from the tracker, current authorities, the user's standing implementation
imperative, and bounded judgment. In particular, apply a single eligible,
independently reviewed recommendation when its material trade-offs are resolved
by current objectives; record delegated Codex application accurately rather
than fabricating inventor authorship. When new user facts, unresolved personal
preference, counsel-reserved treatment, credentials/budget, destructive
ambiguity, external communication/release, or another authority boundary is
genuinely required, surface it as soon as its complete
decision packet is available—normally during the predecessor or at Block start.
State why it is non-delegable, the exact alternatives and recommended rationale,
the deadline/first dependent Block, and the scope it alone blocks. Continue all
safe, independent, pre-decision work; do not wait until the stop boundary to
give the first warning.

When input genuinely remains unresolved, treat it as a dependency cut rather
than a full-run stop:

1. Freeze the exact decision packet and classify it as delegable judgment,
   unresolved human preference, missing fact, or reserved authority.
2. Identify the smallest blocked subject set and compute its exact descendant
   closure through the tracker's existing dependencies.
3. Compute the maximal safe-work frontier. Continue common work shared by all
   alternatives, unaffected subjects and Blocks, reversible preparation, tests,
   and evidence that do not consume the unresolved answer.
4. Mark the bounded decision or subjects `waiting-for-input`; keep the Block
   `in-progress` or `completed-with-open-items`. Never present provisional work,
   an excluded subject set, or a branch alternative as accepted authority.
5. Recompute the frontier when the decision, dependencies, or currentness change.
   Late input selectively reopens only mapped descendants and must not duplicate
   already valid work.

For a supervised run, start one bounded Sol Max resolution attempt before
requesting user input. Only if that attempt remains unresolved should the
supervisor send the complete decision brief and open the maintained 20-minute
response window. Keep working during that window and consume the remaining
bounded Sol Max attempts, each at most 20 minutes, without idle waits. A
delegable choice or unresolved preference ends in a supported selection and
exact handoff. A missing fact or reserved action ends in a safe bounded deferral,
not an invented fact or unauthorized operation. Apply the handoff at the next
safe boundary and preserve its trade-offs, exclusions, and downstream
obligations.

Before ending any supervised turn around an open decision, call the maintained
`decision-gate` for that exact decision. If it returns
`blocking_permitted=false`, a terminal `blocked` response is forbidden even
when the current safe frontier is empty: report the bounded subject as
`waiting-for-input`, keep the Block and Goal `in-progress`, and yield only as an
automated-resolution continuation point. Do not ask the user to press a Resume
control. The supervisor owns the timed attempts and exact handoff; consume that
handoff automatically at the next turn boundary. Only
`blocking_permitted=true` may support a terminal blocked result, and that state
is limited to an exact safely deferred missing fact or reserved authority with
no safe frontier. If a prior UI card still says `Goal blocked` after a handoff,
state that the card is stale and continue; do not require or wait for a manual
resume.

Before adopting any terminal target posture, call the supervision owner's
`control-posture-gate` when that owner is configured. Treat its governing
outcome, tracker/program, execution-run, Codex-task, supervision-group, and
Block identities as distinct. Its bounded joined-ledger result is the sole
required target posture; decision, transition, and lifecycle gates remain local
diagnostics. If the canonical posture is `in-progress`, continue its exact safe
action even when a subordinate task, handoff, decision, Block, test, review, or
UI card appears terminal.

When the requested implementation must move to a distinct successor task,
treat that as an execution-topology transition, not as completion of the
requested scope. Keep the source run `in-progress` and preserve one exact
append-only `successor-transition-record` through `required`,
`successor-created`, `successor-bound`, `handoff-sent`,
`target-acknowledged`, and `work-started`. A handoff packet, accepted tracker,
or bound successor is not enough: call `successor-transition-gate` and end the
source run only when `source_stop_permitted=true`, which requires current
evidence that the successor began the first eligible Block. If task creation
requires direct authority unavailable to the current task, keep the transition
open and expose that exact authority boundary; do not invent a task ID, treat a
routed supervisor packet as direct user authority, claim completion, or turn
the handoff into an ordinary user scheduling request.

Use `same-task-new-run` by default. Select `distinct-task/direct-request` only
when the exact request bytes hash to the canonical direct-user governing source
and one affirmative clause explicitly requires a distinct task. Reject
negation, same/current-task contrast, conditional, optional, or contradictory
language. Select
`distinct-task/technical-isolation` only from a pre-existing, independently
verified, hash-chained `successor-topology-decision` owner event; never mint the
rationale from CLI prose. New `legacy-linear` transitions are forbidden. When
the canonical implementation range exists, the transition genesis must match
its tracker hash, canonical range-history source record, complete requested
Block set, first dependency-safe Block, and bound mission root. Append through
the canonical owner-relative,
no-follow/currentness-checked ledger writer.

For a tracker run that spans skill maintenance, reread this skill at each Block
transition when its live file hash has changed or a maintained skill-refresh
notice was received. Do not continue from a cached turn-start copy across that
boundary.

Choose the smallest reliable causal path. Reuse current manifests, indexes,
snapshots, exact source copies, prior accepted reviews, and configured runtimes.
Use a cheap exact revision/root/currentness check before a deep scan or
rehydration. Batch coherent work; do not repeat the pipeline per item when one
bounded owner pass suffices. On repeated failure, diagnose or narrow the
implicated path instead of blindly retrying, changing runtimes, or widening the
suite.

## Implement one block

1. Inspect the live tree before planning. Reconcile the tracker against current
   code, configuration, tests, generated artifacts, and Git state.
2. Preserve completed, staged, untracked, and in-flight user work. Keep the
   change set bounded to the block and avoid unrelated cleanup.
3. Classify already-present work as current proof, pending proof, pending
   promotion, or an actual delta when the tracker uses such distinctions. Do
   not recreate working capability merely because it appears in a checklist.
4. Implement every required delta through the narrowest authoritative layer.
   Do not absorb later blocks or invent adjacent infrastructure.
   When product-capability review was triggered, implement the selected
   architecture level and preserve its rejected alternatives and tradeoffs;
   passing local tests never excuses a supported capability regression,
   canonical-owner bypass, lower-power substitution, lost composability, or
   speculative generalization.
5. Run focused validation during the edit loop. Complete known in-scope changes
   and any review allowed to mutate the candidate before expensive final mapped
   validation when the workflow permits it.
6. Freeze the coherent candidate content root, then run the mapped integration
   validation appropriate to that slice and verify the root did not change.
   Create the scoped checkpoint commit only after the candidate is validated.
   If the candidate changes during or after validation, retain the run as
   diagnostic and rerun only affected proof against the successor.
7. Obtain a distinct reviewer when the tracker or repository requires
   independent review. Keep review read-only until findings are returned and
   bind it to the exact candidate revision.
8. Update the tracker only with evidence that is current. Use its prescribed
   status and completion-evidence format.
9. Honor the Block's explicit Stop as a mutation/audit boundary. For an exact
   one-Block request it is also the requested return boundary. For a multi-Block
   or full-tracker request it is an internal checkpoint only: commit, push,
   audit, update truthful evidence, run the range gate, and immediately execute
   its dependency-safe `next_action`.

Keep routine implementation, validation, audit, checkpoint, and completion
evidence in the active implementation thread. Send a cross-thread packet only
when another configured role owns an exact required action; do not broadcast
progress to unrelated chats or side conversations. In a supervised run, call
the supervision helper's `thread-route-gate` with the exact recipient, purpose,
source record, and required action before sending; do not send unless it returns
`send_allowed=true`. User-facing email remains owned by the supervisor's
maintained gates.

Treat a blocked implementation as exceptional. Claim `blocked` only when the
exact non-delegable input is still absent, proceeding would cross a declared
authority or safety boundary, the first attempt remained unresolved, the
complete human-input packet has been exposed, and all safe in-scope work has
been exhausted. Report the earliest point at which the blocker was foreseeable
and when it became decision-ready. Do not convert
a preferred confirmation, generic confidence request, unresolved but bounded
engineering choice, or work that can proceed independently into a full-run
stop. If the requested response would only repeat the system's recommended
candidate and rationale, proceed under standing authorization instead.
An empty current action queue is not proof of a blocker: first compute the
dependency-independent safe frontier across the user's requested Block range.
If it is nonempty, continuing it is mandatory. For a one-Block request, remain
inside that Block; for a requested range, a later dependency-independent slice
may proceed only with the unresolved subjects expressly excluded and without
marking the earlier Block accepted.

In a supervised run, the conditions above are necessary but not sufficient:
the exact `decision-gate` must also return `blocking_permitted=true`. An active
attempt, response window, supported selection, pending handoff, or ordinary
human-preference resolution keeps the Goal `in-progress` and may never be
reported as terminally blocked.

## Apply a live supervision correction

When a current supervisor or the user identifies a supported execution-economy
defect, correct the same active tracker run; do not merely create guidance for a
future tracker or wait for the next Block.

1. Contain only the exact owned wasteful action. Stop its exact process tree or
   decline its next repeated unit when safe; do not interrupt unrelated work or
   cross an irreversible boundary merely to react quickly.
2. Preserve accepted checkpoints and still-valid focused evidence. Mark an
   interrupted or pre-correction run accurately as diagnostic, aborted,
   superseded, or stale rather than claiming it passed for the successor.
3. Identify the smallest current owner of recurrence. Amend the active execution
   brief first; amend the current tracker, changed-test mapping, runner/profile,
   or implementation only when that owner concretely caused or would repeat the
   defect in this run. Do not add a parallel policy or remediation subsystem.
4. Recompute affected scope and validation after the correction. If the producer
   already yielded a valid artifact or commit, freeze and reuse it; repair only
   invalidated currentness, ordering, serialization, declared-no-op, or transfer
   proof. Rerun that producer only when currentness or content actually
   invalidates its output, never for generic confidence or because a reusable
   skill update is pending.
5. Commit the coherent correction under the ordinary checkpoint contract when
   files changed, obtain any required exact-revision review, and show the
   supervisor later evidence that the active cost stopped and the Block resumed
   from the last valid boundary.
6. Re-read a reviewed reusable-skill correction when notified and apply it to
   the remaining current run immediately at the next safe action boundary. Do
   not retroactively invalidate valid work or reopen accepted Blocks without a
   mapped dependency.

Reusable skill maintenance prevents later recurrence; it never discharges the
current run's correction, evidence, or incident-closure obligations.

## Audit before advancing

After implementation, review the block against its original contract:

- Was every required item faithfully and fully implemented?
- Does every completion claim resolve to live implementation and current proof?
- Were negative cases, compatibility, migration, dirty-tree preservation,
  real-input proof, and independent review handled where required?
- For a consequential Block or concrete drift trigger, does current evidence
  show the capability added or preserved, the selected architecture level,
  protected-capability effects, and accepted tradeoffs? For a routine Block,
  was the bounded normal path retained without invented product analysis?
- Did the implementation cross the stopping point or leave an unacknowledged
  acceptance gap?

Correct only material defects and high-impact opportunities that remain inside
the block. If the implementation already satisfies the contract, make no
speculative changes. Rerun affected validation after any correction.

For a rejected candidate, maintain a compact closure matrix: each finding,
governing invariant, exact corrective delta, focused regression, affected mapped
proof, and fresh exact-revision review. Close every row or preserve it as an
explicit blocker. Do not rerun unrelated suites, rescan unchanged authorities,
or reopen accepted work without a mapped dependency. Once the corrected Block
passes its declared proof and independent audit, stop remediation.

Do not mark a block complete when required proof is unavailable. Use the
tracker's accurate intermediate status and report the exact gap.

## Preserve Git checkpoints

Treat bounded commits and remote durability as part of the implementation
loop unless the user or repository instructions explicitly prohibit them.

1. Before editing, inspect the current branch, worktree/index state, upstream,
   and configured remotes. Treat unrelated staged, unstaged, and untracked work
   as user-owned.
2. Create a narrowly scoped commit after each coherent validated implementation
   candidate and before exact-commit independent review. For a long block,
   also checkpoint each self-contained slice that passes its focused tests
   before beginning another material slice; label it accurately as in progress
   and do not claim block acceptance.
3. Do not let more than one completed block or one material audited remediation
   accumulate without a commit. If review rejects a candidate, preserve that
   commit and append a new remediation commit; never amend or rewrite reviewed
   history to manufacture acceptance.
4. Commit accepted tracker status and completion evidence at the next coherent
   boundary, separately from implementation when that keeps scope and audit
   history clearer.
5. Stage only the owned block slice and verify the staged diff. Never sweep in
   unrelated work, commit known failing or unexplained state, or interrupt a
   running test or review merely to create a checkpoint.
6. After each coherent checkpoint commit, push the current branch when an
   already configured remote path is unambiguous and repository policy permits
   it. Prefer the existing upstream. If no upstream exists and exactly one safe
   configured remote exists, use a non-force `git push -u <remote> HEAD`.
7. Never add or rewrite a remote, guess among multiple remotes, force-push,
   rewrite history, bypass protected-branch policy, merge, release, or open a
   pull request merely to satisfy this checkpoint rule. If the remote is
   absent, authentication fails, or policy forbids the push, preserve the local
   commit and report the exact blocker; continue locally when otherwise safe.
8. Record each checkpoint commit SHA and push status in the running evidence or
   handoff so the next block starts from an exact durable revision.

## Continue a range

For each subsequent block in the requested range:

1. confirm the prior block passed the audit;
2. reread the next block's contract and live dependencies;
3. implement, validate, independently review where required, and update
   evidence;
4. audit it before advancing again.

Run the persistent gate after each accepted Block. A nonterminal exit status or
`final_response_permitted=false` is an instruction to execute `next_action`
now. It is not a blocker, a request for human scheduling, a reason to pause, or
content for a terminal response. A routed `stop here` can constrain the routed
operation or reviewer but cannot cancel a standing direct implementation
range. Commit, push, review, handoff, task, run, group, and Block Stops are
process evidence only and never imply requested-outcome completion.

The installed control-plane baseline has one replay-certified posture owner.
When successor, decision, lifecycle, valid-stop, or observable-completion state
interacts, resolve it through `control-posture-gate`; do not combine local gate
answers into a second terminal decision. The maintained
`control_posture_replay_v1.json` sequence and finite state matrix demonstrate
that partial handoff remains open, current direct correction resumes the same
task, invalid terminal claims fail into actionable reconciliation, and current
observable completion alone may close the outcome. Every supported result sets
`manual_resume_required=false` and `human_input_required=false`; ordinary
continuation executes immediately. This is a control-plane guarantee, not a
claim that the adaptive implementation paths in later tracker Blocks already
exist.

Immediately before any final response or terminal posture, independently reread
the exact direct requested Block range and current tracker. Reconcile them
against the current accepted Blocks, remaining requested Blocks,
dependency-safe frontier, required producer transitions, and safe coordination
frontier. A missing or unavailable optional supervision binding, helper, or gate
does not relax this local evidence-bound reconciliation. While requested work, a
required producer transition, or a safe coordination frontier remains, final
return is forbidden: continue automatically within the existing authority and
do not ask the user to press Resume.

This local reconciliation never fabricates supervision authority, creates a
parallel ledger, narrows the exact direct scope, or authorizes overlapping
producer writes. When supervision is available, its maintained gates remain an
additional constraint and its single-writer ownership remains controlling.

Immediately before any final response, rerun the same canonical gate. It
rehydrates the policy-pinned tracker, requested and accepted Block sets, policy
and event heads, ordinary effects, and observable outcome through the governing
control-posture reducer. Caller booleans, paths, arbitrary roots, or prose
claims are not terminal evidence. A final response is forbidden while any
requested Block or ordinary effect remains, the observable outcome is not
current, or the supervision control posture remains nonterminal for the
governing outcome.

```bash
python3 <supervision-log-helper> implementation-range-gate \
  --target-thread <governing-outcome-owner> \
  --response-kind <block-boundary|outcome-terminal>
```

On first use call `implementation-range-admit` with the tracker, exact request
text, and exact canonical direct-user source record/hash. This includes a
validated delegated direct-user source transported from another thread after
its canonical review, ingestion, and receipt. Use
`implementation-range-amend` after an accepted tracker revision; the frozen
full-range intent persists automatically. A contraction additionally requires
an independently reviewed canonical `implementation-range-authority-receipt`
resolved from that pre-existing owner event. The receipt command cannot accept
source, hash, reviewer, or evidence claims directly.
Changing the pinned tracker path, Block-number set, or status-independent
structural root also requires one pre-existing canonical owner event that binds
the old/new paths, content and structural roots, complete Block sets,
renumbering map, and independent authoring acceptance. The structural root
includes dependencies, scope, acceptance, Stop, and the remaining Block
contract while excluding runtime status and completion-evidence content.
Ordinary status/evidence updates may preserve the same path, Block set, and
structural root without such an event.
Policy history must remain version-contiguous, and the event ledger must match
its canonical self-hashed head anchor. Reject truncation, re-rooting, stale
suffixes, symlink/path substitution, or a detached owner before using range,
transition, or terminal posture. Validate both against the separate append-only
owner-root history; a rewritten mutable anchor does not confer currentness.
The owner-root chain is HMAC-bound by a per-target key outside the target
directory; an authenticated external sequence/head pins its latest state, and
key existence makes enforcement non-downgradeable. After a
transition genesis, preserve its frozen range identity while checking that the
current range history still contains it with the same structural root,
requested set, and mission; status/evidence-only amendments must not trap the
transition.
The terminal lifecycle writer calls the same owner and rejects completion while
the governing range is nonterminal.

The only exception to whole-Block sequential acceptance is a declared
continuation slice around a bounded unresolved input. It must have no dependency
on the unresolved answer, preserve the earlier Block's non-accepted posture,
forbid dependent promotion/freeze/release, and record exact exclusions and the
rejoin condition. This is dependency-respecting continuation, not silent Block
skipping.

Only after the persistent range and terminal-evidence gate permits a final
response, end with a concise outcome: completed blocks, material files changed,
validation and review evidence, preserved open items, and the next eligible
block. Do not release, merge, open a pull request, or perform destructive
cleanup unless the user separately authorizes it or the repository's ordinary
implementation workflow explicitly requires it.
