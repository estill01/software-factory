# Software Factory Tracker-Authoring Supervision Implementation Tracker

- Tracker status: `superseded`
- Tracker sequence: Blocks 0–4
- Repository: `https://github.com/estill01/software-factory`
- Planning baseline: `123eb3880db8462342e876218c4d89c8110879fb`
- Governing objective: `Extend the existing independent supervision plane so it can supervise consequential implementation-tracker authoring, independently challenge whether the proposed capabilities and Blocks form a good implementation program, and accept authoring only when the resulting tracker is repository-grounded and implementation-ready.`

> Superseded planning history: direct-user amendment
> `direct-user-019ff991-authoring-supervision-merge-annotation-1` merged every
> still-valid Block 0–4 capability into future Blocks 5, 7, 10, and 11 of
> `docs/software-factory-recursive-product-program-evolution-implementation-tracker.md`.
> The exact old-to-new capability map in that tracker preserves independent
> operation for consequential user-seeded authoring, one-shot review for routine
> authoring, sole tracker writing by `author-implementation-trackers`, and
> canonical review/event/lifecycle ownership by `supervise-tracker-runs`. This
> document remains unchanged below as historical design evidence; none of its
> unimplemented Blocks is claimed accepted.

## 1. Purpose and intended outcome

Add a first-class tracker-authoring target profile to the existing supervision
system. The profile must supervise the authoring thread without taking over its
writer role, independently compare the proposed program with the direct mission
and live repository, and catch both under-scoped and overbuilt trackers before
implementation begins.

This is not a second tracker formatter. Structural verification remains
necessary but insufficient. The supervised outcome is a substantively sound
implementation program: the right necessary capabilities are pursued, missing
goal-critical work is surfaced, unsupported features are removed or deferred,
existing architectural owners are reused, Blocks are causal and single-focused,
and acceptance evidence would prove the intended behavior.

Completion means:

- `supervise-tracker-runs` can bind either an existing implementation run or a
  tracker-authoring run through an explicit, backward-compatible target kind;
- an independent semantic reviewer can inspect the direct objective, current
  tracker candidate, and bounded live-repository evidence rather than relying
  on the author's explanation;
- changed authoring state is reviewed for program quality, feature selection,
  owner reuse, Block decomposition, priority, dependencies, acceptance, and
  stopping boundaries;
- supported defects produce one narrow target-owned revision request and stay
  open until a later tracker delta establishes the correction;
- authoring completion requires a current full verifier result plus independent
  implementation-readiness proof bound to the exact tracker and repository
  revisions; and
- ordinary implementation-run supervision retains its existing behavior and
  legacy policies remain readable.

### Mission frame

- Primary outcome: consequential implementation trackers receive independent,
  repository-grounded challenge of what should be built and how it should be
  decomposed before implementation consumes the plan.
- Observable completion: a `tracker-authoring` target can be booted, monitored,
  corrected, and closed through the existing supervision owner; paired
  underreach, overreach, and sound-plan cases demonstrate that semantic review
  distinguishes program quality from document structure; and existing
  implementation supervision tests remain green.
- Ordinary effect classes needed: target-kind binding, backward-compatible
  policy validation, authoring-specific changed-state review, bounded read-only
  repository inspection, checkpoint and intervention routing, exact completion
  proof, lifecycle shutdown, tests, documentation, and independent review.
- Hard direct authority or safety boundaries: the authoring thread remains the
  sole tracker writer; supervisors remain read-only outside canonical
  supervision state and bounded thread steering; the direct mission and live
  repository govern; no target implementation, product decision reversal,
  external release, Gmail enablement, skill self-promotion, or new canonical
  ledger is authorized.
- Material goal alteration or reversal: creating a fourth skill, allowing a
  supervisor to edit the tracker or implement its Blocks, replacing the
  maintained tracker verifier with model judgment, adding a general workflow
  engine, or making supervision mandatory for every small tracker requires a
  later tracker or renewed direct authority.

## 2. Target architecture and authority boundaries

```text
direct objective + repository authority + current repository revision
                              |
                              v
             tracker-authoring thread (sole writer)
                              |
                    materially changed state
                              |
                              v
              existing mechanical watcher gate
                              |
                              v
       independent authoring semantic review (read-only)
          | mission and feature-program challenge
          | repository-owner and architecture challenge
          | Block graph and acceptance challenge
          v
       existing Sol Max escalation/checkpoint decision
          | no finding -> evidence-bound check
          | finding -> one narrow steer to authoring thread
          v
             later candidate delta proves correction
                              |
                              v
   full verifier + implementation-readiness completion record
                              |
                              v
             profile-aware lifecycle shutdown
```

Authority rules:

1. The direct user/system/repository mission remains the governing source.
2. The authoring thread owns every tracker edit, verifier run, Git checkpoint,
   and final authoring report.
3. Terra remains a mechanical change gate and cannot select evidence, judge
   features, or declare the plan good.
4. Sol XHigh independently reads the cited tracker delta and the smallest
   necessary live-repository sources. It does not rely on the author's summary
   as proof and does not mutate or run implementation work.
5. Sol Max owns supported intervention, checkpoint, and genuine trade-off
   decisions. It may steer the authoring thread but cannot write the tracker.
6. `supervision_log.py` remains the only public canonical supervision writer.
   Existing event, incident, escalation, steer, checkpoint-review, resolution,
   lifecycle, and completion records are reused.
7. `verify_tracker.py` remains the structural verifier. Semantic supervision
   neither replaces it nor treats a green verifier as implementation-readiness
   proof.
8. An accepted target-product capability frame from the existing evolution
   tracker may become direct review input. Until then, the reviewer uses the
   current direct mission and repository evidence and does not duplicate or
   pre-approve that unfinished feature.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Tracker authoring, quality criteria, and final authoring handoff | `author-implementation-trackers/SKILL.md` and its references/template | reuse |
| Structural tracker verification | `author-implementation-trackers/scripts/verify_tracker.py` | reuse |
| Supervision target policy, canonical events, routing, completion, and lifecycle | `supervise-tracker-runs/scripts/supervision_log.py` | adapt |
| Target resolution, boot, operation, and role topology | `supervise-tracker-runs/SKILL.md` | adapt |
| Semantic review, checkpoint, intervention, and shutdown contracts | `supervise-tracker-runs/references/supervision-policy.md` | adapt |
| Supervision policy and helper regression coverage | `supervise-tracker-runs/scripts/test_supervision_log.py` | adapt |
| Public system description and invocation guidance | `README.md` and `supervise-tracker-runs/agents/openai.yaml` | adapt after proof |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| Current repository and implementation-run supervisor | `123eb3880db8462342e876218c4d89c8110879fb` | adapt | 0–4 | Generalize the target contract without weakening implementation supervision |
| Current authoring feature-creep and Block-quality rules | planning-baseline authoring skill hash | reuse | 0, 2, 4 | Make their application independently reviewable rather than self-attested |
| Current generic mission binding and changed-state routing | planning-baseline helper/policy hash | adapt | 1–3 | Bind an explicit target kind and authoring completion semantics |
| `docs/software-factory-learning-and-capability-evolution-mvp-implementation-tracker.md`, especially planned Block 4 | planning-baseline document at `123eb388` | reuse-if-accepted; do not duplicate | 0, 2, 4 | Consume an accepted target-product frame when available while remaining valid against direct mission/repository sources |
| Current one-shot authoring `quality-check` mode | planning-baseline authoring skill | reuse | 4 | Keep as the economical default for ordinary trackers; document continuous supervision for consequential authoring |

## 5. Scope, non-goals, and proportionality

### In scope

- An explicit `tracker-authoring` target kind alongside the existing
  implementation-run default.
- Independent review of program/feature selection and Block quality.
- Bounded read-only inspection of exact mission, tracker, repository owner, and
  architecture evidence needed for the changed authoring state.
- Authoring-specific checkpoints, narrow target-owned correction, later
  effectiveness review, and implementation-readiness completion.
- Backward-compatible helper/policy behavior, focused tests, paired semantic
  forward tests, and demonstrated documentation.

### Out of scope

- A fourth Software Factory skill or separate supervision service.
- Automatic product strategy, feature ideation unconstrained by the mission, or
  supervisor preference as authority.
- Supervisor edits to trackers, repository implementation, or execution of any
  proposed Block.
- A new event ledger, incident system, task graph, scoring system, dashboard,
  scheduler, or model router.
- Making four-role continuous supervision the default for every routine or
  low-consequence tracker.
- Reimplementing the planned target-product capability frame owned by the
  separate evolution tracker.
- Generalizing terminal PDF/report machinery merely to close shorter authoring
  runs.

### Proportionality

Reuse the existing four-role supervision topology, canonical events, routing
gate, incidents, and completion record. Add only the target-profile distinction
and authoring-specific semantic contract required to interpret those owners
correctly. Ordinary trackers may continue to use a one-shot independent
`quality-check`; continuous supervision is for consequential, long-running, or
otherwise high-risk authoring.

## 6. Block execution contract

1. Execute Blocks 0–4 in dependency order and audit each Block before
   advancing.
2. Re-read the active Block and inspect the current helper, policy, prompts,
   authoring rules, tests, and Git state before editing.
3. Preserve `implementation-run` as the default target kind and retain readable
   legacy policy/event state.
4. Reuse the existing supervision writer, role topology, event kinds, routing
   gate, and completion-record roots unless a focused failing test establishes
   that one cannot express the authoring invariant.
5. Keep the authoring thread the sole tracker writer. Supervisor work is
   observation, independent review, bounded steering, and later proof only.
6. Separate mechanical changed-state detection, semantic program review, Sol
   Max intervention, and exact completion proof.
7. Test underreach, unsupported overreach, and a proportionate sound program;
   do not encode one project-specific preferred answer as the general rubric.
8. Finish likely-mutating review before final mapped validation. Freeze the
   exact candidate revision and rerun only affected proof after remediation.
9. Commit and push each accepted Block when the configured remote remains
   available. Preserve rejected candidates and successor correction evidence.
10. Stop at every Block boundary rather than implementing adjacent execution,
    reporting, or capability-evolution work.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
- Inputs: `<paths, IDs, revisions, and hashes>`
- Outputs: `<paths, policy/profile roots, fixtures, and hashes>`
- Focused validation: `<commands and results>`
- Mapped validation: `<plan, commands, and results>`
- Candidate freeze: `<commit/content root and whether it changed afterward>`
- Authoring-profile compatibility: `<legacy and implementation-run proof>`
- Program-quality cases: `<underreach, overreach, sound-plan results>`
- Resource posture: `<bounded reads/tests and any justified widening>`
- Independent review: `<review identity, findings, and exact-revision recheck>`
- Retained open work: `<items or none>`
- Post-block audit: `<accepted, reopened, or blocked with reason>`
- Git durability: `<branch, commit, and push posture>`
```

## 7. Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Freeze the authoring-supervision profile and program-quality contract | — | `not-started` |
| 1 | Bind the target kind through canonical supervision state | 0 | `not-started` |
| 2 | Operate independent program, feature, and Block review | 1 | `not-started` |
| 3 | Close authoring with implementation-readiness proof | 2 | `not-started` |
| 4 | Dogfood the profile and document demonstrated operation | 3 | `not-started` |

Required order:

`0 → 1 → 2 → 3 → 4`

## Block 0 — Freeze the authoring-supervision profile and program-quality contract

Status: `not-started`

### Objective

Define the exact authoring target, semantic quality rubric, authority boundary,
and compatibility posture before changing canonical supervision behavior.

### Inputs and dependencies

- Planning baseline `123eb3880db8462342e876218c4d89c8110879fb`.
- Direct user objective recorded by this tracker.
- Current authoring skill, block contract, tracker template, verifier, supervisor
  skill/policy, helper, tests, and existing evolution tracker.

### Required work

- Add one maintained authoring-supervision contract under the existing
  supervision reference owner. Define `implementation-run` and
  `tracker-authoring` as distinct target kinds and preserve the former as the
  default.
- Define the reviewed authoring outcome as an implementation-ready program, not
  a structurally valid document or a completed implementation.
- Define the independent program-quality rubric:
  - mission and intended-user-effect fidelity;
  - necessary capability and feature completeness;
  - removal or deferral of unsupported features and generalized machinery;
  - existing owner and target-architecture reuse;
  - explicit alternatives, trade-offs, and proportionality;
  - Block causality, single focus, priority, dependency, and stop boundaries;
  - acceptance and negative tests that prove supported behavior; and
  - truthful open work, uncertainty, and authority decisions.
- Define evidence-bound dispositions for proposed work: `required`,
  `supported`, `defer`, `reject`, or `missing-required`. A disposition must cite
  the mission/repository basis and cannot become an aggregate score.
- Define authoring checkpoints for program proposal, owner/architecture map,
  Block graph, and final implementation-ready candidate. The semantic reviewer
  may infer a checkpoint from exact changed-state evidence; Terra may not.
- State that any later accepted target-product capability frame is reviewed as
  direct tracker input rather than duplicated by this capability.
- Add static contract tests for writer separation, semantic/mechanical
  separation, underreach and overreach coverage, and backward compatibility.

### Scope and non-goals

- In scope: semantic contract and static guardrails in the existing supervision
  owner.
- Not in scope: helper policy changes, role-prompt changes, target steering, or
  completion/lifecycle behavior.
- Do not create a product doctrine, scoring model, or separate tracker-analysis
  artifact schema.

### Deliverables and recorded state

- One concise maintained authoring-supervision contract referenced by the
  supervision policy.
- Focused static contract tests in the existing supervision test owner.

### Resource and economy contract

One bounded read of current authoring and supervision contracts. No provider
calls, target repositories, report generation, or broad corpus scans.

### QA and independent review

Mechanical tests verify required boundaries and vocabulary. A distinct
reviewer challenges whether the rubric can reject both a polished but
underpowered plan and an impressive but unsupported platform plan without
dictating one project-specific answer.

### Acceptance

- Program quality is explicitly separate from structural validity.
- Missing necessary work and unnecessary proposed work are both reviewable.
- The rubric evaluates intended capability and implementation causality without
  granting the supervisor product authority.
- Existing implementation-run supervision remains the default contract.

### Negative tests

- Reject `the full verifier passed` as sufficient implementation-readiness
  evidence.
- Reject a rubric that only detects feature creep but cannot detect strategic
  underreach or a missing goal-critical capability.
- Reject a rubric that always prefers either the smallest local patch or the
  most general architecture.

### Completion evidence

Pending.

### Stop

Stop before changing helper policy, CLI arguments, or target state.

---

## Block 1 — Bind the target kind through canonical supervision state

Status: `not-started`

### Objective

Make authoring supervision an explicit, fail-closed, backward-compatible target
profile in the existing canonical supervision policy and status flow.

### Inputs and dependencies

- Block 0.
- Current `supervision_log.py` policy, mission binding, initialization, gate,
  status, lifecycle, and test owners.

### Required work

- Add a bounded target-kind contract with `implementation-run` and
  `tracker-authoring`; use `implementation-run` when the argument or legacy
  policy field is absent.
- Add the target kind to initialization, policy hashing/history, conflict
  detection, binding/status output, and the exact boot examples consumed by the
  skill and policy.
- Preserve the current mission-source classes and generic mission binding. The
  target kind interprets the monitored outcome; it does not create authority.
- Define profile capabilities rather than a second state system:
  `tracker-authoring` permits bounded read-only repository inspection by the
  semantic reviewers, prohibits repository/tracker writes and implementation
  commands, reuses `checkpoint` when an authoring checkpoint exists, and does
  not require an `active_block` marker.
- Keep existing event kinds, incident heads, routing, deduplication, decision
  gates, and hash chaining unchanged unless a focused compatibility failure
  proves an exact adaptation necessary.
- Add focused tests for defaulting, explicit selection, invalid target kind,
  existing-policy conflict, status round-trip, policy hash currentness, and
  unchanged implementation-run gate behavior.

### Scope and non-goals

- In scope: canonical target-kind binding and profile permissions in the
  existing helper/policy state.
- Not in scope: authoring semantic prompts, tracker review, lifecycle closure,
  reports, Gmail, or a new event kind.
- Do not migrate or rewrite existing policy histories merely to add the default.

### Deliverables and recorded state

- Backward-compatible helper and policy target-kind support.
- Focused helper regression tests and updated boot-command examples.

### Resource and economy contract

Use synthetic temporary supervision roots. Run the focused helper tests first;
widen only if policy/hash compatibility failures cross another mapped test
owner. No provider calls or live supervision-state writes.

### QA and independent review

Mechanical tests cover exact policy behavior. Independent review inspects the
legacy-default path and confirms that the new profile is an interpretation of
the existing supervision owner, not a parallel authority or permission bypass.

### Acceptance

- New authoring groups bind `tracker-authoring` explicitly.
- Existing and legacy groups resolve to `implementation-run` without rewritten
  history or changed monitoring behavior.
- Invalid or conflicting target kinds fail closed.
- The status surface exposes the bound kind and permission posture.
- A blank `active_block` remains valid for an authoring changed-state gate.

### Negative tests

- Reject an unknown or changed target kind for an existing bound group.
- Reject any profile that permits tracker/repository writes from a supervisor
  role.
- Reject target-kind inference from an untrusted thread title or summary.

### Completion evidence

Pending.

### Stop

Stop before changing reviewer prompts or steering an authoring target.

---

## Block 2 — Operate independent program, feature, and Block review

Status: `not-started`

### Objective

Use the existing supervision roles to independently judge whether changed
authoring state is converging on the right implementation program and require
narrow target-owned correction when it is not.

### Inputs and dependencies

- Block 1.
- Bound `tracker-authoring` profile, direct mission root, current authoring
  contract, target thread, tracker candidate, and bounded repository sources.

### Required work

- Extend target resolution and boot instructions to recognize an authoring run,
  bind its direct mission, and preserve the same isolated watcher, base
  reviewer, Max reviewer, and fix-executor topology.
- Add profile-specific role instructions without weakening the implementation
  profile:
  - Terra reads compact state and exact newest-turn/item references, detects
    only mechanical lifecycle/emergency signals, and routes every material
    authoring delta without substantive framing.
  - Sol XHigh reads the direct objective, exact tracker delta, and the smallest
    necessary repository owners/architecture/tests. It independently applies
    the Block 0 rubric and compares the proposal with one concrete minimally
    sufficient reliable program.
  - Sol Max independently adjudicates supported findings, trade-offs,
    checkpoint transitions, and bounded target steering; deterministic samples
    are formed without first adopting XHigh's rationale.
  - The fix executor remains limited to reviewed reusable supervision
    maintenance and never edits the target tracker.
- Require program review to identify required, supported, deferred, rejected,
  and missing-required features with exact evidence, but keep optional ideas
  outside the active authoring correction.
- Require direct challenge of owner duplication, means/end inversion,
  lower-power substitution, unsupported generalized machinery, false user
  gates, missing dependent work, arbitrary Block granularity, bad priority,
  invalid acceptance, and stop-boundary overlap.
- Reuse the existing incident, escalation, route gate, steer, resolution, and
  checkpoint-review records. A steer is not resolution; later exact tracker
  evidence must show the intended correction.
- Keep the target authoring thread active while any safe authoring frontier
  remains. A genuine product preference or reserved decision follows the
  existing continuation-first decision protocol.
- Add static prompt/policy tests and bounded paired forward cases without
  embedding their intended conclusions in the reviewer input.

### Scope and non-goals

- In scope: target resolution, role prompts, semantic review, checkpoint
  handling, and correction-effectiveness review for authoring targets.
- Not in scope: tracker edits, proposed-Block implementation, new roles,
  automatic feature generation, or authoring completion shutdown.
- Do not turn every optional improvement into a finding or widen from one
  supported defect into a generalized tracker rewrite.

### Deliverables and recorded state

- Updated supervision skill/policy authoring operating path and role prompts.
- Focused static tests and content-minimized authoring review fixtures.
- Evidence-bound checks, incidents, escalations, steers, checkpoint reviews,
  and resolutions using the existing canonical event format.

### Resource and economy contract

Terra remains compact. XHigh reads the exact delta first and widens only to the
direct mission, current tracker sections, and repository owners necessary to
resolve the changed-state question. Reuse a current repository/tracker root
within one review. Do not run implementation tests, broad scans, renders,
provider work, or per-Block repeated whole-repository analysis.

### QA and independent review

Static tests preserve role separation and target-owned writing. Blind paired
cases must cover a structurally green under-scoped tracker, a structurally green
overbuilt tracker, and a proportionate tracker whose local solution should not
be rejected for lacking hypothetical generality. Sol Max independently reviews
the raw cases and exact candidate prompts.

### Acceptance

- XHigh can discover a supported authoring defect absent from Terra's packet.
- A green structural verifier cannot suppress a supported program-quality
  finding.
- Underreach and overreach are both detected from direct evidence.
- A sound proportionate plan receives no intervention.
- Every correction is narrow, target-owned, evidence-bound, and kept open until
  a later delta proves effectiveness.

### Negative tests

- Reject Terra selecting features, evidence, or a semantic conclusion.
- Reject the author summary or tracker prose as sufficient evidence of owner
  reuse, product need, or acceptance quality.
- Reject a supervisor that edits the tracker, implements a proposed Block, or
  certifies its own steer as resolution.
- Reject project-specific wording promoted into the general reviewer rubric.

### Completion evidence

Pending.

### Stop

Stop before accepting final tracker completion or pausing supervision.

---

## Block 3 — Close authoring with implementation-readiness proof

Status: `not-started`

### Objective

Accept and shut down an authoring supervision run only when the exact current
tracker is structurally valid, substantively implementation-ready, and
independently reconciled with its mission and repository.

### Inputs and dependencies

- Block 2.
- Current full-profile tracker verifier, authoring final-handoff contract,
  existing completion-record roots, lifecycle gate, and automation shutdown
  owner.

### Required work

- Define the authoring completion trigger from an explicit final target posture
  and exact tracker candidate; intermediate `planning`, draft, or checkpoint
  language must not trigger shutdown.
- Reuse the existing completion record and map its five exact roots for
  `tracker-authoring`:
  - outcome manifest: mission, tracker identity, proposed capabilities, Blocks,
    and verification matrix;
  - artifact currentness: exact tracker content and inspected repository
    revision;
  - effect reconciliation: required/supported/deferred/rejected/missing-required
    program review and Block coverage;
  - open-item compatibility: retained uncertainty and deferred work do not
    prevent the primary implementation outcome; and
  - independent challenge: distinct reviewer evidence at the frozen candidate.
- Require a current full-profile verifier result, final diff review, dependency
  and stop-boundary review, and confirmation that tracker authoring did not
  implement a Block.
- Fail completion and keep supervision active when required features are
  missing, unsupported features remain required, owners are duplicated,
  acceptance would prove only process, an open item prevents the mission, or
  the independent review is stale.
- Make lifecycle messages profile-aware and avoid implementation-only labels for
  an authoring target.
- Use a proportionate authoring shutdown path: when terminal report generation
  is disabled by the authoring profile, require verified completion, no open
  material incident/decision, viewed paused automations, and an owner-backed
  shutdown receipt without manufacturing implementation PDFs. Preserve the
  existing implementation-run report and shutdown contract unchanged.
- Add focused tests for stale roots, missing verifier evidence, failed semantic
  reconciliation, open findings, profile-aware lifecycle, reportless authoring
  shutdown, and unchanged implementation-run terminal behavior.

### Scope and non-goals

- In scope: authoring completion proof, lifecycle semantics, and proportionate
  shutdown through existing canonical owners.
- Not in scope: implementation acceptance, terminal implementation reports,
  Gmail enablement, tracker publication, or execution of Block 0.
- Do not weaken the implementation-run observable-outcome completion gate to
  accommodate authoring.

### Deliverables and recorded state

- Profile-aware completion/lifecycle/shutdown policy and helper behavior.
- Focused completion, compatibility, and lifecycle tests.
- One canonical verified authoring completion record and shutdown receipt shape.

### Resource and economy contract

Reuse the frozen tracker/repository roots and current verifier result. Perform
one final semantic reconciliation after mutating review is complete. Rerun only
affected proof after correction. Do not generate weekly or terminal PDFs for
the authoring profile merely to satisfy the implementation profile's reporting
shape.

### QA and independent review

Mechanical tests verify exact roots, lifecycle ordering, and compatibility.
The final semantic reviewer must be distinct from the tracker author and read
the direct objective, exact tracker candidate, bounded live owners, verifier
result, and open findings before viewing the completion narrative.

### Acceptance

- A structurally green but substantively weak tracker cannot complete.
- A substantively sound tracker with stale structural or repository proof
  cannot complete.
- The authoring run closes only at the exact independently reviewed candidate.
- Reportless authoring shutdown cannot bypass completion or open-incident gates.
- Implementation-run completion, reports, lifecycle, and shutdown remain
  unchanged.

### Negative tests

- Reject completion from tests, a commit, a green verifier, or the author's
  self-attestation alone.
- Reject completion when the tracker omits a mission-critical feature or
  requires unsupported generalized machinery.
- Reject a completion record bound to an earlier tracker or repository root.
- Reject using the authoring profile to evade implementation terminal reports.

### Completion evidence

Pending.

### Stop

Stop before dogfooding the workflow, editing public documentation, or beginning
tracker implementation.

---

## Block 4 — Dogfood the profile and document demonstrated operation

Status: `not-started`

### Objective

Demonstrate at one frozen revision that authoring supervision improves tracker
program quality without oversteering a sound plan or regressing existing
implementation supervision.

### Inputs and dependencies

- Block 3.
- Frozen authoring-supervision candidate, direct contract, focused fixtures,
  all three installed skill owners, and this implementation tracker.

### Required work

- Run focused helper/policy tests, the full supervision mapped suite, all three
  skill validators, and the full tracker verifier against affected trackers.
- Forward-test the authoring profile with distinct author/reviewer identities on
  bounded cases:
  - a structurally valid tracker that omits a necessary user-visible capability;
  - a structurally valid tracker that introduces unsupported generalized
    infrastructure;
  - a structurally valid tracker with poor Block causality, priority, or
    acceptance evidence; and
  - a proportionate implementation-ready tracker that should close without
    intervention.
- Dogfood one full authoring supervision lifecycle through boot, changed-state
  review, at least one supported-or-explicitly-no-finding checkpoint,
  completion review, lifecycle gate, automation pause, and shutdown receipt.
  Use synthetic/content-minimized evidence and do not commit external target
  content.
- Obtain an exact-candidate independent review that reads the direct objective,
  raw cases, current repository diff, and compatibility evidence before the
  implementation narrative.
- Correct supported findings in successor commits and rerun only affected proof
  before one final mapped suite.
- Update `README.md`, supervisor metadata, and copyable invocation guidance only
  with behavior demonstrated by the accepted candidate. Explain when one-shot
  authoring quality-check is sufficient and when continuous supervision is
  warranted.

### Scope and non-goals

- In scope: bounded dogfood, mapped validation, independent acceptance, and
  accurate public documentation.
- Not in scope: external release, hosted operation, Gmail, additional target
  kinds, autonomous skill evolution, or implementation of any authored tracker.
- Do not claim broad product-quality improvement from synthetic cases alone;
  describe only the demonstrated authoring control behavior.

### Deliverables and recorded state

- Accepted paired-case and full-lifecycle evidence at one frozen revision.
- Updated README architecture/operating-mode guidance and supervisor metadata.
- Final tracker evidence, exact candidate commit, and independent disposition.

### Resource and economy contract

Use bounded synthetic cases and one local dogfood lifecycle. Run the full
mapped suite once after mutating review; after remediation, rerun affected
focused proof and only the mapped tests whose currentness changed. No provider
benchmark campaign, broad repository corpus, generated PDF, or external target
mutation.

### QA and independent review

The tracker author/profile implementer cannot be the sole final reviewer. The
reviewer must challenge false positives, false negatives, target-kind
compatibility, writer separation, completion integrity, and whether the cure
introduced more machinery than the demonstrated need.

### Acceptance

- The underreach, overreach, malformed-Block, and sound-plan cases receive the
  supported dispositions from direct evidence.
- One authoring run completes through the existing supervision control plane
  without supervisor writes to the tracker or implementation work.
- Existing implementation-run behavior and mapped tests remain green.
- Documentation distinguishes structural verification, one-shot independent
  quality-check, continuous authoring supervision, and implementation
  supervision.
- No unsupported performance, cost, or generalized product-quality claim is
  published.

### Negative tests

- Reject a dogfood result in which the reviewer was given the intended case
  conclusion as input.
- Reject acceptance when the sound-plan case is oversteered merely for lacking
  speculative generality.
- Reject a candidate that requires a new role topology, canonical ledger, or
  report subsystem for authoring.
- Reject documentation that implies the supervisor authored, implemented, or
  certified product behavior.

### Completion evidence

Pending.

### Stop

Stop before external release, mandatory supervision of ordinary trackers, or
implementation of a tracker produced by the dogfood run.

## 8. Verification matrix

| Capability/invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| Explicit backward-compatible authoring target kind | 1 | 2–4 | 4 |
| Program and feature selection quality review | 0 | 2–4 | 4 |
| Repository-grounded owner and architecture challenge | 0 | 2, 4 | 4 |
| Block causality, priority, dependency, acceptance, and stop review | 0 | 2–4 | 4 |
| Mechanical/semantic/Max separation | 0 | 1–4 | 4 |
| Target-owned correction and later effectiveness evidence | 2 | 3–4 | 4 |
| Exact implementation-readiness completion proof | 3 | 4 | 4 |
| Proportionate authoring lifecycle shutdown | 3 | 4 | 4 |
| Existing implementation-run compatibility | 1 | 2–4 | 4 |
| No fourth skill, new ledger, or supervisor tracker writer | 0 | 1–4 | 4 |

## 9. Final completion definition

This tracker is complete only when every Block is accepted at exact current
revisions, the `tracker-authoring` target kind operates through the existing
supervision control plane, independent review directly evaluates proposed
features and Blocks against the mission and live repository, supported defects
remain open through later correction evidence, and an exact final candidate
proves implementation-readiness without weakening implementation-run
supervision.

A green tracker verifier, completed helper tests, canonical event population,
or successful dogfood process does not alone establish completion. Terminal
proof requires the paired program-quality outcomes, current compatibility
evidence, exact-candidate independent challenge, truthful open-item posture,
and confirmation that the supervisor neither wrote the tracker nor implemented
its Blocks.
