# Software Factory evolution contract

This reference defines the minimum semantic contract for learning from bounded
tracker runs and evaluating proposed changes to Software Factory capabilities.
It does not create a new source of canonical run state and does not authorize
automatic edits, promotion, deployment, or writes into a target product.

## Authority and supported evidence

Canonical event records and directly observed outcomes are the adjudicating
evidence. Reports nominate hypotheses; they do not become authority merely
because their prose is confident or repeated. A derived learning artifact must
identify the exact, hash-bound sources from which it can be rebuilt.

Supported source classes are:

- canonical, content-minimized supervision events;
- verified run reports that point back to those events;
- tracker status and completion evidence bound to exact commits or artifacts;
- focused test, validator, audit, and user-visible outcome results; and
- explicit operator or independent-reviewer decisions recorded with provenance.

Free-form report prose, an unverified summary, model reasoning, popularity, or
the proposal's own assertions are not sufficient promotion evidence. Target
repository content must not be copied into a committed learning artifact.

## Evolution ladder

The following records remain distinct even when they are stored together:

1. **Evidence** identifies an exact source and an observable fact.
2. **Observation** describes what happened without generalizing beyond that
   evidence.
3. **Lesson** is a bounded, falsifiable interpretation supported by evidence
   and at least one stated counterexample search or uncertainty. A lesson is
   not a control and is not itself a capability.
4. **Meta-pattern** relates multiple lessons while retaining their support,
   counterexamples, scope, and uncertainty. It may represent productive
   patterns as well as harmful patterns.
5. **Capability gap** states an outcome the factory cannot reliably produce or
   protect with its present skills, references, tools, or operating contract.
6. **Capability candidate** proposes a bounded way to close a capability gap.
7. **Experiment** compares an explicit baseline with the candidate under a
   fixed evaluation contract.
8. **Disposition** records independent evaluation as `promote`, `advisory`,
   `revise`, or `reject`.

No step silently confers the authority of a later step. In particular, a
lesson does not automatically become a rule, and a candidate does not become a
capability merely by being implemented.

## Lessons and counterexamples

A lesson records its applicability boundary, supporting evidence, confidence,
known counterexamples, and the counterexample search that was attempted. One
strong instance may nominate a lesson but cannot establish broad applicability
without explaining why the instance generalizes. Repeated failures are not the
only learnable signal: productive patterns, avoided regressions, efficient
choices, and preserved composability are first-class evidence.

Conflicting observations remain visible. They narrow or defeat a lesson rather
than being discarded to produce a cleaner narrative.

## Capability candidates

The factory may propose more than detectors or controls. A candidate declares
one primary type while allowing secondary effects. Supported types include:

- authoring guidance or tracker-contract change;
- implementation or review procedure;
- supervision policy or evidence rule;
- validator, test, or verifier;
- deterministic tool or derived-artifact builder;
- reusable template, reference, or example;
- architecture, interface, or ownership-boundary change;
- integration or routing change;
- removal, simplification, or lower-power substitution;
- documentation or operator-experience improvement;
- experiment or evaluation capability; and
- detector, control, or enforcement mechanism.

Every candidate states the capability gap, proposed effect, protected
capabilities, tradeoffs, uncertainty, applicability, implementation owner, and
evaluation owner. It also states why a smaller change is insufficient and why
the proposal is not disproportionate architecture for the evidence available.
Candidate admission requires at least one exact, hash-bound supporting source
plus known counterexamples or a documented counterexample search. A single
instance may nominate a candidate, but it cannot by itself establish broad
applicability or justify promotion.

## Experiments and disposition

An experiment defines a baseline, candidate condition, representative tasks,
success and regression measures, evidence-capture method, and stop condition
before results are known. Evaluation must inspect both intended gains and lost
capabilities, including canonical-path bypass, lower-power substitution, lost
composability, and unnecessary complexity.

The proposer or candidate implementation cannot promote itself. The evaluator
must be independent of the implementation judgment being assessed and must
record evidence for one disposition:

- `promote`: the candidate demonstrated its bounded capability without an
  unacceptable regression and may enter its separately governed adoption path;
- `advisory`: evidence is useful but does not justify normative adoption;
- `revise`: the gap remains credible but the candidate or experiment must
  change before another evaluation; or
- `reject`: the candidate failed, was disproportional, or was defeated by
  counterevidence.

A disposition is review evidence, not permission for autonomous edits,
deployment, installation, or target-repository writes.

## Seed experiment: target-product alignment

Target-product alignment is the first seeded capability candidate because a
tracker can be mechanically complete while still underreaching the intended
product, bypassing a canonical architecture, replacing a more capable design
with a lower-power shortcut, or overbuilding beyond the product need. Seeding
the candidate does not pre-approve promotion. It must pass the same baseline,
counterexample, regression, proportionality, and independent-evaluation gates
as any later candidate.

## Rebuildability and state ownership

Learning packets, review records, experiments, and dispositions are derived
artifacts. Each artifact set binds its schema version, source roots, source
hashes, transformation version, and deterministic ordering. Given identical
inputs and transformation version, preparation must produce identical content
and identifiers.

The existing supervision event log remains the only public owner of canonical
supervision filesystem writes. Derived evolution artifacts may be written only
through that owner, under its bounded learning directory, using safe
identifiers and atomic immutable-or-identical writes. Deleting a derived set
does not delete or mutate canonical evidence; the set can be rebuilt from its
declared sources. Every retained JSON artifact must remain a regular file under
that owner, use the exact deterministic writer encoding, stay within the
four-megabyte stored-byte ceiling, and preserve one stable file identity through
each bounded read.

## Automatic evidence admission

Automatic admission is one deterministic checkpoint gate in the existing
supervision owner, not a cognitive reviewer, candidate runner, watcher, or new
ledger. It runs only during weekly-report finalization, terminal-report
verification, or the explicit `factory-evolution --action admit` maintenance
command. These are the weekly report finalization, terminal report verification,
and explicit Factory maintenance checkpoints.

The policy reuses `adaptive_decision_mode`. `fixed` is a zero-producer
record-only result. `recommend` may prepare one immutable recommendation packet
but cannot authorize admission. `reviewed-autonomous` and `full-autonomous` may
record one admitted cycle when the existing supervision permissions, mission,
Software Factory target, active-cycle limit, and bounded resource contract are
current. The gate does not call a model or reviewer, does not start cognitive
review, and does not create a candidate, human request, skill write, or target
write.

The gate derives two identities which must not collapse:

- the novelty identity (the canonical-evidence novelty key) hashes only sorted
  exact adjudicating event/outcome record identities and their supported
  coverage; and
- the context/currentness identity (the context root) hashes the verified
  packet, novelty key, target repository, Factory revision, mission, policy,
  and checkpoint kind for reproducibility and currentness.

Report IDs, report prose, report hashes, coverage packaging, checkpoint kind,
and Factory revision cannot create novelty. A report hypothesis nominates a
signal only when its exact evidence references resolve to canonical gap/failure
records or an exact `observable-outcome-completion` record that passes the
existing independent capability-reconciliation contract. A recurring
productive meta-pattern requires at least two such exact completion records.
A generic check, caller-selected positive category, praise, frequency, a
prose-only positive theme, and an unbound report section remain ineligible.

One target may have at most one active cycle. Repackaged or overlapping reports,
changed checkpoints, and unrelated Factory revisions return a no-op for the
same novelty key. A context change may require revalidating the existing cycle
but cannot create another cycle. After a verified terminal disposition, at
least one new adjudicating record beyond consumed coverage is required. The
eligible path writes the existing byte-identical learning packet and prepare
manifest once, then appends one content-minimized admission record through the
canonical supervision writer. Interruption may leave only those non-authoritative
prepared artifacts; they do not consume the active-cycle ceiling until an exact
admission event owns their evolution ID. Retry in the same context reuses them;
a current-context retry may prepare the same packet under its new deterministic
cycle ID and appends at most one admission.

## Existing-owner candidate orchestration

After one current `admitted` event owns a prepared packet, `status` and
`orchestrate` expose a deterministic, nonauthorizing cycle action. The stage
sequence is `review-required` → `owner-handoff-required` →
`owner-acknowledgment-required` → `evaluation-handoff-required` →
`evaluation-required` → `evaluated`, or a terminal `candidate-stopped`.
The corresponding next actions are `review`, `author`, `implement`, `compare`,
`evaluate`, or `reject`. Evaluation is read-only and nonauthorizing; adoption,
installation, and cutover remain later separately governed stages.

The first orchestration event routes the exact packet root and current
mission/policy/range/tracker/Factory revision to the policy-owned cognitive
reviewer. The finalized review retains the existing exact review schema,
counterexample floor, complete selection dimensions, one experiment, and three
distinct proposer, implementation-owner, and evaluator identities. Its
baseline revision equals the current Factory target revision.

The selected candidate type determines one normal owner through this complete
map; prose and detector-first routing cannot override it:

- `correction`, `detector`, `exculpator`, `resource-policy`, and `supervision`
  route to `supervise-tracker-runs`;
- `architecture`, `evaluation`, `execution`, `experiment`, `removal`, and
  `skill-method` route to `implement-tracker-blocks`; and
- `tracker-method` routes to `author-implementation-trackers`.

The owner handoff binds the admitted packet and review roots, selected
candidate and experiment roots, exact target repository/revision, current
mission and policy, active implementation-range head and tracker hash,
capability-frame root, all three skill tree roots, full candidate budget,
protected capabilities, role identities, and incumbent production authority.
Unknown types, an incomplete map, stale roots, an implementation-owner claim
that differs from the mapped owner, or a later candidate outside that owner's
bounded source scope rejects before any acknowledgment.

`acknowledge --owner-ack-json` accepts one exact canonical JSON object with
these keys:

`schema_version`, `kind`, `owner_handoff_record_id`,
`owner_handoff_orchestration_root`, `owner_handoff_record_sha256`,
`handoff_root`, `target_revision`, `candidate_revision`, and
`protected_capability_test_paths`. Use JSON integer `1` and
`software-factory-evolution-owner-acknowledgment-input` as `kind`.

The protected-capability map has every exact derived capability ID once and
maps each to a distinct changed test named for that ID. The candidate must be
the one direct non-current child of the exact incumbent.
Its commit message binds the canonical owner-handoff record ID, orchestration
root, and record SHA-256, and its complete diff remains inside the mapped
owner's scope. Each mapped focused test path is a changed regular Python test
file in that same scope. The supervision owner—not the input JSON—executes
those exact tests from a bounded archive of the candidate revision and records
runtime, argv, chronology, exit status, timeout posture, and output hashes.
One aggregate deadline runs from the canonical handoff timestamp; each next
test receives only the remaining time and execution stops at the first failed
or exhausted command. It then derives separately attributable validation,
protected-capability, resource, owner-proof, and Stop roots.
Submitted exit codes, output hashes, protected postures, timestamps, owner
names, or Stop labels are not accepted. A failed executed validation or
resource ceiling returns a terminal stopped posture; only a current isolated
candidate created after its exact owner handoff and within every ceiling
returns `compare`.

Review handoff, owner handoff, and owner acknowledgment use the existing
mission-scoped canonical supervision event log. Each stage is immutable,
idempotent on retry, and rehydrated from exact packet/artifact/repository state;
duplicate delivery cannot create another review, owner handoff, candidate, or
production authority. The evolution helper validates and records these stages
but never edits a skill, tracker, Git branch, policy, or target. The incumbent
remains the sole production authority through the Block 13 Stop.

## Governed candidate evaluation

Only a current `candidate-ready-for-comparison` owner proof can create the one
evaluation handoff. Before the comparison starts, the supervision owner
preflights the fixed sealed evaluator key and verification interface. It then
runs the same declared focused tests against the exact incumbent archive once.
A canonical comparison-start event makes a later missing completed result a
Stop rather than permission to rerun. The completed pending result binds that
exact start record ID, record hash, root, and start-before-producer chronology;
pre-start bytes reject. A per-cycle owner lock serializes duplicate delivery,
and an owner-authenticated pending record retains those raw command results
through file and parent-directory durability before the handoff append;
interruption reuses that exact result. The pending record is transient and is
not a required finalized evolution artifact. Once the canonical handoff
retains and revalidates its exact raw result and provenance, the owner removes
the pending record and syncs the parent directory; duplicate delivery safely
completes that cleanup without rerunning the producer. The handoff pairs it
with the already-retained candidate results and binds its provenance root and
the preflighted evaluator-key root together with
the packet, review, experiment, candidate contract, owner handoff,
acknowledgment, exact baseline/candidate revisions and roots, every positive
and exception case ID, protected-capability results, resource use,
reversibility, incumbent production authority, and the exact target-owner ref
plus bounded reflog-file currentness root, including same-HEAD events. A stale
root rejects before that mapped comparison
is run. Target-currentness loss during the physical handoff append records an
exact correction before returning rejection. The owner root keeps the stale
handoff inactive if correction persistence is interrupted or the target
transiently changes and returns.

The configured sealed adaptive evaluator is distinct from the review proposer
and implementation owner. Its submission is signed by the fixed evaluator key
and covers every positive and exception case exactly once for both conditions.
Every semantic result binds its condition revision and the corresponding raw
validation root; result arrays also retain observed effects, costs, and
regressions. The signed submission includes bounded contrary evidence,
regression findings, rationale, and exactly one existing disposition:
`promote`, `advisory`, `revise`, or `reject`.

`promote` requires complete passing candidate cases, passing raw candidate
commands, preserved protected capabilities, no regression findings, distinct
condition evidence, and the review's improvement or non-inferiority posture.
At the evaluation boundary it means only `adoption_eligible`;
`adoption_authorized` remains false and the incumbent remains authoritative.
`advisory`, `revise`, and `reject` route to their exact non-adoption
Stop/owner posture. The canonical evaluation event is
immutable and idempotent; retry rehydrates its exact disposition without
rerunning comparison or performing a target write. Target-currentness loss
during its physical append similarly records an exact correction. Its bound
target-owner root leaves no active evaluation disposition across correction
interruption or a transient ref change-and-return.

## Governed adoption and retirement

An evaluated cycle enters the existing supervision writer once more. The
adoption gate revalidates the current mission, policy, implementation range,
Factory target revision, exact evaluation, incumbent installation, permission
ceilings, and role separation. `fixed` records only; `recommend` records a
recommendation; `advisory`, `revise`, and `reject` retain their exact
non-adoption posture. Only `promote` in `reviewed-autonomous` or
`full-autonomous`, with `repository_write`, `allowlisted_skill_maintenance`,
`release`, and `production_promotion` all already true, can call the normal
release owner. Full autonomy creates no human request.

The evolution artifact never writes an installed path. The existing local
release owner independently rebuilds the candidate from its exact Git commit,
requires an externally signed exact-candidate review, stages one sealed
three-skill release, consumes one current separately signed operator boundary,
and atomically compares the frozen prior release ID plus activation-history
HMAC before replacing only the established release-root `current` pointer.
Intervening release activity, including an A-to-B-to-A sequence, rejects before
the operator boundary is consumed.
Stable discovery links do not change. A fresh process resolves and hashes all
three installed skills before success. The adoption executor, release
reviewer, evolution reviewer/proposer, implementation owner, and evaluator
remain separated by the applicable role constraints.

The canonical adoption result binds the frozen evaluation, mode and four
permission results, requested-capability, selected-architecture, tradeoff,
protected-behavior, baseline-behavior, capability-frame, packet, review,
experiment, acknowledgment, and evaluation roots; the baseline release
transition; the post-release-owner root; accepted manifest; release acceptance
and activation records; installed verification and operator-visible-effect
roots; authority posture; and next outcome-reconciliation action. The post-
release snapshot's activation record ID and HMAC must equal the exact owner
result, so a post-activation release-history change rejects before the adoption
event. Interrupted rehydration accepts only one unique candidate activation
from the frozen baseline. The
supervision owner holds the exact current Git ref against a concurrent ref
write and requires a clean, unchanged baseline worktree immediately before and
after the release effect and physical event append. Retry after a completed
activation but before the supervision append rehydrates the installed release
without another activation or operator record. A release-owner change during
append records an exact currentness correction; the stale source event cannot
remain active. Exactly one installed release is authoritative after a
successful adoption. This stage does not publish, deploy, expand policy,
create a candidate, rerun the mapped comparison, or claim terminal outcome
completion.

## Governed outcome feedback and rollback

Every adopted, retained, revised, or retired cycle closes through one canonical
`factory-evolution-outcome` event. The event binds the admission coverage,
packet, review, evaluation and adoption roots; selected and rejected paths;
intended and independently observed effects; protected regressions; bounded
resource use; owner identities; recurrence posture; and exact evidence refs.
An installed adoption requires the latest independently verified
`observable-outcome-completion` record for its exact evaluation/adoption state.
Evaluation or report prose alone cannot establish effectiveness.

Run `factory-evolution --action outcome --evolution-id <id>
--outcome-completion-record <record-id>` after the current observable result is
available. Non-adoption postures omit the completion argument and close against
the retained incumbent. A verified adopted result becomes
`adopted-effective`. A later supported `reopen-narrow-owner` result appends a
successor in the same outcome lineage, preserves the earlier effective record,
and requires `--quiescent-evidence` so the existing release owner can restore
the frozen baseline. Rollback compares the exact candidate activation, appends
one normal release-history rollback record, revalidates all installed skill
roots, and is idempotent across interruption; it never deletes the candidate,
review, evaluation, adoption, or earlier outcome evidence.

The latest current outcome head alone governs status. A release-owner change at
the physical outcome append produces an append-only currentness correction;
interruption before that correction is recoverable, and a corrected outcome is
never authoritative. The original admission's canonical coverage becomes
consumed only after a current terminal outcome. Repackaging, checkpoint changes,
overlap, and unrelated repository revisions remain no-ops. A current terminal
outcome may itself be nominated as later canonical evidence, but only the latest
uncorrected head is eligible and its new record root is consumed by the later
cycle in the ordinary way.

Weekly and terminal JSON, Markdown, and PDF reports contain a concise derived
outcome projection with current cycle IDs, outcome roots, posture, rollback,
recurrence, and next action. The canonical event ledger retains the complete
precision. Reporting remains nonauthorizing and does not reopen a consumed
cycle. No continuous monitor, reward score, learning database, or automatic new
candidate is introduced.

## Exact submission wire shapes

The public helper rejects extra or missing fields. Submission JSON is bounded,
normalized, and source-bound; it contains no transcript, prompt, target-file
content, or hidden reasoning.

The `finalize --review-json` object has these exact top-level keys:

`schema_version`, `kind`, `packet_id`, `packet_root`, `reviewer_id`,
`observations`, `lessons`, `meta_patterns`, `candidates`, `selection`, and
`experiment`. Use `software-factory-evolution-review` as `kind`.

- Observation: `observation_id`, `summary`, `valence`, `event_ids`.
- Lesson: `lesson_id`, `statement`, `observation_ids`,
  `supporting_case_ids`, `report_hypothesis_ids`,
  `counterexample_case_ids`, `counterexample_posture`,
  `counterexample_search`, `goals_advanced`, `goals_threatened`,
  `causal_hypothesis`, `confidence`, `applicability`,
  `unresolved_questions`.
- Meta-pattern: `meta_pattern_id`, `statement`, `lesson_ids`,
  `supporting_case_ids`, `counterexample_lesson_ids`, `applicability`,
  `uncertainty`.
- Candidate: `candidate_id`, `candidate_type`, `capability_gap`, `effect`,
  `meta_pattern_ids`, `evidence_ids`, `protected_capabilities`, `applicability`,
  `tradeoffs`, `uncertainty`, `counterexample_case_ids`,
  `counterexample_posture`, `counterexample_search`, `implementation_owner`,
  `evaluation_owner`, `smaller_change_insufficient`, `proportionality`, and
  `selection_dimensions`.
- Every selection-dimension object has `rating`, `rationale`, and
  `evidence_ids`. The exact dimensions are `effect`, `recurrence`, `reach`,
  `compounding_value`, `reliability`, `product_gain`, `evidence_strength`,
  `cost`, `regression_risk`, `complexity`, `reversibility`, and
  `time_to_evidence`.
- Selection: `candidate_id`, `compared_candidate_ids`, `rationale`, and
  `dimensions_considered` in the maintained dimension order above.
- Experiment: `experiment_id`, `candidate_id`, `proposer_id`, `implementer_id`,
  `evaluator_id`, `baseline_revision`, `candidate_revision`,
  `positive_case_ids`, `exception_case_ids`, `expected_effects`,
  `resource_bounds`, `rollback_condition`, `success_measures`,
  `regression_measures`, `evidence_capture`, `stop_condition`,
  `comparison_mode`, `minimum_expected_delta`, and
  `non_inferiority_justification`.
- `reviewer_id` is the experiment `proposer_id`; the helper rejects an alias.
  The evaluation `evaluator_id` must remain distinct from that reviewer and the
  implementer.

For a legacy on-demand evolution set, the `evaluate --evaluation-json` object
has these exact top-level keys:

`schema_version`, `kind`, `packet_id`, `packet_root`, `review_id`,
`review_root`, `experiment_id`, `candidate_id`, `evaluator_id`,
`baseline_results`, `candidate_results`, `contrary_evidence_ids`,
`regression_findings`, `disposition`, and `rationale`. Use
`software-factory-candidate-evaluation` as `kind`.

Every baseline or candidate result has `case_id`, `evidence_class`,
`evidence_ids`, `outcome`, `observed_effect`, `resource_cost`, `regressions`,
`condition_revision`, and `evidence_root`. Compute `evidence_root` with
`factory_evolution.experiment_result_evidence_root(result_without_root)` after
normalizing ID/string arrays; the validator recomputes it from every result
field. Baseline and candidate result arrays each cover every positive and
exception case exactly once.

For a governed admitted cycle, first run `orchestrate` after the owner
acknowledgment to create the raw evaluation handoff. Its signed
`evaluate --evaluation-json` object has these exact top-level keys:

`schema_version`, `kind`, `evaluation_handoff_root`, `evaluator_id`,
`evaluator_authority_key_sha256`, `evaluation_signature_base64`,
`baseline_results`, `candidate_results`, `contrary_evidence`,
`regression_findings`, `disposition`, and `rationale`. Use
`software-factory-orchestrated-candidate-evaluation-submission` as `kind`.

Each governed baseline/candidate result has `case_id`, `outcome`,
`observed_effect`, `resource_cost`, `regressions`, `condition_revision`,
`source_evidence_root`, and `evidence_root`. The source root is the exact raw
condition validation root from the canonical handoff. The evidence root is the
canonical digest of `{evaluation_handoff_root, result: result_without_root}`.

### Types and accepted values

- `schema_version` is the JSON integer `1`. Every `*_id`, `*_root`, revision,
  prose, enum, and `kind` value is a JSON string. Plural `*_ids`, goals,
  tradeoffs, questions, effects, bounds, measures, findings, and regressions are
  JSON arrays of strings. Record collections are JSON arrays of objects.
- `selection_dimensions` is a JSON object whose exact keys are the twelve
  maintained dimensions. Each value is an object with string `rating`, string
  `rationale`, and an `evidence_ids` array of strings.
- Observation `valence`: `productive`, `harmful`, `exception`, or `mixed`.
- Counterexample `posture` for lessons and candidates: `observed`,
  `searched-none-found`, or `unknown-limits-applicability`. `observed` requires
  one or more exact counterexample case IDs; either non-observed posture
  requires an empty case array and a nonempty documented search.
- Lesson `confidence`: `low`, `medium`, or `high`.
- Candidate `candidate_type`: `detector`, `correction`, `exculpator`,
  `skill-method`, `tracker-method`, `supervision`, `execution`, `evaluation`,
  `resource-policy`, `architecture`, `removal`, or `experiment`.
- Selection-dimension `rating`: `low`, `medium`, `high`, or `unknown`.
- Experiment `comparison_mode`: `improvement` or `non-inferiority`.
  `improvement` requires an empty `non_inferiority_justification` string;
  `non-inferiority` requires a nonempty justification.
- Result `evidence_class`: `observed`, `shadow`, or `synthetic`. Result
  `outcome`: `pass`, `fail`, or `mixed`.
- Evaluation `disposition`: `promote`, `advisory`, `revise`, or `reject`.

All prose must already be single-spaced, nonempty unless explicitly allowed
empty, and no longer than 600 characters. ID arrays and string arrays are
unique and sorted by the validator before identity is computed. To construct a
result root reproducibly from a JSON result object that omits `evidence_root`,
run this from the repository root after making `evidence_ids` and `regressions`
sorted and unique:

```bash
PYTHONPATH=supervise-tracker-runs/scripts \
  uv run --python 3.14 python -c \
  'import json,sys; from factory_evolution import experiment_result_evidence_root; value=json.load(sys.stdin); value["evidence_ids"]=sorted(value["evidence_ids"]); value["regressions"]=sorted(value["regressions"]); print(experiment_result_evidence_root(value))' \
  < result-without-root.json
```
