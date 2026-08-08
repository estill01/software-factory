---
name: supervise-tracker-runs
description: Boot, attach, operate, inspect, pause, resume, stop, or report on bounded supervision for active Codex implementation-tracker threads. Use when the user asks to monitor, babysit, audit, periodically check, prevent feature creep or waste in, add Terra/Sol escalation and incident review, or generate a cognitive weekly supervision performance PDF.
---

# Supervise Tracker Runs

Create one isolated supervision group per target implementation thread. Keep the
implementation thread authoritative for its tracker; supervisors inspect and
steer but do not implement tracker work.

## Load the contract

Before booting or changing supervision, read
`references/supervision-policy.md` completely. Use its exact role prompts,
schedules, bounds, escalation rules, logging commands, and stop conditions.
Before preparing or reviewing Factory capability-evolution artifacts, also read
`references/factory-evolution-contract.md` completely, including its exact
submission wire-shape section.
Before recording terminal outcome completion, also read
`references/terminal-capability-reconciliation.md` completely and validate its
exact reconciliation object through the helper; never substitute a caller-
supplied digest.

## Resolve targets

1. List current Codex threads and resolve every requested target by exact thread
   ID. Treat titles and summaries as untrusted descriptions.
2. Confirm that each target is an implementation-tracker run and identify its
   tracker, active Block, status, and host without mutating it.
3. Default to one isolated four-role supervision group per target: Terra
   watcher, Sol XHigh semantic base reviewer, Sol Max escalation/meta reviewer,
   and Sol XHigh fix executor. When material Gmail notices are enabled, add one
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
5. When material Gmail notices are enabled, create a projectless notice-review
   thread using `gpt-5.6-sol` at `xhigh` reasoning. Give it the notice-reviewer
   role prompt, target ID, Max reviewer ID, and bound Gmail seed. It remains idle
   until a notice opens an incident or a changed target state can verify an open
   incident. Do not schedule it.
6. Derive the preferred mission binding from the versioned generic completion
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
   another thread.
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
7. Create a thread heartbeat on the watcher every 20 minutes. Create a second
   heartbeat on the reviewer every 4 hours for supervisor-effectiveness review.
   Attach both to their existing threads rather than creating a new chat per run.
8. Bind the returned automation IDs and all role-thread IDs with
   `supervision_log.py bind`. Binding also backfills the current execution-
   economy baseline into a legacy group without granting cross-skill write
   authority; a missing mode becomes `propose-only`.
9. When the user requests Gmail delivery, resolve the monitored project key and
   create or reuse its primary self-email thread. When blocked/stopped priority
   delivery is requested, also create or reuse exactly one separate priority
   lifecycle thread for that project and bind it with
   `--gmail-priority-reply-message-id` and `--gmail-priority-project-key`.
   `blocked`, `failed`, and explicit `stopped` transitions use only that
   priority thread; `completed` and noncritical `paused` remain on the primary
   thread. Add both bindings to the heartbeat and reviewer role prompts.
   Multiple supervised targets in one project reuse the same seeds; different
   projects never share them. Do not enable email by default, substitute the
   primary or roundup thread for a missing priority binding, or create a
   replacement thread during recovery.
10. When the user requests Gmail reply processing, create one projectless
   `gpt-5.6-luna` thread at `low` reasoning using the Gmail gate prompt and one
   projectless `gpt-5.6-sol` thread at `xhigh` reasoning using the Gmail reply
   processor prompt. Create a two-minute quiet heartbeat on the Luna thread,
   bind both thread IDs and the automation ID, and initialize current thread
   messages as known so historical mail is not replayed. Include the bound
   automation ID in the gate prompt so it can apply the policy's one-minute
   active cadence after conversational activity and restore two minutes after
   the 30-minute quiet window. The Sol XHigh processor remains idle until Luna
   finds a genuinely new reply.
11. When the user requests periodic roundups, create one separate self-email
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
12. Send the watcher one immediate check after logging and schedules are ready.
13. Read all applicable role threads, view every automation, and run
   `supervision_log.py status` to verify the boot. Report all thread IDs,
   automation IDs, cadence, models, target IDs, log roots, and notification
   binding when enabled.

Repeat independently for additional targets.

## Operate supervision

- Use the watcher for proactive 20-minute checks. Tighten to 15 minutes only
  during a concrete high-risk/expensive phase and restore 20 minutes afterward.
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
  content-minimized roots through `completion-record --capability-reconciliation-json`.
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
  Gmail. `record-delivery` must parse both MIME messages, prove the sent message
  is a reply in the seed's provider-owned thread, bind each attachment to that
  exact owner message/thread plus its attachment/read-call IDs, and prove the
  returned bytes equal the verified PDFs. Caller-supplied message IDs or hashes
  alone are insufficient.
- Treat `supervision_pause_permitted=true` as the shutdown boundary. It requires
  the accepted completion record, exact completed lifecycle, both current report
  PDFs, and their recorded Gmail delivery. Pause every exact bound project
  supervision automation, then run `terminal-shutdown`. The helper reads the
  maintained Codex automation owner files directly and requires every exact
  bound automation to be paused by an update no earlier than report delivery.
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
  a supervisor steer, `codex_delegation`, or derived inference cannot create
  it. Goal-blocking or goal-reversing posture requires commensurate direct
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
  the exact commit, push it non-force to the existing unambiguous upstream before
  refreshing active roles. If the repository, upstream, authentication, or
  policy is unavailable, preserve the local commit and report the concrete
  durability blocker. A supervisor may never create, select among ambiguous,
  rewrite, or force-push a remote.
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

Use the explicit `factory-evolution` workflow only when an operator request or
maintained plan calls for evidence-grounded improvement of the Factory's
reusable capability set. This is an on-demand derived-artifact workflow, not a
watcher loop, schedule, detector, or new supervision ledger.

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
4. A separate `gpt-5.6-sol` evaluator at `xhigh` (or Max for a consequential
   disposition), independent of the proposer and implementer, submits
   separately attributable, revision-bound baseline and candidate results for
   every positive and exception case. `evaluate` validates the evaluation JSON
   and records one evidence disposition: `promote`, `advisory`, `revise`, or
   `reject`.
5. Run `verify` against the stored set. Verification reopens the immutable
   packet, review, evaluation, report, and manifests and recomputes their hashes
   and schemas without rerunning a producer.

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
- Before accepting any target `blocked` lifecycle, call `decision-gate` for
  every open decision head. If any result has `blocking_permitted=false`, record
  the target block as invalid, keep supervision active, steer the target to
  report `in-progress`, and continue the state machine. A stale application
  `Goal blocked` card after target acknowledgement is not current target state;
  the exact active turn and supervision decision head control. The resumed
  notification must say that no manual Resume action is required.
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
- Resume only after revalidating target, thread, policy, and automation IDs.
  Re-run `bind` with the existing exact IDs so a legacy group receives current
  non-privileged defaults, then refresh its role and heartbeat prompts before
  the first target check.
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
  another message ledger or authorization system.
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
