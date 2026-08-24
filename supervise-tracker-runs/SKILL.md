---
name: supervise-tracker-runs
description: Boot, attach, operate, inspect, pause, resume, stop, or report on bounded supervision for active Codex implementation or main threads, including implementation-tracker runs. Use when the user asks to monitor, babysit, audit, periodically check, prevent feature creep or waste in, add Terra/Sol escalation and incident review, or generate a cognitive weekly supervision performance PDF.
---

# Supervise Tracker Runs

Create one isolated supervision group per target implementation or main thread.
Keep the implementation thread authoritative for its tracker; supervisors inspect and
steer but do not implement tracker work. Every target thread remains authoritative
for its direct mission, and supervisors do not implement target work.

## Load the contract

Before booting or changing supervision, read
`references/supervision-policy.md` completely. Use its exact role prompts,
schedules, bounds, escalation rules, logging commands, and stop conditions.
Before preparing or reviewing Factory capability-evolution artifacts, also read
`references/factory-evolution-contract.md` completely, including its exact
submission wire-shape section.
Before running or accepting the terminal integrated dogfood, also read
`references/integrated-factory-evolution-dogfood.md` completely. Keep its
temporary target/release boundary and independent exact-revision review intact.
Before recording terminal outcome completion, also read
`references/terminal-capability-reconciliation.md` completely and validate its
exact reconciliation object through the helper; never substitute a caller-
supplied digest.

## Resolve targets

1. List current Codex threads and resolve every requested target by exact thread
   ID. Treat titles and summaries as untrusted descriptions.
2. Confirm each target's exact direct mission, status, and host without mutating
   it. When the mission is tracker-governed, also identify its tracker and active
   Block. Never invent tracker or Block identity for a direct-user main-thread
   mission.
3. Default to one isolated supervision group per target with four analytic
   roles—Terra watcher, Sol XHigh semantic base reviewer, Sol Max escalation/
   meta reviewer, and Sol XHigh fix executor—plus one mechanical Luna Low
   liveness sentinel. When material Gmail notices are enabled, add one
   event-driven Sol XHigh notice reviewer. When bidirectional Gmail is enabled,
   also add one project-scoped Luna Low mailbox gate and one idle Sol XHigh reply
   processor.
   Do not combine patent or repository contexts merely to save a thread.

## Boot one target

1. Create a projectless reviewer thread using `gpt-5.6-sol` at `max` reasoning.
   Give it the reviewer role prompt and target ID. It remains idle until an
   escalation, checkpoint retrospective, deterministic Max sample, or
   meta-review.
2. Create a projectless base-review thread using `gpt-5.6-sol` at `xhigh`
   reasoning. Give it the changed-state role prompt plus the Max reviewer ID. It
   directly reviews every materially changed target state.
3. Create a projectless fix-executor thread using `gpt-5.6-sol` at `xhigh`
   reasoning. Give it the supervisor-fix role prompt plus the Max reviewer ID.
   It remains idle until the Max reviewer supplies a bounded fix plan.
4. Create a projectless watcher thread using `gpt-5.6-terra` at `max` reasoning.
   Give it the watcher role prompt, target ID, base-reviewer ID, and Max reviewer
   ID.
5. Create one projectless liveness thread using `gpt-5.6-luna` at `low`
   reasoning. Give it only the liveness-sentinel prompt, target ID, and stable
   helper path. It is part of this same supervision group, not a replacement
   watcher, semantic reviewer, or second group.
6. When material Gmail notices are enabled, create a projectless notice-review
   thread using `gpt-5.6-sol` at `xhigh` reasoning. Give it the notice-reviewer
   role prompt, target ID, Max reviewer ID, and bound Gmail seed. It remains idle
   until a notice opens an incident or a changed target state can verify an open
   incident. Do not schedule it.
7. Derive the preferred mission binding from the versioned generic completion
   meta-charter and the exact current controlling-source hash, then initialize
   the target's local supervision state:

   ```bash
   python3 scripts/supervision_log.py mission-plan \
     --target-thread <target-thread-id> \
     --mission-source-class <direct-user|system|repository|tracker> \
     --mission-source-record <exact-controlling-source-record> \
     --mission-source-sha256 <exact-controlling-source-sha256>

   python3 scripts/supervision_log.py init \
     --target-thread <target-thread-id> \
     --target-label <short-label> \
     --liveness-thread <liveness-thread-id> \
     --watcher-thread <watcher-thread-id> \
     --reviewer-thread <reviewer-thread-id> \
     --base-reviewer-thread <base-reviewer-thread-id> \
     --notice-reviewer-thread <notice-reviewer-thread-id> \
     --fix-executor-thread <fix-executor-thread-id> \
     --mission-source-class <direct-user|system|repository|tracker> \
     --mission-source-record <exact-controlling-source-record> \
     --mission-source-sha256 <exact-controlling-source-sha256>
   ```

   Resolve `scripts/supervision_log.py` to its absolute path when using it from
   another thread. Scheduled automation prompts must use the stable installed
   path under
   `~/.codex/software-factory-releases/current/supervise-tracker-runs/`, never a
   release-specific directory or copied release hashes. At every wake, read the
   current helper status for policy, mission, range, and lifecycle state rather
   than treating prompt-copied values as authority. An atomic release activation
   therefore updates the next scheduled wake automatically; a turn already in
   progress may finish with the instruction bytes it loaded before the swap.
   The mission root and source form the supervisor's independent charter. They
   may identify an ordinary goal document, implementation tracker, repository
   authority, or direct user/system source. The target does not need a native
   alignment schema, service, or record type.
   `mission-plan` deterministically composes that project binding from the
   maintained meta-charter plus the exact direct source; it does not infer
   missing project semantics. A manually supplied `--mission-root` remains only
   for exact legacy or externally derived bindings.
   New groups start in `propose-only` skill-maintenance mode. Change that mode
   only on an explicit operator instruction, using the bounded `adjust`
   command from the policy.
   If a target thread later begins a materially different direct mission after
   its prior mission is complete or superseded, use `mission-successor` with the
   exact predecessor root, new direct-source hash, and exact first eligible work
   identity. This appends a new policy version, preserves the predecessor in
   policy history, and creates one derived pending mission activation in the
   canonical event ledger. Immediately route the same target to that first work,
   keep it `in-progress`, and use `mission-activation-start` only after a later
   current-mission source record contains the exact work-start evidence. Do not
   create a successor task, request a manual Resume, use `bind` to overwrite a
   mission, or synthesize this obligation for initial or already-current
   missions.
8. Create a one-minute heartbeat on the liveness thread, a 20-minute heartbeat
   on the watcher, and a 4-hour heartbeat on the reviewer for supervisor-
   effectiveness review. Attach each heartbeat to its existing role thread
   rather than creating a new chat per run.
9. Bind the returned automation IDs and all role-thread IDs with
   `supervision_log.py bind`. Binding also backfills the current execution-
   economy baseline into a legacy group without granting cross-skill write
   authority; a missing mode becomes `propose-only`. Also bind
   `--liveness-thread` and `--liveness-automation`. When attaching to a legacy
   active group that lacks these bindings, add this sentinel to that same group
   without replacing its existing threads, ledgers, or automation IDs.
10. Resolve the monitored project key and create or reuse its primary self-email
   thread for the default terminal-completion report delivery. Bind it with the
   terminal-only Gmail options so this required final delivery does not enable
   ordinary intermediate alerts. When blocked/stopped priority delivery is
   requested, also create or reuse exactly one separate priority
   lifecycle thread for that project and bind it with
   `--gmail-priority-reply-message-id` and `--gmail-priority-project-key`.
   `blocked`, `failed`, and explicit `stopped` transitions use only that
   priority thread; `completed` and noncritical `paused` remain on the primary
   thread. Add both bindings to the heartbeat and reviewer role prompts.
   Multiple supervised targets in one project reuse the same seeds; different
   projects never share them. Terminal report email is enabled by default;
   ordinary intermediate, priority, inbound-reply, and roundup delivery remain
   opt-in. Do not substitute the primary or roundup thread for a missing
   priority binding, or create a replacement thread during recovery.
11. When the user requests Gmail reply processing, create one projectless
   `gpt-5.6-luna` thread at `low` reasoning using the Gmail gate prompt and one
   projectless `gpt-5.6-sol` thread at `xhigh` reasoning using the Gmail reply
   processor prompt. Create a two-minute quiet heartbeat on the Luna thread,
   bind both thread IDs and the automation ID, and initialize current thread
   messages as known so historical mail is not replayed. Include the bound
   automation ID in the gate prompt so it can apply the policy's one-minute
   active cadence after conversational activity and restore two minutes after
   the 30-minute quiet window. The Sol XHigh processor remains idle until Luna
   finds a genuinely new reply.
12. When the user requests periodic roundups, create one separate self-email
   roundup thread for the monitored project, one projectless `gpt-5.6-sol`
   thread at `xhigh` reasoning using the roundup prompt, and one Pacific-time
   heartbeat at 7:00 AM, 1:00 PM, 5:00 PM, and 11:00 PM on it. Reuse that
   roundup seed for every later summary; never
   create a new email conversation per run. The primary thread remains the
   alert, reply, and action channel.
   When the user also requests a weekly supervision review, reuse this roundup
   writer and Gmail thread. Add one Monday 8:00 AM America/Los_Angeles heartbeat
   by default. Do not create another writer thread, email conversation, metric
   store, or report authority.
13. Send the liveness sentinel and watcher one immediate check after logging and
   schedules are ready.
14. Read all applicable role threads, view every automation, and run
   `supervision_log.py status` to verify the boot. Report all thread IDs,
   automation IDs, cadence, models, target IDs, log roots, and notification
   binding when enabled.

Repeat independently for additional targets.

## Operate supervision

- Use the Luna Low sentinel only for a one-minute mechanical liveness gate. It
  reads the compact target status/update marker and calls `liveness-gate`; it
  never reads target turns, repositories, trackers, or test output and never
  decides whether inactivity is semantically valid. When canonical posture is
  `in-progress` and the target is non-active beyond the 90-second grace, the
  helper pulls forward the already-bound watcher, then Sol XHigh, then Sol Max
  on consecutive unresolved minutes. Each send still requires
  `thread-route-gate`. Identical state is suppressed after that ladder, and an
  active target records recovery without a route. The sentinel never messages
  the target, creates a replacement task/group, runs proof, or performs a fix.
- Use the watcher for proactive 20-minute checks. Tighten to 15 minutes only
  during a concrete high-risk/expensive phase and restore 20 minutes afterward.
- If the compact target read is unavailable, call `watcher-availability`
  instead of writing an ordinary no-intervention record. At three consecutive
  same-target, same-fingerprint unavailable reads, the helper opens or reuses
  one supervision-owned incident and returns the exact autonomous retry and Max
  route. It must suppress identical unavailable checks until availability or
  the read trigger changes. Do not interpret an unavailable read as unchanged
  target state.
- Close that incident only after `watcher-availability --read-status
  available-verified` retains one real compact read and one distinct next-state verification,
  and the bound Max reviewer accepts the effectiveness evidence.
  The helper's verified-read record is review-ready evidence, not self-closing
  authority.
- Use Terra only for the compact change gate, mechanical triage, and obvious
  emergency-stop conditions. Route every materially changed state to the Sol
  XHigh base reviewer; Terra must not be the semantic no-intervention authority.
- Require Sol XHigh to read the bounded target delta directly rather than rely
  on a Terra-selected substantive summary. It escalates a supported concern,
  material uncertainty, checkpoint, or major plan change to Sol Max.
- Route a deterministic one-in-six sample of Sol XHigh no-intervention states to
  Sol Max for an independent direct-delta review.
- Record Max and meta samples as non-completion review evidence. They must never
  replace or regress the Terra/XHigh change-gate completion watermark.
- Allow a narrow automatic steer only for a concrete supported violation. Report
  a genuine ambiguity or material trade-off to the user instead.
- Do not repeat an unchanged incident or steer. Respect the configured cooldown.
- Keep ordinary implementation, checkpoint, audit, and incident progress in the
  monitored target thread. Send a cross-thread role packet only to a configured
  supervision role that owns a required action or decision. Before every such
  send, call the helper's `thread-route-gate` with the exact recipient, purpose,
  source record, and required action, and require `send_allowed=true`. Never use
  an unrelated chat or side conversation as a status sink. User-facing email
  goes only through the maintained notification gates.
- An explicit direct-user request may route one bounded `status-broadcast` to
  the recipient policy's exact target. Bind source task/item and scope, record
  the returned deduplication key, and never broadcast routine progress.
- Record before routing a critical correction or reporting one handled. Mark
  that route `--severity critical` and cite the exact current open incident head,
  incident ID, and failure-mode ID. The head must already bind the complete
  failure-mode envelope and correction, an autonomous target/supervisor owner,
  `user_action_required=no`, and a nonempty autonomous next effectiveness
  trigger. A missing, stale, mismatched, triggerless, or terminal head fails
  closed; the route gate returns the exact accepted head and currentness root.
- Bind every new supervision group to an exact content-minimized mission root
  and controlling source record before its first watcher check. The semantic
  mission remains in its direct goal, repository, or tracker sources: its
  primary outcome governs subordinate process optimization, while ordinary
  required effects, hard direct authority/safety boundaries, and acceptance/
  stop boundaries remain distinguishable. A legacy unbound policy may still be
  observed; only an explicit `bind` with the exact root and source may upgrade
  it.
- Run every target from that independent mission charter whether or not the
  target implements native alignment. Target-native alignment records, when
  present, are optional read-only corroboration. They never authorize or block
  supervisor action, never replace direct mission sources or observed effects,
  and are never written by supervision. When absent, report native alignment
  `unavailable/open` while continuing ordinary observation and charter-based
  semantic review. Only absence of an authoritative mission charter prevents a
  consequential containment or decision.
- After a same-target `mission-successor`, treat the helper's pending mission
  activation as the immediate continuation boundary. Route the current target
  to the exact first eligible work, and close the activation only from exact
  later target evidence through `mission-activation-start`. While pending,
  `completed`, `paused`, and `stopped` fail closed with target posture
  `in-progress`. This is not the distinct successor-task transition workflow
  and never creates a task or manual Resume requirement.
- Apply the maintained generic completion meta-charter before project-specific
  review: observable outcome outranks process proxies; authorized ordinary
  effects needed for completion are expected; safe in-scope continuation is the
  default; and valid work, history, and user-owned state are preserved. Derive
  the exact project charter from current direct goal/repository/tracker sources,
  never from supervisor state or a target's self-attestation.
- Treat `completed` as a gated semantic claim, not an observed status to relay.
  Before recording it, require a Sol XHigh or Max reviewer to reconstruct the
  primary outcome from current direct sources, inspect the operator-visible
  deliverables, reconcile expected versus actual effects, verify exact
  artifact/currentness bindings, and determine whether every retained open item
  is compatible with that outcome. Also reconcile the requested product
  capability, protected capabilities, selected architecture level, accepted
  tradeoffs, current behavior, operator-visible effects, and any supported gap
  with its narrow owning skill or repository component. Hash the exact
  normalized reconciliation object and record that root with the other five
  content-minimized roots through `completion-record`, supplying exactly one of
  `--capability-reconciliation-json` or `--capability-reconciliation-base64`.
  Preserve the explicit-file path's fail-closed checks. When the reviewer role
  forbids file creation, require the canonical base64 path rather than creating
  a temporary file.
  The submitted JSON remains caller-owned and is not copied into the canonical
  ledger; the helper validates it first and retains its normalized root,
  revision, posture, gap count, and independent role identities. The helper must reject
  `completed` when that record
  is missing, failed, stale, tied to another mission or fingerprint, or lacks
  any required binding.
- Treat product-capability reconciliation as semantic outcome proof, not a
  duplicate test inventory. Reconstruct the requested capability from the
  direct mission and current product-capability frame when one exists. Verify
  that the selected architecture level still matches the current owner, that
  accepted tradeoffs remain compatible with the request, and that current
  operator-visible effects establish the capability without regressing
  protected behavior. If current evidence supports a gap, reject completion and
  reopen only the narrow authoring, implementation, supervision, or target
  owner that can close it. Do not broaden the mission, invent product intent,
  or treat populated artifacts, passing tests, or an evolution disposition as
  the capability itself.
- A tracker, test, audit, commit, push, record population, or terminal ledger may
  support but never replace outcome proof. When the tracker and direct mission
  disagree, open a critical false-completion review, keep supervision and the
  target active, and route the narrow tracker/outcome correction. Do not send a
  completion notice or pause automations until `lifecycle-gate` returns
  `completion_permitted=true`.
- After a current completion record passes, generate two verified derived
  terminal reports through `terminal-report`: one covering work since the
  latest prior report or roundup and one inception-to-completion full
  implementation "report of reports." Send one completion email to the bound
  primary Gmail thread with both PDFs attached. Read the exact sent message with
  raw MIME, also read the bound seed message, and read both attachments through
  Gmail. Every prepare, finalize, verify, delivery, and shutdown boundary must
  re-establish the exact completed implementation range, current lifecycle, and
  completed governing-outcome posture. A successful `verify` appends a rooted,
  dedicated verification receipt over the immutable manifest, PDF hashes, and
  complete extracted PDF projections. Delivery-only retries must reuse those
  retained bytes and current receipt; they must not regenerate either report.
  `record-delivery` must parse both MIME messages, prove the sent message
  is a reply in the seed's provider-owned thread, bind each attachment to that
  exact owner message/thread plus its attachment/read-call IDs, and prove the
  returned bytes equal the verified PDFs. It also requires an independently
  signed exact review of the retained Gmail provider outputs and retains that
  signed object byte-for-byte after validation; caller-supplied
  message, attachment, read-call IDs, or hashes alone are insufficient.
- Treat `supervision_pause_permitted=true` as the shutdown boundary. It requires
  the accepted completion record, exact completed lifecycle, both current report
  PDFs, and their recorded Gmail delivery. Pause every exact bound project
  supervision automation, then run `terminal-shutdown`. The helper reads the
  maintained Codex automation owner files directly and requires every exact
  bound automation to belong to its policy-bound runtime role task and be
  paused by an update no earlier than report delivery. It rechecks the owner
  files across the canonical append and records a rooted currentness rejection
  if they change. Generic records cannot create terminal delivery,
  verification, or shutdown evidence.
  Do not claim that supervision stopped when an expected owner is missing,
  active, stale, or divergent.
- Treat an unsupported goal-preventing stop as a critical operational event,
  not every pause or bounded wait. Completion, a current direct stop/goal
  change, a hard authority/safety boundary, independently established current
  infeasibility, or an unavailable required nondelegable input with an empty
  safe frontier may support stopping. A test result, checkpoint freeze,
  historical hold, monitoring uncertainty, or nonempty safe frontier alone may
  not.
- Preserve non-scalar mission impact for every material containment or decision:
  mission root, exact authority class/source, local/material/goal-blocking/goal-
  reversing impact, affected width, duration, reversibility, whether an ordinary
  required means is disabled, and independent mission review. Missing or stale
  mission binding fails closed for consequential action, never for ordinary
  observation, change detection, or a simple target action.
- Treat containment as a temporary operation envelope, not durable authority.
  Route it only with exact operation/Block scope, content-minimized identity,
  expiry event, `carry-forward=false`, and successor effects allowed; record the
  same structure in the existing append-only event ledger. Expiry retires it to
  history, and neither compaction nor a later Block silently revives it. A
  critical goal-blocking emergency hold is limited to one operation and requires
  independent mission review. A supervisor may never reverse the mission goal.
- At a Block transition or acceptance checkpoint, inspect the current and next
  eligible Block for an allegedly non-delegable decision gate. Independently
  test necessity; tracker labels such as `responsible human adoption` or
  `operator decision` do not suffice. A single eligible, independently reviewed
  recommendation whose trade-offs are resolved by current objectives proceeds
  under the user's standing imperative. If a genuinely non-delegable decision
  packet is or will imminently be complete, require the target to surface it
  early while safe work continues. Use the dedicated priority decision lane
  only when substantive decision context is explicitly enabled; routine
  advance forecasts remain on the primary lane.
- Treat continuation as the default while a genuine decision remains open.
  Require the target to freeze the decision packet, exact blocked subjects and
  descendant closure, and maximal safe-work frontier. If that frontier is
  nonempty, target idleness or a whole-run wait is a high-severity supervision
  defect: steer the target to continue the independent slice and keep the
  incident open until resumed evidence exists. Provisional/common work may not
  be promoted or called accepted.
- Record and drive genuine decisions through `decision-record` and
  `decision-gate`. Start one bounded Sol Max resolution attempt before asking
  the user. If that attempt remains unresolved, send the complete priority
  decision brief, open the 20-minute response window, and continue safe work
  plus the remaining bounded Sol Max attempts during that window. Each attempt
  is capped at 20 minutes and resolution stops the protocol early. After the
  third attempt and response window, select and proceed for delegated judgment
  or human preference; for a missing fact or reserved authority, hand off an
  exact safe deferral. Never fabricate a fact or self-authorize a reserved
  action.
- Treat `decision-gate` as the mechanical target-lifecycle boundary. When it
  returns `blocking_permitted=false`, require the target Goal to remain
  `in-progress` even if the safe frontier is empty; a target-emitted `blocked`
  result is an invalid lifecycle transition that requires an immediate narrow
  resume steer. Do not ask the operator to press a Resume control. After an
  exact selected or safely deferred handoff, require automatic target
  acknowledgement and continuation at the next turn boundary. Only
  `blocking_permitted=true` may support a terminal blocked posture.
- Treat every safe deferral as provisional and currentness-bound. If later
  canonical direct authority corrects, cancels, or expires the exact successor-
  topology premise that produced the deferral, the governing reducer must
  reconcile that decision immediately, keep the target `in-progress`, and
  return `record-decision-correction-and-continue-governing-outcome`. Append the
  explicit `corrected` decision record from that same authority, but do not keep
  the target blocked while waiting for the bookkeeping append. Mismatched
  mission, source, state fingerprint, transition lineage, or authority remains
  blocking. The exact transition genesis must predate and be cited by the
  decision-ready record, every later decision phase must preserve the frozen
  decision identity, and the cited matching lineage must be unique; a generic,
  uncited, later-created, or ambiguous event is never enough.
- Treat every unresolved Important/Critical notice as an incident, not a
  terminal notification. Route it immediately to the event-driven Sol XHigh
  notice reviewer. A corrective steer changes the incident to
  `awaiting-target-evidence`; it does not resolve it. On each later changed
  target fingerprint, route every relevant open incident whose latest record is
  not already bound to that fingerprint back to the notice reviewer.
- Separate incident importance from email urgency. Record `resolution_owner`
  and `user_action_required` for material incidents. Target- or supervisor-owned
  remediation remains silent while it is progressing normally; its intermediate
  state belongs in the four-hour digest and separate roundup.
- Skip deep analysis when the target state has not materially changed.
- Review execution economy on every materially changed state across relevance,
  ordering, scope, reuse, batching, stability, convergence, stopping,
  proportionality, and resource posture. Judge the causal path to the Block
  outcome, not duration or activity volume alone.
- Treat repeated equivalent reads, deep scans, tests, renders, model calls, or
  failed runtime probes; per-item work where a bounded batch exists; validation
  before likely-mutating review; reconstruction where exact reuse is available;
  speculative machinery; context thrash; and continued work after the stop or
  acceptance condition as signals requiring semantic review, not automatic
  findings.
- Intervene only when the actual target delta supports an avoidable active cost
  or correctness risk and the narrowest better path is concrete. Do not stop a
  relevant long run merely because it is long, and do not create generic
  process work from one ambiguous episode.
- A reusable-maintenance candidate never substitutes for correcting the active
  run. When avoidable work is still in flight, direct the target to contain only
  the exact owned action, preserve valid completed evidence, mark aborted or
  superseded work accurately, and apply the narrow current-run correction before
  resuming. The target thread—not a supervisor role—owns any tracker, repository,
  runner, or implementation edit under its ordinary authority.
- Require the current-run correction to name the causal defect, smallest owner,
  exact affected command or work slice, evidence that remains reusable, tracker
  or execution-brief amendment when needed, focused revalidation, and resume/
  stop condition. Recompute the affected proof after correction; never restart
  the same wasteful path merely because reusable skill maintenance is pending.
- Keep Gmail polling separate from implementation monitoring. Luna Low performs
  only the message-ID gate and never interprets or acts on the user's reply. It
  uses the helper's derived cadence: two minutes while quiet, one minute for 30
  minutes after a genuine reply or a recorded ACK/result, then two minutes
  again. It wakes Sol XHigh only for a previously unprocessed user message.
- Keep priority lifecycle and roundup traffic out of the primary Gmail thread.
  A project may have one primary supervision thread, one priority lifecycle
  thread, and one roundup thread. The priority thread is immediate and limited
  to `blocked`, `failed`, and explicit `stopped`; the Pacific-time writer never
  delays or replaces it.

Adaptive implementation authority is separately configurable through the same
policy owner. New groups start `full-autonomous`; a legacy group without the
field behaves as `fixed` until an explicit `bind` or `adjust` appends the
migration. Operators may select `fixed`, `recommend`, `reviewed-autonomous`, or
`full-autonomous` and adjust the one-lane file/change/command/time/mapped/review
ceilings without changing code. The retained candidate interchange has fixed
absolute caps of three files and six commands, so policy may tighten but cannot
widen those two ceilings:

```bash
python3 scripts/supervision_log.py adjust \
  --target-thread <target-thread-id> \
  --adaptive-decision-mode <fixed|recommend|reviewed-autonomous|full-autonomous> \
  --adaptive-target-class <target-repository|software-factory> \
  --adaptive-target-repository-root <canonical-absolute-repository-root> \
  --candidate-max-active-lanes 1 \
  --candidate-max-files <n> \
  --candidate-max-changed-lines <n> \
  --candidate-max-commands <n> \
  --candidate-max-elapsed-minutes <n> \
  --candidate-max-mapped-comparisons 1 \
  --candidate-max-review-passes 1 \
  --reason <operator-directive> --evidence <source-record>
```

Before applying or exposing an adaptive choice, call
`adaptive-decision-gate --decision-evidence` with one bounded canonical source
packet. The helper recomputes the decision fingerprint and currentness from its
mission/Block, target revision/state, adjudicating evidence, owner/scope,
protected capability, Stop, safe-frontier, and revisit fields plus the current
policy and governing event head. It derives target class from policy and effect
class from target plus disposition; callers cannot supply a fingerprint or
substitute a weaker target/effect permission. Candidate dispositions also
require one bounded canonical
`--candidate-evidence` JSON object that binds owner, source revision, candidate,
usage, protected-capability, validation, comparison, and currentness roots.
The repository root is canonical policy state: it must be the exact existing
Git top level (never `/`, an ancestor, or a symlink), bind it at `init` or
exactly once while migrating an older policy, and never widen or replace it.
Candidate source revision and decision-basis root must bind the exact target
revision, Block/capability/state, affected paths/content, and protected contract;
candidate protected-capability evidence must cover all and only that contract.
The gate rehydrates the policy-pinned tracker, exact Git HEAD, affected regular
file bytes, candidate after-bytes, focused-before-mapped result sequence, six
comparison dimensions, and elapsed/resource use. A separately sealed evaluator
signature accepts that retained candidate packet. The canonical event ledger,
not a candidate counter, supplies the one-active-lane-per-target frontier.
Software Factory proposer and implementation-owner identities come from the
configured owner roles and remain explicit in both reviewer/evaluator signatures
and canonical events. Never replace any of these with caller flags or counts.
The gate records the decision in the existing event ledger, but it never writes
the target or publishes an unconditional cross-owner write grant. An otherwise
applicable decision is `owner-application-ready` with
`application_authorized=false` and an exact application-precondition root. Only
the existing target Git/write owner may consume it, and that owner must
atomically revalidate policy, target revision/state, affected bytes, candidate
currentness, and owner identity in the same write transaction. When the gate
returns `automated-independent-review-required`,
the external reviewer signs the complete source-decision identity, fingerprint,
currentness, semantics, candidate/owner, disposition, policy, and evidence
result with the sealed reviewer authority. Import it exactly once through
`adaptive-decision-review --review-json`, then rerun the gate with that canonical
event ID. Software Factory mutations, including inline correction, additionally
require a separately signed accepted evaluator result from the sealed evaluator
authority; the reviewer signature then binds that exact evaluator result.
Neither a boolean, caller ID, self-hash, nor reviewer prose proves review. In
`full-autonomous`, the
adaptive gate and the existing decision/notification owner both reject or
suppress every human-request attempt: resolve
ordinary judgment from current sources, choose the safest reversible supported
option, or record `reserved-external` with exact blockers and continue the safe
frontier. Do not send a Resume instruction.

When a target-repository semantic review is already retained as the exact
`independent-review-clean-signature-unavailable` supervision event, seal the
current review-required decision through
`adaptive-decision-review-sign --source-record --review-evidence-record
--output-json`. The signer accepts only an exact decision-source/fingerprint
match to the independently reviewed decision, permits a governing-head-only
currentness and semantics refresh, derives every review field from the current
canonical event, uses the fixed owner-only reviewer key, revalidates the
resulting signature through the sealed public authority, and writes one
immutable canonical artifact. It does
not reinterpret findings, sign rejected or inconclusive evidence, sign a
Software Factory self-change without its distinct evaluator, or import or apply
the result. Run the signer and `adaptive-decision-review` without an intervening
event.

An accepted `amend-structure` adaptive decision is only the trigger for the
existing tracker-authoring owner. It is not tracker bytes or range authority.
Before authoring begins, bind one immutable `tracker-authoring` policy profile
to the exact authoring target thread through `adjust
--program-revision-authoring-thread
--program-revision-authoring-profile-review`; its policy-owned watcher, base
reviewer, reviewer, and optional fix executor are authority, not caller labels.
The supplied signed review must independently accept the exact Git revision and
blob root only as the profile-design contract; it must explicitly make no claim
that the separate tracker Blocks are implemented. The mechanical route
cites the source adaptive decision, the
semantic review cites the canonical signed review event, and adjudication cites
the separately signed evaluation root.
The author builds an exact active-program revision packet through
`author-implementation-trackers/scripts/program_revision.py`; a distinct sealed
reviewer signs the exact predecessor/proposal, accepted history, Block map,
affected closure, finding lineage, profile source/binding, and resume Block.
Import that result with
`implementation-program-revision --previous-tracker --proposed-tracker
--packet-json --review-json --decision-evidence`. The command records one
append-only `implementation-program-revision` event and never edits the target.
An identical event retry returns the same exact proposal-installation next
action rather than only a duplicate marker.
Only `accepted` permits the repository owner to install the exact proposal and
then call `implementation-range-amend` with that event. `revise` and `rejected`
remain history and continue unaffected safe work; a successor must bind and
resolve their open findings before acceptance. Full-tracker intent expands
across inserts/splits/renumbering; explicit ranges map to the successor union
plus every incomplete inserted prerequisite. The application must be one
single-parent tracker-only commit whose parent is the packet target revision,
with exact predecessor/proposal blobs. Revalidate current policy, decision,
current HEAD, and live tracker bytes at first application and again at the
policy-write boundary, then resume the derived dependency-safe Block without a
user scheduling step. An identical retry returns that same resume state. Do not
use this path for status-only or local corrections.

Adaptive mode never grants repository, command, credential, spend, destructive,
Gmail, deployment, release, promotion, or skill-maintenance permission. A
candidate still requires one lane, exact ceilings, focused-before-mapped proof,
and independent review; ceiling exhaustion or protected regression retires it.
Use `status` to inspect the mode, budget/use, decision and human-request counts,
reserved deferrals, safe frontier, and application posture.

## Record and improve

- Record every bounded check as one compact JSONL event. Create Markdown only for
  material incidents, effectiveness reviews, and the deterministic human-readable
  projection paired with an explicitly requested weekly PDF review.
- Keep decision timing and continuation evidence in the same JSONL ledger:
  classification, decision-ready/deadline times, attempt number, packet hash,
  blocked-scope hash, safe-frontier hash/posture, disposition, handoff, and
  target acknowledgement. Do not add a decision ledger or copy substantive
  packet content into supervision records.
- Preserve mission root, authority provenance, and non-scalar mission impact
  unchanged through every decision transition. `reserved-authority` may cite
  only an exact applicable direct-user, system, repository, or tracker source;
  a supervisor steer, unbound `codex_delegation`, or derived inference cannot
  create it. A helper-validated delegated-authority event and current receipt
  carry the exact independently verified originating direct-user authority
  through the current pending mission-activation source and the system's owner-produced
  target-action route result; execute that bounded source
  without asking the user to repeat it, and never expand it from the routing
  packet. Goal-blocking or goal-reversing posture requires commensurate direct
  authority plus an independent mission-level challenge.
- Use only `scripts/supervision_log.py` for supervisor filesystem writes. Never
  place patent prose, project paths, credentials, prompts, or copied tool output
  in supervision records.
- Generate an on-demand or scheduled weekly review with the helper's
  `weekly-report` command. `prepare` deterministically scans the entire bounded
  window and writes canonical metrics plus a full content-minimized cognitive
  review packet. The Sol XHigh roundup writer must read every packet record and
  synthesize patterns, effectiveness, misses, monitored development pace,
  machinery changes, resource posture, and limitations; it may not merely
  restate counts. The review evaluates the supervisor and monitoring machinery,
  not the implementation it observes. Target details may appear only as bounded
  evidence of what supervision detected or prevented. Recommendations may
  change only supervisor watchers, reviewers, routing, incident handling,
  reporting, or operating policy; they must never prescribe target work.
  `finalize` accepts only the exact hash-bound cognitive-review contract and
  creates one canonical machine-readable `report.json`, its deterministic
  Markdown and charted PDF projections, and a file manifest. The report includes
  explicit scheduled-active/paused hours, total period hours, recorded
  target-read availability, and model-attributed token/cost projections under a
  versioned public API-equivalent pricing profile. Never infer continuous uptime
  from quiet event gaps or label projected tokens/cost actual, billed, invoiced,
  or provider-reconciled. `verify` fails on a divergent JSON/Markdown
  projection, manifest, evidence reference, or unreadable PDF.
- At accepted terminal completion, use the helper's separate `terminal-report`
  owner. `prepare` freezes the delta-since-last-report and full-run evidence
  packets; the Sol XHigh reviewer writes both required evidence-bound syntheses;
  `finalize` produces canonical JSON, Markdown, and PDF projections; and `verify`
  fails on divergent content, hashes, manifests, or unreadable PDFs. The full
  report must synthesize earlier roundups and reports rather than merely repeat
  the last interval. Both reports describe implementation outcome and evidence,
  not patent prose or a new completion authority.
- Lay out the PDF for fast inspection: the first page is an executive dashboard
  naming the monitored target, exact coverage and duration, configured
  supervision roles, scheduled monitoring time, projected cost, incidents
  detected/resolved/open, and a short cognitive assessment. Put a concise table
  of contents at the bottom and move daily activity to a supporting page. Every
  chart must name its units, show readable axis ticks, place the color legend
  below the plot, and explain each category in operator language. Internal
  counters such as events, changed states, tracker stages, or tool changes may
  appear only in defined supporting detail, not as unexplained headline cards.
  Limit each cognitive-review section to three concise evidence-backed findings
  so review domains remain skimmable. Start every major review domain on a new
  page. Use only maintained
  foreground/background pairs that pass the report's 4.5:1 contrast check. Do
  not lead with a long narrative or reproduce target line items as report
  content.
- Treat recorded task counts as a lower bound when scheduled no-op wakes are not
  logged. Always show the intended trigger/cadence beside actual recorded
  activity, define rate denominators, and distinguish detection-rate changes
  from causal claims about implementation quality.
- Run the Sol effectiveness heartbeat only when new checks, incidents,
  interventions, checkpoints, or outcomes exist. It samples the original target
  deltas behind no-intervention records—not merely the records—to look for false
  negatives.
- Classify a recurring or materially expensive execution-economy defect as a
  de-projectized maintenance candidate only after Sol Max verifies the actual
  episodes, the avoidable counterfactual, the proper owner, and the risk of
  false blocking. Route tracker-design defects to
  `author-implementation-trackers`, execution-sequencing defects to
  `implement-tracker-blocks`, and detection/intervention defects to this skill.
  Repository-specific defects remain with the target tracker, instructions,
  profile, or runner.
- Pursue reusable maintenance and active-run remediation as two linked but
  independently closed lanes. The current target must demonstrate containment,
  narrow correction, and effective resumed behavior. The reusable lane prevents
  recurrence in later runs. Neither lane may claim the other lane's evidence or
  remain open merely to justify broader work after its own stop condition passes.
- Before recording effectiveness or terminal closure for a supported execution-
  economy incident, record one explicit bounded reusable-lane disposition on
  that incident-owned event: `candidate-opened`, `existing-owner-sufficient`
  with exact evidence, `repository-specific-not-applicable` with rationale, or
  `evidence-pending` with its next evidence trigger. Current-run correction and
  the reusable lane remain independently owned; silence is not a disposition.
- The Sol XHigh fix executor normally applies only the bounded policy fields
  accepted by `supervision_log.py adjust`. In
  `apply-allowlisted-skill-maintenance-with-review` mode, it may also update
  only `author-implementation-trackers`, `implement-tracker-blocks`, and
  `supervise-tracker-runs`, and only from a current Sol Max plan that cites
  de-projectized evidence, exact files, focused validation, safe activation,
  and a stop condition. Sol Max must independently accept the exact change
  before active role prompts or automations are refreshed.
- When those allowlisted skills live in a Git repository, the fix executor must
  preserve unrelated state, stage only the plan-bound files, and commit each
  coherent validated candidate before exact-change review. A rejected candidate
  remains immutable; remediation is a successor commit. After Sol Max accepts
  the exact commit, normally attempt a non-force push to the existing unambiguous
  upstream. Remote publication and the rollback-safe local release are separate
  lanes. An unavailable or failed publication becomes
  `durability-pending`, requires an autonomous retry trigger, and blocks only a
  remote-durability claim; it never changes final-response permission, required
  target posture, local promotion eligibility, post-activation role-refresh
  eligibility, or local effectiveness. After the exact accepted commit is
  available locally, have the independent release reviewer sign one exact
  `software-factory-release-acceptance` object and ingest it with
  `software-factory-release-accept`. The canonical event binds its exact source
  commit/tree, no findings, reviewer public-key identity, root, and signature.
  A generic caller-authored checkpoint cannot substitute for it, and its policy
  version must remain current when promotion begins. Then use
  `supervision_log.py software-factory-release-promote --target-thread <target>
  --repo <repo> --source-commit <commit> --acceptance-record <event>` without
  asking for another user confirmation.
  That orchestration command invokes only the
  maintained release owner's exact flagless `promote --repo <repo>
  --source-commit <commit>` operation, revalidates its returned active release
  and three installed roots through live owner status, and records one
  deduplicated canonical result. Invoke that owner with the canonical
  operating-system account home and a minimal fixed Python/Git environment;
  ambient `HOME`, `PYTHONPATH`, and Git overrides must not select release or
  installation roots. It accepts no caller-selected active identity,
  pointer, stage, quiescence, or manual-pin input. An explicit manual pin is a
  separate policy-owned exception and is never selected by this promotion
  command. Before the owner call, retain one canonical promotion requirement
  binding the exact acceptance and prior live release identity, three installed
  roots, verification root, and history count. If review advances for the same
  exact source before any effect, append one linear successor requirement only
  after proving that complete prior state remains unchanged; never let the
  retired acceptance invoke the owner. Serialize that
  requirement, owner effect, currentness recheck, and result against later
  acceptance/policy events; an interrupted retry rehydrates the one owner
  transition from live status. A changed predecessor or activation-history
  count after the effect is retained as a canonical currentness rejection and
  cannot trigger another promotion. Validate the returned owner effect before
  the following live-status observation; if another activation wins between
  those calls, retain that exact effect as rejected so retry cannot promote it
  again. The release owner must run exact-commit checks, retain the
  prior release, atomically swap the active pointer, verify it in a fresh
  process, and restore the prior pointer on failure. The signed acceptance is
  the independent acceptance itself, not a second promotion or quiescence
  authorization. Scheduled automations bind to
  the stable `current` paths, so verified activation updates their next wakes
  without rewriting schedules or identities. After promotion, run
  `software-factory-supervisor-refresh-plan` with the exact promotion record.
  It requires the canonical implementation range, reads the configured
  automation owner files, rejects foreign roles or mixed
  release identities, emits one full field-preserving migration for each
  maintained release-pinned prompt, and retains explicit manual pins. Apply each
  update only through the Codex automation owner; the next scheduled wake is the
  safe runtime boundary. Route already-running role context through the plan's
  existing `role-refresh` gates, which deliver at role message boundaries. A
  `verified` refresh-health append is provisional until a boundary reread
  confirms the same policy and exact range root, promotion, complete refresh
  plan, automation-owner roots, release activation-history count and record
  HMAC, and governing control posture. Retain drift under the newly current
  policy as a successor `currentness-rejected` event, including after an
  interrupted correction append. Before rollback, require the original
  promotion history count, reread live owner status, and pass the exact
  candidate release plus activation-record HMAC to the release owner's locked
  expected-current guard. A same-ID reactivation is not the original
  promotion; never overwrite it or another newer valid release. When a
  preserved schema-v1 rollback health record already matches the live restored
  release, rehydrate that terminal result without another owner effect or an
  incompatible schema-v2 duplicate. A supervisor
  may never create, select among
  ambiguous, rewrite, or force-push a remote.
- Changes to models, target permissions, defect semantics, auto-steer
  authority, repository access, patent authority, or the skill allowlist still
  require the user. Skill maintenance never authorizes target-repository or
  tracker edits from a supervisor thread.
- When an effectiveness review finds a problem, the Sol Max reviewer writes a
  bounded fix plan. It performs a thread-only steer itself. For any other
  permitted supervisor-maintenance correction, it hands the plan to the Sol
  XHigh fix executor. Cross-skill work must obey the current maintenance mode
  and exact allowlist. The executor may never change the target implementation,
  tracker, repository, or patent workspace.
- Preserve policy history and incident history. Correct with successor events;
  never rewrite an earlier event.
- For an enabled Gmail self-notification channel, reply only to the bound seed
  message. Send immediate material alerts and new-evidence meta digests; keep
  unchanged and ordinary no-intervention work silent. Record each successful
  delivery as a deduplicated `notification` event.
- Send one immediate `🚨 IMPLEMENTATION BLOCKED / STOPPED 🚨` message to the
  dedicated priority thread when the monitored target enters `blocked`,
  `failed`, or explicit `stopped`. Send ordinary `IMPLEMENTATION STATUS` for
  `completed` and noncritical `paused` to the primary thread. Record the exact
  transition as a deduplicated `lifecycle` event, call `lifecycle-gate`, and
  obey its channel, seed, category, and `send_now` result. State the stopped
  Block/work boundary, why progress cannot continue, whether immediate user
  action is required, the precise response route, and content-minimized source
  record IDs. When the operator has enabled substantive decision context and
  action is required, the same priority message must also contain a concise
  decision brief: the exact question, recommendation and why, material
  alternatives, trade-offs/uncertainties, consequence of no action, response
  options, and authoritative detail link. An alert that merely says `adopt or
  reject` is insufficient. Keep the supervision ledger content-minimized even
  when the email carries this explicitly authorized brief. Send before applying
  any stop-condition pause; the four-hour
  reviewer repairs a missing priority or ordinary lifecycle notification.
- Use the same dedicated priority thread after the first bounded automatic
  resolution attempt proves the decision remains genuinely non-delegable. The
  initial notice states that resolution and safe work continue, gives the
  20-minute response deadline, and includes the complete decision brief. Send
  later phase updates only when the helper makes them eligible: final
  disposition and target resumed. A decision resolved by the first attempt, a
  procedural choice, or an immediately delegable choice generates no
  human-input notice.
- Start every notification with the monitored project, target, writer role, and
  job being performed. A role that does not own email delivery escalates to the
  owning writer instead of sending a competing message.
- Make every user-facing supervisor communication that names a tracker Block
  self-contained. Immediately after the identifying fields, add the exact field
  `Block purpose — Block <N>:`. Follow it with one plain-language sentence
  describing what that Block is intended to accomplish and, when material to the
  message, where it stops.
  If more than one Block is materially discussed, give each Block its own short
  purpose line. Derive the summary from the current authoritative tracker; do
  not substitute implementation activity, status, a Block title alone, or a
  tracker link, and do not expect the operator to open the tracker. Keep patent
  substance and copied tracker text out of operational mail.
- Put a severity banner before those fields. Use `🚨 CRITICAL SUPERVISION ALERT
  🚨` for a critical incident or major error, `⚠️ IMPORTANT SUPERVISION NOTICE`
  for other material items requiring attention, and `SUPERVISION DIGEST` only
  for an ordinary periodic summary. Do not inflate routine findings into the
  higher banners. A distinct critical alert is immediate and is not delayed by
  the digest cadence or an unrelated incident's cooldown; exact-incident
  deduplication still applies.
- Every Important/Critical notice must state `Follow-up: required` or
  `Follow-up: not required`. A required notice includes its incident ID and next
  trigger. A non-required notice states the terminal or informational reason.
  Follow-up results stay in the same primary Gmail thread and use exactly one of
  `RESOLVED`, `NO ACTION NEEDED`, `CORRECTION ISSUED`, `NEEDS USER DECISION`, or
  `STILL UNDER REVIEW` as their outcome heading.
- Before any incident email, call the helper's `notice-gate` command and obey its
  `send_now`, `channel`, and `banner`. Immediate Important mail is limited to a
  critical condition, genuine user action/decision, blocked or failed
  remediation, or a supported correction that was issued. Never send an
  immediate `STILL UNDER REVIEW` update merely because an automatically owned
  incident changed fingerprint or materially improved.
- Send one nonurgent `SUPERVISION OUTCOME` terminal reply only when that incident
  was previously alerted. Otherwise leave terminal closure for the digest or
  roundup. Operational warnings are supervisor-owned and silent unless repeated
  failure blocks the monitored function or requires the user.
- Treat a reply in the bound project email thread as ordinary user input for
  that project, not as a restricted command language. Use Gmail message IDs and
  the outbound ledger—not sender identity—to distinguish automation from user
  input. Strip quoted history, record only a content-minimized hash/ID receipt,
  and route the exact new authored portion to Sol XHigh. Acknowledge it in the
  same email thread, carry out or route the instruction under the ordinary
  authorization and safety rules, and send a same-thread result when known.
  Never create a reply loop or a second primary conversation thread. The
  notification-only priority lifecycle thread and separately bound roundup
  thread are the only permitted additional conversations.
- Post four operational change-log roundups per day to the project's separate
  roundup thread at 7:00 AM, 1:00 PM, 5:00 PM, and 11:00 PM Pacific time.
  Identify the coverage period, writer, material implementation
  movement, decisions/actions, incidents and outcomes, reply-driven work, open
  posture, and source record IDs. For each materially discussed Block, include
  its short plain-language purpose so the roundup is understandable without the
  tracker. Keep patent content and copied output out.
- Send the weekly PDF as an attachment in that same roundup Gmail thread. Record
  the report event and delivery receipt in the existing event ledger. The report
  is a derived operational review, not a second status database, patent
  authority, legal conclusion, or quality score.

### Factory capability evolution

At weekly-report finalization, terminal-report verification, or an explicit
Factory-maintenance checkpoint, run the deterministic eligibility gate once.
It resolves report nominations to exact canonical event/outcome evidence,
derives a novelty key distinct from its currentness context, and either prepares
the existing packet or returns a reasoned no-op. `fixed` performs no packet
build; `recommend` may prepare only a non-authorizing recommendation;
`reviewed-autonomous` and `full-autonomous` may admit one cycle within the
existing mission, permissions, and resource contract. Repackaged reports,
overlapping windows, changed checkpoints, unrelated Factory revisions, and
prose-only themes cannot create novelty. This gate performs no model/reviewer
call, candidate work, human request, skill edit, or target write.
Productive evidence must be an exact current `observable-outcome-completion`
record that passes the existing independent capability-reconciliation contract;
a generic check, positive category, or praise-only summary is not adjudicating
evidence. A recurring productive meta-pattern requires at least two such exact
outcomes.

Use the later explicit `factory-evolution` workflow only after a supported
admission or when an operator request or maintained plan calls for
evidence-grounded improvement of the Factory's reusable capability set. This
is an on-demand derived-artifact workflow, not a watcher loop, schedule,
detector, or new supervision ledger. An explicit checkpoint uses
`factory-evolution --action admit --report-json <report.json> --events-jsonl
<events.jsonl>`; its safe evolution ID is derived rather than supplied.

Keep the roles and authority sequence exact:

1. Verified weekly reports nominate hypotheses; canonical event records and
   observed outcomes adjudicate them. Prepare a deterministic packet from
   explicit paths only:
   `uv run --python 3.14 python scripts/supervision_log.py factory-evolution
   --target-thread <id>
   --evolution-id <safe-id> --action prepare --report-json <report.json>
   --events-jsonl <events.jsonl>`.
2. A distinct `gpt-5.6-sol` cognitive reviewer at `xhigh` reads the complete
   packet and submits bounded observations, lessons, counterexamples,
   meta-patterns, broad capability candidates, visible selection dimensions,
   and one experiment. Escalate consequential or unresolved selection judgment
   to a separate Sol Max reviewer. The helper validates but does not generate
   that judgment. Finalize with only the explicit review JSON and the same
   target/evolution identity.
3. Any selected change is implemented separately by the existing
   `author-implementation-trackers`, `implement-tracker-blocks`, or
   `supervise-tracker-runs` owner under its ordinary tracker, review, Git, and
   authorization contract. The evolution command never edits a skill or target.
   For an admitted cycle, run `factory-evolution --action orchestrate` once to
   append the packet-to-reviewer handoff. After the exact review is finalized,
   run it again to append the deterministic candidate-type-to-owner handoff.
   The complete map and bound currentness fields are defined in
   `references/factory-evolution-contract.md`; no prose classifier or detector
   prerequisite may change the owner.
4. After the canonical owner-handoff event, the normal owner creates at most
   one direct isolated candidate revision while the incumbent stays current.
   Bind that exact handoff record ID, orchestration root, and record SHA-256 in
   the candidate commit and submit only the candidate revision plus one
   distinct changed focused-test path for each exact protected capability with
   `factory-evolution --action acknowledge --owner-ack-json <ack.json>`.
   The supervision owner executes those tests from the exact candidate archive;
   it does not accept submitted pass/fail, output-hash, protected-posture,
   timestamp, owner, or Stop assertions. One aggregate deadline begins at the
   canonical handoff; each test receives only the remaining time and execution
   stops at the first failure or exhaustion. `status` returns `compare` only for a
   current candidate within scope, protected-capability, command, file, line,
   elapsed-time, and Stop ceilings; otherwise it returns a stopped/reject
   posture. Retry rehydrates the one existing canonical stage without rerunning
   its completed owner proof.
5. Run `orchestrate` once more only after the owner proof is comparison-ready.
   It first verifies the configured sealed evaluator interface, then the
   supervision owner executes the one declared mapped incumbent comparison.
   A canonical comparison-start event makes a missing completed result a Stop,
   not permission to rerun. The pending result binds that exact start record ID,
   record hash, root, and chronology, so pre-start bytes cannot become the
   handoff. A per-cycle owner lock serializes duplicate
   deliveries, while an
   owner-authenticated, file-and-directory-synced pending result makes an
   interrupted handoff append reuse that exact comparison instead of rerunning
   it. The pending record is a transient owner artifact, not part of the
   finalized evolution bundle; after the canonical handoff retains the exact
   raw result and provenance, the owner verifies and removes the pending file
   with parent-directory durability. The resulting
   nonauthorizing evaluation handoff binds that provenance, the evaluator key,
   the raw incumbent result, and the retained candidate proof. The sealed
   adaptive evaluator, distinct from
   proposer, reviewer, and implementer, signs separately attributable,
   revision-bound baseline and candidate results for every positive and
   exception case. `evaluate` verifies the fixed evaluator key, exact handoff,
   raw result roots, protected proof, contrary evidence, and regression posture,
   then records one immutable disposition: `promote`, `advisory`, `revise`, or
   `reject`. At the evaluation boundary, `promote` is adoption eligibility
   only; every disposition preserves incumbent authority until the separately
   governed adoption action runs.
   The handoff also binds the exact target-owner ref and bounded reflog-file
   currentness root, including same-HEAD events. Target-currentness loss at
   either canonical handoff or evaluation append is followed by an exact
   correction event; the bound owner root keeps a stale source inactive even
   if correction persistence is interrupted or the target ref transiently
   changes and returns.
6. For an evaluated cycle, run `factory-evolution --action orchestrate` again.
   Fixed mode records only, recommend mode records a recommendation, and lower
   dispositions record their exact retain/revise/retire posture without release
   inputs or installed mutation. A current reviewed/full-autonomous `promote`
   requires the four existing skill-release permissions plus
   `--release-review-evidence <signed-review.json>` and
   `--quiescent-evidence <signed-operator-boundary.json>`. The supervision
   owner then calls the existing local release owner; it does not write a skill
   itself. Retry rehydrates one activation, and successful full autonomy records
   zero human requests before continuing to current-outcome reconciliation.
7. Close the cycle with `factory-evolution --action outcome`. An installed
   adoption requires the latest independently verified observable-outcome
   completion record for the exact evaluation/adoption state. A verified
   result becomes current `adopted-effective` evidence. A later supported
   regression appends a successor outcome in the same lineage and, with exact
   quiescent evidence, invokes the existing release owner once to restore the
   frozen baseline. Retry rehydrates an interrupted rollback or outcome append;
   currentness loss appends a correction and leaves no false authoritative
   outcome. Non-adoption dispositions close against the incumbent without a
   release input. Only a current terminal outcome consumes the admission's
   canonical coverage; unchanged overlap is a no-op, while one newly nominated
   canonical outcome/event may support a later bounded cycle. Weekly and
   terminal JSON, Markdown, and PDF reports project concise current outcome
   summaries without gaining authority or opening a monitor.
8. Run `verify` against the stored set. Verification reopens the immutable
   packet, review, evaluation, report, and manifests and recomputes their hashes
   and schemas without rerunning a producer.

For terminal integrated evidence only, run
`scripts/factory_evolution_dogfood.py` exactly as documented in
`references/integrated-factory-evolution-dogfood.md`. Inspect its raw rooted
inputs, temporary installed bytes and executed output, current stable-skill
identities, operator status, consumed-input no-op, rejected candidate, role
separation, and false live-effect flags. Do not replace those observations with
the test result, artifact count, evaluator disposition, changelog, or summary.
The runner is not an alternate live release or supervision owner.
Retain the run-specific raw JSON with `--evidence-output`; use the separately
rooted default/stdout semantic projection only for deterministic replay. The
projection is nonauthorizing and never substitutes for raw-currentness review.

The evaluation disposition remains independent evidence. Before terminal
completion, reconcile the resulting current Factory behavior against the
requested capability, protected capabilities, selected architecture level,
accepted tradeoffs, and operator-visible effects. A populated or verified
evolution artifact set cannot replace that reconciliation. A supported gap
reopens only its narrow ordinary owner; `promote` is never forced merely to
finish the cycle.

Run the helper with the maintained `uv run --python 3.14 python` runtime, or
another Python 3.11+ interpreter; the macOS system `python3` may be too old for
the helper. All public writes go through `scripts/supervision_log.py` under
`~/.codex/supervision/tracker-runs/<target-thread>/learning/factory-evolution/
<evolution-id>/`, or the equivalent target directory below an explicit
`--root`. Writes are atomic and
immutable-or-identical. Reuse an unchanged ID only for byte-identical artifacts;
use a new safe ID for a changed candidate or evidence set. A recorded `promote`
disposition is review evidence for a separately governed adoption path, not
automatic adoption or permission to edit, install, route to a target, notify,
schedule, deploy, or promote. Do not copy target files, transcripts, prompts, or
hidden reasoning into the review.

Stored evolution JSON is accepted only as a regular file under that owner, in
the exact deterministic writer encoding and within the maintained four-megabyte
per-artifact ceiling. Verification holds one stable identity through each read;
path-type, byte-bound, encoding, or identity differences fail closed.

## Pause, resume, or stop

- Pause all project supervision automations when the target completes, becomes
  genuinely inactive after the decision protocol and safe-frontier check, or the
  user requests a pause. Do not pause merely because a material decision awaits
  user input; the watcher must continue the timed resolution protocol and verify
  safe-frontier progress.
- Before pausing supervision for a blocked, failed, or explicitly stopped
  target, ensure its deduplicated priority-thread lifecycle email was sent.
  Before pausing for a completed or noncritical paused target, ensure its
  ordinary lifecycle-status email was sent to the primary project thread. For
  `completed`, the required lifecycle email is the terminal report email with
  both verified PDFs attached; do not send a report-less substitute.
- Before accepting or pausing for `completed`, require the exact current
  `completion-record`, a lifecycle event bound to that record, and
  `lifecycle-gate` with both `completion_permitted=true` and
  `supervision_pause_permitted=true`. A failed completion gate
  keeps the target active and requires a critical false-completion review; it
  is not a notification-only defect. A passed outcome gate with missing report
  delivery keeps supervision active only long enough to produce, verify, attach,
  send, and record the terminal reports.
- A blocked posture is valid only when the exact non-delegable input remains
  absent, proceeding would cross a declared authority/safety/stop boundary, the
  first attempt remained unresolved, the complete human-input packet has been
  exposed, and all safe scoped work is exhausted. Otherwise steer the target to
  continue or narrow the stop. Record when the blocker was first foreseeable
  and when it became decision-ready.
- Before accepting any target `blocked`, `paused`, `stopped`, or `completed`
  lifecycle, call `control-posture-gate` on the governing-outcome owner target.
  It is the sole required target posture. The gate keeps governing outcome,
  tracker/program, execution run, Codex task, supervision group, and Block
  identities separate; follows at most eight exact acyclic successor-member
  ledgers; and binds their policy/event heads into one currentness root. Use
  `decision-gate`, `successor-transition-gate`, and `lifecycle-gate` only for
  their local diagnostics. If any local result conflicts with the canonical
  posture, preserve it as evidence and obey `control-posture-gate`.
- A stale application
  `Goal blocked` card after target acknowledgement is not current target state;
  the exact active turn and supervision decision head control. The resumed
  notification must say that no manual Resume action is required.
- Before accepting a source-task `paused`, `stopped`, or `completed` posture
  after a successor handoff, call `successor-transition-gate`. Record the
  transition in the canonical event ledger through the exact phases
  `required`, `successor-created`, `successor-bound`, `handoff-sent`,
  `target-acknowledged`, and `work-started`. Keep the source target and its
  incident active while `source_stop_permitted=false`; an accepted tracker,
  handoff packet, created task, mission binding, or acknowledgement is not a
  substitute for current first-Block start evidence. If direct task-creation
  authority is unavailable, preserve that boundary as an open transition—do
  not invent authority, manufacture a successor ID, falsely close the source,
  or turn the internal orchestration obligation into routine human scheduling.
  Reuse the current task by default through `same-task-new-run`; require an
  exact, unconditional direct request or an independently accepted
  technical-isolation decision for `distinct-task`; conditional, optional,
  contradictory, or merely caller-described topology prose is not authority.
  Reject self-successors. If the premise changes, preserve history and
  append only `corrected`, `cancelled`, bounded `expired`, or `superseded` from
  reviewed direct authority. A `work-started` record whose first-action
  currentness fails at its write boundary may advance only to an exact
  `corrected` disposition, preserving the stale start while preventing the
  gate from continuing it. A replacement is inactive until its predecessor
  carries the exact supersession link, and no retired transition closes the
  governing outcome.
- Preserve the implementation owner's canonical direct requested-range
  binding. A routed steer, reviewer Stop, task/run/group boundary, transition,
  handoff, commit, push, or accepted checkpoint may constrain its own operation
  but cannot narrow or cancel that range. Before any terminal lifecycle, call
  `implementation-range-gate`. If it reports remaining Blocks or a noncurrent
  governing outcome, classify a return as the critical
  `FM-UNAUTHORIZED-EARLY-RETURN` failure, reject terminalization, and require
  its immediate dependency-safe `next_action`. An absent or noncurrent range
  binding also returns a structured nonterminal verdict: keep the target
  `in-progress`, continue the local safe frontier, and repair the binding with
  no manual Resume or ordinary human scheduling. Block, commit, review,
  handoff, push, and final-response boundaries never imply completion. A Block
  Stop inside a full-tracker request is an audit checkpoint, never a user-return
  boundary.
- At admission, distinguish an unbound internal packet from a canonical
  delegated-authority envelope. The former cannot create scope. The latter
  preserves exact originating user bytes, current mission/policy, the canonical
  current pending mission-activation source, owner-produced target-action route
  result/projection, and independent acceptance; ingest and
  receipt it through the existing owner, bind the full tracker, and start its
  first safe Block automatically. No same-thread repetition or manual Resume is
  permitted.
- Treat the content-minimized `control_posture_replay_v1.json` fixture and its
  finite state matrix as the demonstrated convergence baseline for this failure
  family. Replay it through the public `control-posture-gate`: an open or
  acknowledged transition remains active; routed authority cannot create a
  stop; direct correction can retire the stale transition and resume same-task
  work; invalid terminal claims reconcile; and only exact current direct-stop
  or observable-completion proof becomes terminal. Preserve one posture, no
  self-successor, no terminal handoff inference, and no human scheduling leak.
  The fixture is regression evidence, not a second ledger, private incident
  transcript, or proof that later adaptive/evolution Blocks are implemented.
- Before accepting `completed`, `paused`, or `stopped` after a same-target
  mission succession, require its derived mission activation to reach
  `work-started`. Use only exact later target evidence bound to the active
  mission and first-work identity; keep the current target `in-progress` while
  pending. Do not substitute the separate successor-task transition, create a
  new task, or request manual Resume.
- Characterize a material recurrence with the record command's
  `--failure-mode` envelope: stable failure-mode ID, layer, mechanism, trigger,
  observed effect, detection rule, bounded correction, recurrence invariant,
  and whether it leaked scheduling to the human. Attach the envelope to the
  existing incident-owned event; do not create a second failure ledger.
- Before accepting an explicit stopped posture, apply the bound meta-charter's
  valid-stop conditions. If none applies, classify the goal-preventing stop as
  critical, keep supervision active, and route the narrow resume-or-establish-
  valid-stop challenge. Do not call an authorized pause or completed stop
  catastrophic merely because execution is no longer active.
- A nonempty safe-work frontier makes a blocked posture invalid. After the timed
  protocol, missing facts and reserved actions use safe deferral; a full stop is
  permitted only when that deferral still leaves the declared terminal outcome
  impossible and the exact safe frontier is empty.
- The necessity review asks what new fact, preference, reserved judgment, or
  authority the user response contributes. If it adds none and only repeats the
  system's sole eligible reviewed recommendation, classify the stop as
  procedural, issue a current-run correction, and require narrow continuation.
- Resume only after revalidating the target, active mission, current policy and
  history, exact paused lifecycle, one distinct current watcher/Sol XHigh
  semantic-check record and state fingerprint, and every bound automation ID.
  Re-run `bind` with the existing
  exact IDs first when a legacy group needs current non-privileged defaults;
  then record a new current `no-intervention` check with exact target evidence
  under that resulting policy. A notification, task event, Max/meta sample, or
  empty/caller-shaped record is not eligible resume source evidence.
- Call `resume-gate` with that pause/source/fingerprint tuple before changing an
  automation. It reads only the policy-bound automation owners, verifies each
  owner-derived target and RRULE, and returns the exact paused IDs plus one
  eligibility root. Missing, duplicate, stale, malformed, differently targeted,
  differently scheduled, or partially configured owners fail closed.
- Enable only the returned IDs through the maintained Codex automation owner;
  never write `automation.toml`. Call `resume-finalize` with the unchanged
  eligibility root only after a fresh gate reports every exact bound owner
  `ACTIVE`. The finalizer rechecks policy/event/source currentness and the named
  owners under one append lock, then appends at most one hash-chained lifecycle
  record with category `supervision-resume` and status `resumed`.
- A task/thread resume, turn start, caller assertion, or active automation by
  itself is not semantic supervision resume. Refresh role and heartbeat prompts
  before the first target check only after the canonical resumed record exists.
  Exact duplicate finalization is idempotent; changed replay stays rejected and
  the prior paused record remains immutable history.
- On stop, pause or delete the applicable automations as requested. Preserve the local
  supervision ledger unless the user explicitly asks to delete it.

## Boundaries

- Supervisors are read-only except for their dedicated supervision log root and
  concise thread steering messages. The fix executor has the additional narrow
  supervisor-maintenance permission described above, plus reviewed edits to the
  exact three-skill allowlist only when the target policy explicitly enables
  that mode.
- Do not edit repositories, patent workspaces, trackers, tests, configuration,
  or patent content from a supervisor thread.
- Do not run the target's commands or tests, create subagents, broaden scope, or
  replace the tracker's required independent audit.
- Cross-thread communication is action routing, not progress broadcasting. A
  bounded packet identifies the recipient's required action and must pass
  `thread-route-gate`; routine evidence and outcomes remain in the target thread
  or their helper-approved email lane. The gate is read-only and must not become
  another message ledger or authorization system. A critical correction or
  handled report must pass the record-first incident-head check described above.
- Scheduled inactivity consumes no model tokens; each wake must remain bounded.
- Supervision evidence is operational evidence, not patent authority, legal
  status, or proof of patent quality.
- A monitored target needs no integrated alignment implementation. The
  supervisor's independent mission charter is governing; any target-native
  alignment is an advisory read-only attestation. Do not import a target
  alignment module, require its schema, or write through its owner merely to
  supervise that target.
- Gmail notification is self-delivery only. The dedicated priority lifecycle
  thread and separate roundup thread are the only additional project threads;
  neither is a second incident, status, or monitoring authority. Gmail is an
  operational alert surface, never a substitute for the append-only ledger.
  Ordinary alerts remain free of patent content, local paths, prompts,
  credentials, or copied tool output. An explicitly enabled user-decision
  priority brief may include only the minimum substantive context required to
  decide; it must not copy full patent prose or place that context in the
  supervision ledger.
