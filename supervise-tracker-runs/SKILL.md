---
name: supervise-tracker-runs
description: Boot, attach, operate, inspect, pause, resume, or stop bounded supervision for one or more active Codex implementation-tracker threads. Use when the user asks to monitor, babysit, audit, periodically check, prevent feature creep or waste in, or add Terra/Sol escalation and incident review to tracker-driven implementation runs.
---

# Supervise Tracker Runs

Create one isolated supervision group per target implementation thread. Keep the
implementation thread authoritative for its tracker; supervisors inspect and
steer but do not implement tracker work.

## Load the contract

Before booting or changing supervision, read
`references/supervision-policy.md` completely. Use its exact role prompts,
schedules, bounds, escalation rules, logging commands, and stop conditions.

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
6. Initialize the target's local supervision state with:

   ```bash
   python3 scripts/supervision_log.py init \
     --target-thread <target-thread-id> \
     --target-label <short-label> \
     --watcher-thread <watcher-thread-id> \
     --reviewer-thread <reviewer-thread-id> \
     --base-reviewer-thread <base-reviewer-thread-id> \
     --notice-reviewer-thread <notice-reviewer-thread-id> \
     --fix-executor-thread <fix-executor-thread-id>
   ```

   Resolve `scripts/supervision_log.py` to its absolute path when using it from
   another thread.
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
  material incidents and effectiveness reviews.
- Keep decision timing and continuation evidence in the same JSONL ledger:
  classification, decision-ready/deadline times, attempt number, packet hash,
  blocked-scope hash, safe-frontier hash/posture, disposition, handoff, and
  target acknowledgement. Do not add a decision ledger or copy substantive
  packet content into supervision records.
- Use only `scripts/supervision_log.py` for supervisor filesystem writes. Never
  place patent prose, project paths, credentials, prompts, or copied tool output
  in supervision records.
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
  posture, and source record IDs. Keep patent content and copied output out.

## Pause, resume, or stop

- Pause all project supervision automations when the target completes, becomes
  genuinely inactive after the decision protocol and safe-frontier check, or the
  user requests a pause. Do not pause merely because a material decision awaits
  user input; the watcher must continue the timed resolution protocol and verify
  safe-frontier progress.
- Before pausing supervision for a blocked, failed, or explicitly stopped
  target, ensure its deduplicated priority-thread lifecycle email was sent.
  Before pausing for a completed or noncritical paused target, ensure its
  ordinary lifecycle-status email was sent to the primary project thread.
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
- Gmail notification is self-delivery only. The dedicated priority lifecycle
  thread and separate roundup thread are the only additional project threads;
  neither is a second incident, status, or monitoring authority. Gmail is an
  operational alert surface, never a substitute for the append-only ledger.
  Ordinary alerts remain free of patent content, local paths, prompts,
  credentials, or copied tool output. An explicitly enabled user-decision
  priority brief may include only the minimum substantive context required to
  decide; it must not copy full patent prose or place that context in the
  supervision ledger.
