# Software Factory Learning and Capability Evolution MVP Implementation Tracker

- Tracker status: `completed`
- Tracker sequence: Blocks 0–6
- Repository: `https://github.com/estill01/software-factory`
- Planning baseline: `087803add9877b55763220070d68fa5c6e6dedb4`
- Governing objective: `Use verified cross-run evidence to identify one Software Factory capability gap, implement the selected capability through the existing three-skill system, compare baseline and candidate behavior, and permit promotion only from current independent evidence.`

## 1. Purpose and intended outcome

Build the smallest complete Software Factory evolution loop. The loop must turn
existing canonical supervision evidence and derived reports into source-bound
lessons, synthesize higher-order capability gaps rather than only detector
changes, select one reversible candidate, implement it through existing owners,
and compare baseline and candidate behavior before promotion.

The first seeded candidate is target-product capability alignment. It is a
candidate to be tested, not a conclusion that the evidence-processing machinery
may silently assume.

Completion means:

- a deterministic, content-minimized learning packet can be rebuilt from exact
  report and canonical-event roots without becoming operational authority;
- a bounded cognitive review can record lessons, counterexamples, meta-patterns,
  capability candidates, and a visible multidimensional selection rationale;
- one selected capability can receive a baseline-versus-candidate experiment
  with independent disposition of `promote`, `advisory`, `revise`, or `reject`;
- the existing authoring, execution, and supervision skills implement a
  source-backed target-product capability frame without always preferring
  generalized architecture; and
- a dogfood cycle proves the packet-to-candidate-to-implementation-to-evaluation
  path at one frozen repository revision.

### Mission frame

- Primary outcome: Software Factory can improve its own capability set from
  verified experience, not merely add incident detectors or rewrite itself from
  persuasive report prose.
- Observable completion: The derived evolution artifacts verify from exact
  source roots, the three installed skills exhibit the selected target-product
  alignment behavior, paired underreach/over-architecture cases distinguish the
  intended behavior, and an independent exact-candidate review supports the
  recorded terminal disposition.
- Ordinary effect classes needed: derived packet creation, contract validation,
  bounded semantic synthesis, candidate selection, skill-method changes,
  focused and mapped tests, baseline/candidate comparison, independent review,
  Git checkpoints, and local skill activation through the existing symlinks.
- Hard direct authority or safety boundaries: reports remain derived; canonical
  supervision records remain unchanged; `supervision_log.py` remains the only
  public supervision filesystem writer; target repositories are read-only for
  evidence; no hidden reasoning is requested; no candidate self-promotes; no
  user/global Codex configuration, external release, destructive operation, or
  target-product implementation is authorized by this tracker.
- Material goal alteration or reversal: adding autonomous promotion, target
  writes, a new canonical ledger, runtime action interception, App Server or
  hook integration, a general detector/control platform, or an opaque aggregate
  quality score requires a later tracker or renewed direct authority.

### Target-product capability frame

- Applicability: `consequential`.
- Product thesis: Software Factory is a three-skill system that turns an
  implementation goal into a dependency-ordered program, executes it
  autonomously and economically, independently supervises drift and recovery,
  and verifies the operator-visible outcome.
- Intended user effect: improvements learned from prior runs change future
  Software Factory behavior through inspectable, reversible, evidence-gated
  skill changes.
- Protected capabilities: direct-mission authority, independent review,
  one canonical supervision writer, bounded continuation, exact Block
  checkpoints, current observable-outcome proof, and local skill activation.
- Architecture strategy: extend the three existing skill owners and the
  supervision helper; use derived artifacts for synthesis and evaluation;
  do not introduce a fourth skill, service, database, or runtime daemon in this
  MVP.
- Requested capability: evidence-grounded Factory capability evolution.
- First candidate capability: source-backed target-product alignment during
  tracker authoring, consequential Block execution, and terminal closure.
- Proportionality rule: reject both a lower-power local path that conflicts with
  supported product capability and a generalized platform unsupported by the
  immediate or evident adjacent need.
- Uncertainty: four current report artifacts cover one long supervised target,
  while canonical event ledgers cover four targets; this is sufficient for an
  MVP and not for broad statistical calibration.

## 2. Target architecture and authority boundaries

```text
verified report.json + canonical events.jsonl
                     |
                     v
        deterministic derived learning packet
                     |
                     v
  bounded cognitive review: lessons + counterexamples
                     |
                     v
        meta-patterns + capability candidates
                     |
                     v
 visible dimensions + selected experiment candidate
                     |
                     v
 existing author -> implement -> supervise owners
                     |
                     v
 baseline/candidate cases + independent disposition
                     |
                     v
 accepted skill change or explicit revise/reject record
```

Authority rules:

1. `events.jsonl` and verified report source roots remain evidence authority.
2. Evolution packets, reviews, candidates, experiments, and manifests are
   derived artifacts and may be deleted and rebuilt.
3. `factory_evolution.py` validates and computes artifacts; public writes occur
   only through `supervision_log.py`.
4. Cognitive review proposes lessons and candidates but cannot write canonical
   incidents, change target repositories, edit skills, or promote itself.
5. Existing tracker authoring, implementation, Git, supervision maintenance,
   and exact-candidate review contracts own actual skill changes.
6. Candidate and evaluator identities remain distinct in accepted experiment
   evidence.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Canonical events, policy, and public supervision writes | `supervise-tracker-runs/scripts/supervision_log.py` | adapt |
| Verified cognitive reports and source roots | `weekly_report.py`, `terminal_report.py`, and their verified artifacts | reuse |
| Supervisor learning threshold and skill-maintenance authority | `supervise-tracker-runs/SKILL.md` and `references/supervision-policy.md` | adapt |
| Tracker capability framing and verification | `author-implementation-trackers/` | adapt |
| Consequential implementation-path selection | `implement-tracker-blocks/SKILL.md` | adapt |
| Terminal observable-outcome challenge | current completion-record and terminal-review owners | adapt |
| Local installation | the three existing `~/.codex/skills/` symlinks | reuse without configuration mutation |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| Current repository | `087803add9877b55763220070d68fa5c6e6dedb4` | adapt | 0 | Freeze exact owners and behavior |
| Existing supervisor-effectiveness learning loop | planning-baseline policy/skill hash | adapt | 0–3 | Generalize from skill-maintenance defects to capability gaps |
| Attached adaptive alignment/control tracker | planning input outside repository | not adopted as the MVP execution tracker | 0 | Reuse bounded alignment, replay, false-positive, and authority principles only |
| Strategic Learning and Evolution Engine note | direct user-supplied planning source | adapt | 0–6 | Prove one complete vertical cycle |

## 5. Scope, non-goals, and proportionality

### In scope

- Exact-source learning packet preparation and verification.
- Structured lessons covering productive and harmful patterns.
- Counterexamples, applicability, uncertainty, and causal hypotheses.
- Meta-pattern and capability-gap synthesis.
- Visible selection dimensions and one reversible experiment contract.
- The first target-product-alignment capability across existing skill owners.
- Synthetic and local dogfood evidence with independent candidate review.

### Out of scope

- App Server streams, lifecycle hooks, runtime interception, event-chain engines,
  adaptive routers, control registries, shadow controls, or automatic blocking.
- Embeddings, vector databases, learned models, hosted services, dashboards,
  schedulers, telemetry systems, or broad statistical claims.
- Unreviewed skill mutation or automatic promotion.
- Target-repository implementation or target-owned alignment files.
- A fourth Software Factory skill merely to hold this workflow.

### Proportionality

Build one vertical capability-evolution proof before generalizing runtime
control infrastructure. Reuse exact current report/event artifacts and batch
them once. Add a mechanism only when an acceptance condition cannot be met
through an existing owner.

## 6. Block execution contract

1. Execute Blocks 0–6 in dependency order and audit each Block before advancing.
2. Re-read the active Block and inspect current owners before editing.
3. Keep derived evolution artifacts outside canonical target/event authority.
4. Use synthetic fixtures for repository tests and content-minimized exact IDs
   for local dogfood; never commit target prose, transcripts, or secrets.
5. Finish likely-mutating review before mapped final validation and bind proof
   to the frozen candidate.
6. Commit and push every coherent accepted Block. Preserve rejected candidates
   and remediate through successor commits.
7. Do not implement any out-of-scope runtime control feature merely because it
   appeared in the predecessor tracker.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
- Inputs: `<paths, IDs, versions, hashes>`
- Outputs: `<paths, IDs, versions, hashes>`
- Focused validation: `<commands and results>`
- Mapped validation: `<commands and results>`
- Candidate freeze: `<commit/content root>`
- Resource posture: `<bounded inputs and widening>`
- Independent review: `<reviewer/evidence or not-applicable>`
- Retained open work: `<items or none>`
- Post-block audit: `<accepted/reopened>`
- Git durability: `<branch, commit, push>`
```

## 7. Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Freeze the MVP evidence and capability-evolution contract | — | `accepted` |
| 1 | Build the deterministic derived learning packet | 0 | `accepted` |
| 2 | Validate lessons, capability candidates, and experiments | 1 | `accepted` |
| 3 | Integrate the evolution workflow through the supervision owner | 2 | `accepted` |
| 4 | Add target-product capability framing to tracker authoring | 3 | `accepted` |
| 5 | Apply target-product capability review during Block execution | 4 | `accepted` |
| 6 | Reconcile terminal capability, dogfood the cycle, and accept | 5 | `accepted` |

Required order:

`0 → 1 → 2 → 3 → 4 → 5 → 6`

## Block 0 — Freeze the MVP evidence and capability-evolution contract

Status: `accepted`

### Objective

Establish the exact evidence classes, derived-artifact contract, first-candidate
posture, and baseline behavior before adding implementation machinery.

### Inputs and dependencies

- Planning baseline `087803add9877b55763220070d68fa5c6e6dedb4`.
- Current three skills, supervision helper/policy, report contracts, tests, and
  local content-minimized supervision-state inventory.
- The attached strategic note and predecessor tracker as planning inputs.

### Required work

- Add one concise maintained evolution contract reference under the supervision
  skill defining evidence authority, lessons, meta-patterns, capability gaps,
  candidates, experiments, promotion dispositions, and rebuildability.
- Record supported source classes and the minimum evidence/counterexample
  posture for a candidate.
- Define target-product alignment as the seeded first experiment, not a
  pre-approved promotion.
- Add contract-level tests that prevent report prose from becoming authority,
  prevent candidate self-promotion, and preserve positive-pattern learning.

### Scope and non-goals

- In scope: maintained semantic contract and static tests.
- Not in scope: packet code, CLI changes, or skill behavior changes.
- Do not create a schema collection or runtime state owner.

### Deliverables and recorded state

- `supervise-tracker-runs/references/factory-evolution-contract.md`.
- Focused contract tests in the existing supervision test owner.

### Resource and economy contract

One bounded inspection of current report/event shapes and existing learning
rules; no model/provider calls and no copied target content.

### QA and independent review

Mechanical tests verify explicit authority and disposition boundaries.
Substantive review checks that the contract can produce a new capability rather
than only a new detector.

### Acceptance

- Reports nominate hypotheses; exact canonical evidence adjudicates them.
- Productive and harmful patterns are both representable.
- Lessons remain distinct from controls and capabilities.
- Candidate implementation and promotion are separate.

### Negative tests

- Reject `report says so` as sufficient promotion evidence.
- Reject a contract limited to detector/control candidates.
- Reject self-certified promotion.

### Completion evidence

- Repository commits: `8f0c316f48f9bbfce74362cfcb96306cc1ed9d36`
  (contract and initial tests) and
  `4df0851c8a3304b74adf55ea44ac938b61889e24` (review remediation).
- Inputs: planning baseline `087803add9877b55763220070d68fa5c6e6dedb4`,
  Block 0 contract, current report/event shapes, and existing learning rules.
- Outputs: `factory-evolution-contract.md` at SHA-256
  `7884823f242ac18bb2a25eea103f01e1931636b16c91a8eddc6ab91af8526e4d`
  plus six contract guardrail tests.
- Focused and mapped validation:
  `uv run --python 3.14 --with reportlab python -m unittest discover -s
  supervise-tracker-runs/scripts -p 'test_supervision_log.py'` — 106 tests,
  all passed.
- Candidate freeze: exact successor commit `4df0851c8a3304b74adf55ea44ac938b61889e24`.
- Resource posture: one bounded local shape/rule inspection; no provider calls,
  target content, packet preparation, public writes, or whole-home discovery.
- Independent review: distinct `block0_review` reviewer found the candidate
  admission floor underspecified; successor commit `4df0851` added exact
  hash-bound support and known-counterexample or documented-search requirements.
  The reviewer re-reviewed that delta and returned no findings.
- Retained open work: packet preparation and all runtime integration remain in
  Blocks 1–6.
- Post-block audit: accepted after remediation; the contract represents broad
  capability types, productive and harmful patterns, evidence authority, and
  evaluator independence while stopping before packet or CLI behavior.
- Git durability: `codex/evolution-mvp`; implementation and evidence commits
  pushed to configured `origin` after this evidence checkpoint.

### Stop

Stop before implementing packet preparation or file writes.

---

## Block 1 — Build the deterministic derived learning packet

Status: `accepted`

### Objective

Produce one bounded, rebuildable packet from verified reports and canonical
events with exact source roots and enough content-minimized evidence for lesson
synthesis.

### Inputs and dependencies

- Block 0.
- Existing `report.json` and `events.jsonl` contracts.

### Required work

- Add `factory_evolution.py` behind the supervision script owner.
- Validate report identity/source roots and canonical event record hashes.
- Select supported evidence kinds, retain exact record IDs/hashes, and bound
  summaries/evidence arrays without copying full transcripts or target files.
- Deduplicate repeated report roots and event records.
- Compute deterministic coverage, source manifest, packet identity, and packet
  root independent of caller ordering.
- Add synthetic positive, productive, exception, and malformed fixtures/tests.

### Scope and non-goals

- In scope: pure packet construction, validation, minimization, and hashing.
- Not in scope: semantic lessons, candidate selection, or public CLI writes.
- Do not scan all supervision state implicitly; inputs are explicit.

### Deliverables and recorded state

- `supervise-tracker-runs/scripts/factory_evolution.py` packet functions.
- `supervise-tracker-runs/scripts/test_factory_evolution.py` packet tests.

### Resource and economy contract

Read each explicit source once, cap retained text and evidence fields, and
deduplicate by exact identity/root. No model calls or repository scans.

### QA and independent review

Focused tests cover ordering, duplicate roots, invalid hashes, unknown kinds,
bounded text, and rebuild equality. Review checks minimization and authority.

### Acceptance

- Equivalent explicit inputs yield the same packet root.
- A changed source changes the root.
- Every retained claim resolves to a report or event identity.
- The packet is explicitly derived and non-authoritative.

### Negative tests

- Reject malformed JSONL or a record whose declared hash is invalid.
- Reject raw transcript fields and unbounded strings.
- Reject implicit whole-home discovery.

### Completion evidence

- Repository commits: `ff97eaf` (initial pure builder), `f21bd40`
  (weekly-report contract correction), `0d7278e` (integrity hardening), and
  accepted successor `63b59d33bb2ef44d47ccc854c5514302c97c1eac`.
- Inputs: explicit synthetic fixtures plus one live weekly `report.json` and its
  matching canonical `events.jsonl`; no implicit state discovery.
- Outputs: pure `factory_evolution.py` at SHA-256
  `55b3453b38e8006a7169ba5288822edb9b9287367e45e6cc0ff87750dd52f336`
  and focused tests at SHA-256
  `7ccf532f235797e11d9b0606110907e1ee316994cc8513bc9676410a6e8a0acd`.
  No derived artifact was written.
- Focused validation:
  `uv run --python 3.14 python -m unittest discover -s
  supervise-tracker-runs/scripts -p 'test_factory_evolution.py'` — 19 tests,
  all passed.
- Mapped validation:
  `uv run --python 3.14 --with reportlab python -m unittest discover -s
  supervise-tracker-runs/scripts -p 'test_*.py'` — 145 tests, all passed;
  `py_compile` and `git diff --check` also passed.
- Live-schema acceptance: packet `learning-60905419088742cc16e7` rebuilt from
  one weekly report and a 1,149-record ledger, retaining 1,148 supported events,
  30 source-bound report hypotheses, and one counted unsupported event kind.
- Candidate freeze: exact successor commit
  `63b59d33bb2ef44d47ccc854c5514302c97c1eac`.
- Resource posture: explicit-path-only, one filesystem read per source, 16 MiB
  per-source cap, bounded input/source/record/hypothesis/evidence arrays, no
  model calls, transcript retention, target-file content, or public writes.
- Independent review and incident history: `INC-20260808-070407-2D3765`
  caught advertised terminal-report support backed only by a weekly loader;
  `f21bd40` narrowed the contract and added explicit rejection. A distinct
  `block1_review` reviewer then adversarially found shallow re-root validation,
  rewritten identities, conflicting-root collapse, dangling report evidence,
  aggregate-bound gaps, cross-ledger provenance, and ordering/nonempty gaps.
  Successors `0d7278e` and `63b59d3` preserved the rejected history and closed
  each finding. Final re-review returned no findings and independently rejected
  a two-ledger 12,000-index-row probe.
- Retained open work: semantic lesson/candidate/experiment validation and all
  public writes remain in Blocks 2–6.
- Post-block audit: accepted. Equivalent explicit inputs have one root;
  mutations change or invalidate it; exact claims resolve to a weekly report or
  canonical event identity; terminal reports, malformed or unsafe sources,
  stale hashes, conflicting roots, implicit discovery, and re-rooted malformed
  packets are rejected.
- Git durability: `codex/evolution-mvp`; all coherent implementation and
  evidence commits pushed to configured `origin` after this checkpoint.

### Stop

Stop before accepting cognitive review or writing derived artifacts.

---

## Block 2 — Validate lessons, capability candidates, and experiments

Status: `accepted`

### Objective

Turn a packet-bound cognitive review into validated lessons, meta-patterns,
capability candidates, and one independently evaluable experiment without
pretending semantic judgment is deterministic.

### Inputs and dependencies

- Block 1.
- The maintained evolution contract.

### Required work

- Validate lesson records with observations, supporting cases,
  counterexamples/posture, goals advanced or threatened, causal hypothesis,
  confidence, applicability, and unresolved questions.
- Validate meta-patterns against lesson IDs and capability candidates against
  meta-pattern/evidence IDs.
- Support detector, correction, exculpator, skill method, tracker method,
  supervision, execution, evaluation, resource policy, architecture, removal,
  and experiment candidate types.
- Preserve visible effect, recurrence, reach, compounding value, reliability,
  product gain, evidence strength, cost, regression risk, complexity,
  reversibility, and time-to-evidence dimensions; do not collapse them into one
  opaque score.
- Validate one selected-candidate experiment with baseline/candidate revisions,
  positive and exception cases, expected effects, resource bounds, rollback,
  evaluator independence, and disposition.
- Add deterministic machine report and manifest verification functions.

### Scope and non-goals

- In scope: validation, exact references, selection transparency, experiment
  comparison, and manifest equality.
- Not in scope: generating semantic prose, implementing candidates, or
  promoting changes.
- Do not infer causal benefit from shadow or synthetic observations alone.

### Deliverables and recorded state

- Review/candidate/experiment functions and focused tests in the Block 1 owners.

### Resource and economy contract

Validate bounded submitted objects once; reopen source evidence only through
exact cited references. No model calls inside deterministic code.

### QA and independent review

Tests cover dangling evidence, missing counterexample posture, opaque scoring,
self-review, unsupported disposition, regression cases, and exact rebuild.
Independent review challenges the selected candidate and experiment.

### Acceptance

- A validated review can conclude that a capability—not another rule—is
  missing.
- Candidate dimensions and contrary evidence remain visible.
- No candidate can be marked promoted without an independent experiment.
- Baseline and candidate results remain separately attributable.

### Negative tests

- Reject lessons supported only by report prose when exact cases are absent.
- Reject a selected candidate with no exception case or rollback condition.
- Reject proposer, implementer, and evaluator identity collapse.

### Completion evidence

- Repository commits: `787135b` (initial review/experiment validators),
  `dcd5e1f` (candidate admission and causal-comparison remediation), and
  accepted successor `0eaa6231353ee53cbf1046cbe83756c85663ab9f`
  (canonical condition-result evidence binding).
- Inputs: verified synthetic learning packet, maintained evolution contract,
  source-bound semantic review submission, selected experiment, and independent
  evaluation submission. Deterministic code did not generate semantic prose.
- Outputs: review, candidate, experiment, evaluation, machine-report, manifest,
  and exact-bundle validators in `factory_evolution.py` at SHA-256
  `23472379c6b616e8105ba197e3a1f3c34956ba6b9a714445a4f94b015cc7cf0c`;
  focused tests at SHA-256
  `af765f744121f3fc3e94030f8812060928245a4583747b4fb39ec36f873bc93c`.
- Focused validation:
  `uv run --python 3.14 python -m unittest discover -s
  supervise-tracker-runs/scripts -p 'test_factory_evolution.py'` — 29 tests,
  all passed.
- Mapped validation:
  `uv run --python 3.14 --with reportlab python -m unittest discover -s
  supervise-tracker-runs/scripts -p 'test_*.py'` — 155 tests, all passed;
  `py_compile` and `git diff --check` also passed.
- Candidate freeze: exact successor commit
  `0eaa6231353ee53cbf1046cbe83756c85663ab9f`.
- Resource posture: bounded submitted objects only; no model/provider calls,
  semantic generation, public writes, candidate implementation, or skill/CLI
  changes. Manifest inputs are capped by count, per-artifact bytes, and
  aggregate bytes.
- Independent review: distinct `block2_review` rejected `787135b` because
  candidate counterexample admission was absent, result contrast could be
  non-causal, exact lesson references could conflict, manifest bytes were
  unbounded, and the seeded fixture mislabeled a skill method as architecture
  while comparing only against a detector. `dcd5e1f` added candidate
  counterexamples/search, observation/support reconciliation, condition-bound
  all-case observed comparison, finite bytes, and a skill-method candidate
  compared with detector and tracker-method alternatives across explicit
  bounded-fit, underreach, and overarchitecture measures. Re-review then found
  caller-asserted result hashes; `0eaa623` derives each root from all normalized
  result and revision fields. The final reviewer mutated every bound field and
  confirmed rejection, returning no findings.
- Retained open work: public CLI writes, skill-method changes, and local dogfood
  remain in Blocks 3–6.
- Post-block audit: accepted. Report-only lessons, missing or inconsistent
  counterexample posture, dangling/contradictory references, opaque scores,
  owner collapse, unsupported dispositions, regression-bearing promotion,
  synthetic/shadow promotion, stale result roots, non-causal improvement, and
  oversized artifacts are rejected. Baseline and candidate roots remain
  separately attributable.
- Git durability: `codex/evolution-mvp`; all coherent implementation and
  evidence commits pushed to configured `origin` after this checkpoint.

### Stop

Stop before public CLI integration or skill-method changes.

---

## Block 3 — Integrate the evolution workflow through the supervision owner

Status: `accepted`

### Objective

Expose prepare, finalize, evaluate, and verify operations through the existing
supervision filesystem writer and maintained skill/policy without creating a
new operational ledger or scheduler.

### Inputs and dependencies

- Block 2.
- `supervision_log.py`, supervision skill/policy, and existing atomic derived
  report patterns.

### Required work

- Add one `factory-evolution` command family for prepare, finalize, evaluate,
  and verify.
- Store derived sets under the existing supervision learning directory with
  safe identities, exact source roots, atomic writes, immutable-or-identical
  reuse, and a verifiable manifest.
- Add the workflow to the supervision skill and policy: reports nominate,
  exact evidence adjudicates, Sol-level cognitive review proposes, existing
  skill owners implement, and independent evidence disposes.
- Keep scheduled execution, automatic implementation, notification, and
  promotion outside this Block.
- Add CLI integration and static skill/policy tests.

### Scope and non-goals

- In scope: existing CLI/writer integration and operating instructions.
- Not in scope: new schedules, Gmail, target routing, or automatic skill edits.
- Do not add a separate `evolution` skill.

### Deliverables and recorded state

- Integrated CLI commands, skill/policy guidance, and tests.

### Resource and economy contract

Inputs are explicit and prepared once. Finalize/evaluate reuse the frozen
packet and review. Verify performs hashes/schema checks without re-running the
producer.

### QA and independent review

Focused CLI tests verify safe paths, idempotent reuse, changed-artifact failure,
and action ordering. Skill validation and policy review are required.

### Acceptance

- The public workflow is usable through `supervision_log.py` only.
- Derived files cannot alter canonical events or policy.
- Re-running unchanged input reuses identical artifacts.
- Skill instructions clearly separate discovery, implementation, evaluation,
  and promotion.

### Negative tests

- Reject finalize before prepare.
- Reject changed content under an existing evolution ID.
- Reject promotion or target writes from the command family.

### Completion evidence

- Repository commits: `891b891` (initial CLI/skill/policy integration),
  `f29390f` (Skill Creator forward-test usability remediation), and accepted
  successor `cf20f43dfb6a633ef1d0e3388abe46ede96e1add` (owner and artifact-set
  containment).
- Inputs: explicit report/event, review, and evaluation paths plus the frozen
  packet/review from earlier stages. No command scans all supervision state.
- Outputs: `factory-evolution` actions `prepare`, `finalize`, `evaluate`, and
  `verify`; immutable stage artifacts and manifests under the target learning
  directory; maintained skill/policy/wire-shape instructions. Exact SHA-256:
  `supervision_log.py` `250cf473c8efca391432f849e5bd387ab23030c8b07187e05e3269d84b1be1f5`,
  supervision skill `8fb29d1c057c19b9377c380c5c932fbd661e8683cd9a91b15d6153ab2f61f592`,
  policy `06c4c4d6ad49644d137bf10e773b8f789da11cdf5717c5540195ede9af1d1242`,
  evolution contract `5dbf4ce0d0b33e05efb72e1e142011ac6bda4456c4f8810a13f0f8a128a1f48e`.
- Focused CLI/static validation: five original integration cases plus nested
  symlink and unexpected-artifact adversarial cases passed within
  `test_supervision_log.py`.
- Mapped validation:
  `uv run --python 3.14 --with reportlab python -m unittest discover -s
  supervise-tracker-runs/scripts -p 'test_*.py'` — 162 tests, all passed;
  `quick_validate.py supervise-tracker-runs` — `Skill is valid!`; `py_compile`
  and `git diff --check` passed.
- Candidate freeze: exact successor commit
  `cf20f43dfb6a633ef1d0e3388abe46ede96e1add`.
- Resource posture: explicit inputs prepared once; finalize/evaluate reopen
  frozen stored artifacts; verify checks stored schemas/hashes/manifests without
  producer rerun. Writes are serialized, atomic, immutable-or-identical, and
  inventory-bounded to seven JSON artifacts plus the no-follow lock.
- Independent review: distinct `block3_review` confirmed action ordering,
  partial/tampered-set failure, idempotent reuse, and absence of canonical
  event, policy, target, schedule, Gmail, notification, implementation, or
  promotion writes. It found a nested-owner symlink escape, incomplete enum
  guidance, and unmanifested `promotion.json` acceptance; `cf20f43` closed all
  three and the reviewer returned no findings.
- Skill Creator forward test: a cold-start reviewer using only the skill and
  required references correctly separated prepare/review/owner implementation/
  independent evaluation/verify and refused automatic edits or schedules. It
  found runtime, role, root, and submission-wire discoverability gaps;
  `f29390f` and `cf20f43` specified Python 3.11+/the maintained uv runtime,
  exact Sol XHigh/Max roles, default absolute artifact root, all JSON shapes and
  enum domains, normalization, and a runnable result-root command. Final
  forward re-test returned no findings.
- Retained open work: tracker-authoring and implementation-skill target-product
  behavior remain in Blocks 4–6.
- Post-block audit: accepted. Finalize-before-prepare, changed bytes under an
  existing ID, unsafe IDs, symlink escapes, partial/tampered or unexpected sets,
  producer inputs during verify, and any implicit promotion action fail closed.
- Git durability: `codex/evolution-mvp`; all coherent implementation and
  evidence commits pushed to configured `origin` after this checkpoint.

### Stop

Stop before changing tracker-authoring behavior.

---

## Block 4 — Add target-product capability framing to tracker authoring

Status: `accepted`

### Objective

Make new implementation trackers reconstruct source-backed target-product
capability intent before decomposing consequential product work.

### Inputs and dependencies

- Block 3.
- Existing authoring skill, template, block contract, verifier, and tests.

### Required work

- Add one concise tracker-level target-product capability frame covering
  applicability, thesis/effect, protected capabilities, architecture strategy,
  requested capability, proportionality, tradeoffs, and uncertainty.
- Require direct mission/repository sources for asserted product doctrine and
  permit explicit routine/not-applicable posture.
- Add a consequential-Block capability delta when feature behavior, canonical
  representation, architecture strategy, operating model, or a protected
  capability changes.
- Extend the full-profile verifier mechanically without pretending it can judge
  product quality; retain a documented compatibility path for inherited
  trackers.
- Add paired underreach and speculative-over-architecture tests.

### Scope and non-goals

- In scope: authoring skill, template, block contract, verifier, and tests.
- Not in scope: implementation-path selection or terminal review.
- Do not duplicate the global frame in every Block.

### Deliverables and recorded state

- Updated `author-implementation-trackers/` owners and accepted fixtures.

### Resource and economy contract

Perform one bounded target-product reconstruction per tracker and reuse it.
Verifier work remains linear in document length.

### QA and independent review

Run verifier tests and skill validation. Forward-test one consequential and one
routine request without providing the intended answer.

### Acceptance

- New full-profile trackers declare a target-product frame or justified
  not-applicable posture.
- Consequential Blocks expose capability gains/losses and tradeoffs.
- Unsupported product ethos and automatic preference for a platform are both
  rejected.

### Negative tests

- Reject literal feature wording as the whole product capability when direct
  broader intent exists.
- Reject unsupported architecture doctrine.
- Reject requiring generalized infrastructure for every local change.

### Completion evidence

- Repository commits: initial candidate `d57f8a6`; rejected-review
  remediations `f916ea4` and `6822ee8`; accepted candidate `c777c9c`.
- Inputs: Block 3; the authoring skill, template, Block contract, verifier, and
  tests at the planning baseline; direct Block 4 capability requirements in
  this tracker.
- Outputs: `author-implementation-trackers/SKILL.md`
  (`8154687040df4afbae6dc187cd373761c784609b4f9dbec00eb3a80ce21f3ac3`),
  `assets/implementation-tracker-template.md`
  (`c24bd08a75fe88746b483243ec27b73df67896c7da937fb83ec6ee042cb6be5b`),
  `references/block-contract.md`
  (`8ac907bcd39505a9cf6446f9b1cb709f4798cd73c972a868c11ac0b2e506f7bc`),
  `scripts/verify_tracker.py`
  (`f0f5f18de4ebd52682df6634cc1bcf3121e18a67a72d7f300d9fae45ce33995c`),
  and `scripts/test_verify_tracker.py`
  (`fd3855056d22191c4f9be4595995eba8d8e2fe0bdf34cc3ed97808e8eef49fe8`).
- Focused validation: 30 authoring tests passed; the authoring skill validator
  passed; `git diff --check` passed.
- Mapped validation: all 162 supervision tests passed under Python 3.14; this
  inherited tracker passed the documented `--profile core` compatibility path.
- Forward tests: a fresh consequential Download CSV request reconstructed the
  direct-source portability capability across web and CLI and rejected a
  second store/service; a fresh routine contributor-guide typo/link request
  stayed one Block and added no product or documentation platform. Both
  generated trackers passed the hardened full verifier unchanged at
  `c777c9c`.
- Candidate freeze: `c777c9c9b97787ad49d6dace328ca5b5041961b7`;
  no implementation files changed after final review.
- Remediation closure: contradictory or stray semantic sections, fenced and
  indented-code decoys, placeholder/deferred evidence, posture contradictions,
  valid angle-bracket prose, and sparse-ID allocation each received focused
  regression coverage. The initial macOS Python 3.9 mapped run was diagnostic
  because that runtime lacks `tomllib`; the identical suite passed under the
  repository's Python 3.14 runtime.
- Resource posture: the verifier is linear in document length; independent
  probes scaled from about 0.063 seconds for 1,000 Blocks to 0.465 seconds for
  8,000 Blocks, and a sparse Block 1,000,000,000 rejected in about 0.0011
  seconds without magnitude-based allocation.
- Independent review: exact-successor review at `c777c9c` found no remaining
  issues after a 26-case adversarial matrix; a separate exact review at
  `6822ee8` found no issues outside the later-contained evidence-deferral case.
- Retained open work: implementation-path capability review remains Block 5;
  terminal reconciliation and dogfood disposition remain Block 6.
- Post-block audit: `accepted`.
- Git durability: branch `codex/evolution-mvp`; accepted evidence commit and
  push recorded immediately after this update.

### Stop

Stop before changing the implementation skill.

---

## Block 5 — Apply target-product capability review during Block execution

Status: `accepted`

### Objective

Make the executor select a proportionate implementation path against the
accepted target-product frame without repeating product-strategy analysis for
routine Blocks.

### Inputs and dependencies

- Block 4.
- Current implementation skill and accepted tracker frame.

### Required work

- Add a concise product-capability review reference and route the implementation
  skill to it only for consequential Blocks or concrete drift triggers.
- Compare the smallest local path, bounded-general path, and available
  architectural owner; justify the selected level from current and evident
  adjacent needs.
- Check protected-capability regression, canonical-owner bypass, lower-power
  substitution, lost composability, and speculative generalization.
- Bind the selected capability delta and tradeoffs into completion evidence.
- Add static contract tests and paired realistic forward tests.

### Scope and non-goals

- In scope: implementation skill and one supporting reference.
- Not in scope: runtime interception, prospective monitoring, or broad
  rearchitecture outside the active Block.
- Routine Blocks retain the economical normal path.

### Deliverables and recorded state

- Updated `implement-tracker-blocks/SKILL.md` and
  `references/product-capability-review.md`.
- Focused cross-skill contract tests.

### Resource and economy contract

Read the tracker-level frame once per consequential Block and reuse its hash.
Widen only for one named missing product fact or affected owner.

### QA and independent review

Skill validation plus blind paired-case forward tests. Review rejects both
lower-power underreach and unsupported generalization.

### Acceptance

- The executor can state the product capability added or preserved.
- Passing local tests do not excuse a supported capability regression.
- A proportionate local solution is not rejected for lacking hypothetical
  future generality.
- Unknown product intent becomes a bounded dependency, not invented strategy.

### Negative tests

- Reject `always choose the most general architecture`.
- Reject treating every refactor as a consequential capability decision.
- Reject product framing that overrides explicit Block scope or direct mission.

### Completion evidence

- Repository commits: initial reviewed candidate `70d6e4b`; accepted remediation
  `17a7571`.
- Inputs: accepted Block 4 authoring contract; current implementation skill;
  tracker-level frame bytes with SHA-256
  `f45c827fbc9e5bc12f7ba8ee7140233e8bcad444403660596404a17cae475936`.
- Outputs: `implement-tracker-blocks/SKILL.md`
  (`887b3eca6f8ca1219878990c0031c84675a7f6258e321e19dd036b6899366bab`),
  `references/product-capability-review.md`
  (`68d255c1cd7c03b61b9278e0d1a20290c7452abb661ba00ae47d15e60bfc3017`),
  and `scripts/test_product_capability_contract.py`
  (`8df2eab497ad85ae66f682b2c5a47af605751e228ef9ea6f1c1566c9a8529c8f`).
- Focused validation: seven cross-skill capability-contract tests passed; the
  implementation skill validator and Python compilation passed.
- Mapped validation: all 30 authoring tests and 162 supervision tests passed
  under Python 3.14; `git diff --check` passed.
- Candidate freeze: `17a7571873cff82b4190db1ffe75216cac75937f`;
  no Block 5 implementation files changed after final review.
- Product-capability review:
  - Trigger: consequential executor behavior and completion-evidence change.
  - Frame identity: this tracker, Block 5, exact frame SHA-256
    `f45c827fbc9e5bc12f7ba8ee7140233e8bcad444403660596404a17cae475936`.
  - Capability added or preserved: the executor selects the least-complex
    source-supported implementation level without sacrificing a protected
    capability or penalizing a justified local solution.
  - Paths compared: inline local guidance; one bounded reusable review
    reference; the existing implementation skill as architectural owner.
  - Selected level and owner: one conditionally loaded reference routed by the
    existing implementation skill; this keeps the method inspectable without a
    new skill, runtime, service, or always-on gate.
  - Protected-capability result: routine Blocks retain the fast path; direct
    mission, Block scope, canonical owners, evidence-bound completion, and
    bounded input handling remain explicit.
  - Rejected alternatives: an inline-only reminder under-specified comparison
    and evidence binding; an always-general or runtime-enforced system was
    unsupported and outside scope.
  - Tradeoffs and uncertainty: consequential execution reads one 118-line
    reference once and reuses an exact byte hash; an absent or conflicting
    product fact remains a bounded dependency rather than invented intent.
  - Frozen-candidate proof: `17a7571`; static contracts, paired live execution,
    mapped tests, and exact-candidate review are current.
- Forward tests: the justified-local case used the existing session-preferences
  owner, passed four behavioral tests, demonstrated same-session retention and
  fresh-session reset, and added no settings platform. The lower-power case
  found the canonical report read already sufficient, preserved a rejected
  redundant-alias checkpoint, removed that alias, passed eight mapped tests,
  rehydrated the current canonical payload with provenance, and stopped before
  later web/CLI wiring.
- Remediation closure: static tests now guard positive concrete-drift routing,
  inherited formats, local-not-default, bounded unknown intent, tests-alone
  non-completion, and deterministic CRLF-preserving frame identity; the
  supporting reference has linked navigation.
- Resource posture: one frame read/hash and one bounded affected-owner pass;
  no runtime interception, monitoring, or broad rearchitecture was added.
- Independent review: two distinct exact-successor reviews at `17a7571` found
  no actionable issues; fresh probes covered routine fast path, inherited drift,
  canonical-owner comparison, missing intent, tests-only evidence, and CRLF
  byte hashing.
- Retained open work: terminal reconciliation and experiment disposition remain
  Block 6.
- Post-block audit: `accepted`.
- Git durability: branch `codex/evolution-mvp`; accepted evidence commit and
  push recorded immediately after this update.

### Stop

Stop before terminal capability reconciliation or experiment disposition.

---

## Block 6 — Reconcile terminal capability, dogfood the cycle, and accept

Status: `accepted`

### Objective

Demonstrate at one frozen revision that the derived evolution workflow produced,
implemented, and independently evaluated the first capability without replacing
the substantive outcome with process evidence.

### Inputs and dependencies

- Block 5.
- Frozen packet/review/candidate/experiment contracts and the changed three
  skills.

### Required work

- Add terminal target-product capability reconciliation to the supervision
  skill/policy and completion contract guidance.
- Reconcile requested capability, protected capabilities, selected architecture
  level, accepted tradeoffs, current behavior, and operator-visible effects;
  reopen only the narrow owner on a supported gap.
- Run the evolution prepare/finalize/evaluate/verify cycle against bounded local
  evidence without committing target content.
- Compare baseline and candidate on paired consequential-underreach and
  justified-local-solution cases using distinct reviewers.
- Run focused tests, all three skill validators, full mapped tests, tracker
  verification, and exact-candidate independent review.
- Record `promote`, `advisory`, `revise`, or `reject`; do not force `promote`.
- Update README only with behavior demonstrated by the accepted candidate.

### Scope and non-goals

- In scope: terminal capability review, dogfood evaluation, accurate docs,
  terminal evidence, and final disposition.
- Not in scope: runtime controls, automated deployment, external release, or
  additional capability candidates.
- Stop once the first cycle is truthfully disposed.

### Deliverables and recorded state

- Updated terminal supervision contracts/tests and evidence-bound README.
- Verified local dogfood artifact set outside canonical target state.
- Final tracker evidence and exact candidate commit.

### Resource and economy contract

Use the existing bounded local evidence inventory once. Forward-test only the
paired cases. Run the full mapped suite once after all mutating review; rerun
only affected proof after remediation.

### QA and independent review

The candidate author/implementer cannot be the sole evaluator. Independent
review reads the direct objective, raw paired cases, and exact candidate diff
before the completion narrative.

### Acceptance

- The complete packet-to-capability-to-evaluation path verifies.
- Target-product alignment changes all three owned workflow stages.
- Paired cases show less strategic underreach without systematic
  over-architecture.
- No report, test, tracker status, or self-review substitutes for current skill
  behavior and exact candidate evidence.
- The recorded disposition is supported and all Critical/High findings are
  resolved or block promotion explicitly.

### Negative tests

- Reject terminal acceptance from green tests without behavior evidence.
- Reject evaluator identity collapse.
- Reject target content in committed dogfood artifacts.
- Reject continuing into the predecessor tracker's broader control platform.

### Completion evidence

- Repository commits: initial terminal-contract candidate `3e24701`; semantic
  enforcement successor `d773307`; terminal-report fixture successor
  `41bc94e`; live-policy upgrade successor `1edd436`; accepted exact candidate
  `363596c`.
- Inputs: Block 5; verified weekly report
  `weekly-20260801T001853Z-20260803T234400Z-62f881d083b0` and its explicit
  canonical `events.jsonl`; the frozen baseline `876a03d`; the accepted
  candidate `363596ce10c4c3a39ead387bc9db493c12128c8b`; and the maintained Factory
  evolution wire contracts.
- Terminal reconciliation outputs:
  `supervise-tracker-runs/SKILL.md`
  (`9358ef1afffccd5b30c2ef179db0830d7f625ef28149ce514b411a456ff3862c`),
  `references/supervision-policy.md`
  (`4d3404b4d1426fae61104dc67b33eef5e940b9bf3dfddc0572dc0e8e8b4b9b66`),
  `references/terminal-capability-reconciliation.md`
  (`fbdbdc16592ee397771276c63f582fbcbb187e338fcd1abb1e3d4cb47a97e4ba`),
  `scripts/supervision_log.py`
  (`12957199609aea462d146140a3d581538ccf6e392a7ab94cc3629edf6ffdf7c6`),
  and focused completion/terminal-report tests.
- Evolution-independence outputs:
  `references/factory-evolution-contract.md`
  (`57d25b4f6871262adb6d84be753d46815e39c8133557115882b03d0d5c6a46ac`)
  and `scripts/factory_evolution.py`
  (`c731ed0d03424f9e32d7689038affd8005b8f8f4a9ba97290e204efcf3cdf8b6`).
  Review author now equals the recorded proposer, and evaluation rejects that
  reviewer or the implementer as evaluator.
- Behavior: `completion-record` now validates a bounded caller-owned semantic
  JSON before append, binds target, mission, state fingerprint, current
  revision, policy-eligible independent reviewer, implementation owner,
  claim-linked evidence classes, architecture owner, tradeoffs, current
  behavior, operator-visible effects, and enumerated gaps. A verified posture
  requires zero gaps; process-only evidence, stale content, self-review, or an
  unbound reviewer rejects. Only the normalized root and content-minimized
  identity/posture fields enter the canonical ledger.
- Compatibility and resource proof: the exact no-capability predecessor and
  the intermediate Block 6 policy contract remain readable and upgrade only
  through `bind`; a sparse oversized reconciliation rejects before open/JSON
  parsing and the post-stat read is bounded to 64 KiB plus one byte.
- Focused and mapped validation: 169 supervision tests, 30 authoring tests, and
  7 implementation contract tests passed; all three Skill Creator validators,
  `py_compile`, and `git diff --check` passed. This inherited tracker passed the
  documented `--profile core` verifier path.
- Paired independent condition reviews: baseline reviewer
  `baseline-reviewer-block1` and candidate reviewer
  `candidate-reviewer-block2` separately evaluated consequential underreach and
  justified-local work. Both revisions rejected browser-only export underreach
  and preserved the routine local fast path; candidate evidence additionally
  made the local/bounded-general/canonical-owner comparison and terminal
  reconciliation explicit. Baseline result SHA-256
  `3c1b5fd711b2f753e8ad7928ce5575389b5ea8a1c3a4bbf1c70f4f8ce9a25594`;
  candidate result SHA-256
  `4d367c6db28c23fef5fd8544dec1bd22158f2a112a31c90a86be0be3524e2b5c`.
- Verified local dogfood set: explicit root
  `/tmp/software-factory-evolution-block6.OwGuCe`, target identity
  `019fb18f-3d03-7ca0-9fe9-68353f0405ce`, evolution ID
  `sf-block6-cycle-20260808-b`. `prepare`, `finalize`, `evaluate`, and `verify`
  succeeded without target, policy, event, Gmail, automation, installation, or
  repository-content writes. Packet root
  `d13a5ab2f3cdc804f83edb30cc0d271bb2f34429c27d3a6244727a73534e8f49`;
  review root
  `b4ef76e84481c86985c18eb2230495593d43b3b9c8024e80b1dfa3c786f911ff`;
  evaluation root
  `274d7dd631656308d7c8fea6a15952e15bcbbb6d6c837b5784ff47578ab11a28`;
  manifest root
  `23abda282e79a9d0c44961c75e9d0038f92ecfcdb46ff31532672017408da71e`.
- Independent disposition: `evolution-evaluator-block6` recorded `promote` on
  a non-inferiority comparison because both exact revisions passed both cases
  with no protected regression and the candidate added reusable evidence. The
  disposition is review evidence only; it applied no promotion, install,
  deployment, notification, schedule, target write, or authority change.
- README evidence: `README.md`
  (`992a34de6c894d43c11028e7e2cc5ea4abc7418c896539341542fbd9dabad372`)
  describes only demonstrated reconciliation and non-automatic disposition
  behavior.
- Review history: exact review rejected opaque-hash and identity-alias
  candidates, then found and closed the intermediate live-policy upgrade gap
  and pre-read byte-bound gap. Final exact-archive review at
  `363596ce10c4c3a39ead387bc9db493c12128c8b` found no issues.
- Resource posture: one verified live report/event inventory was reused; only
  the two named paired cases were cold-reviewed; an immutable `-a` dogfood set
  was superseded before evaluation when review changed the candidate revision,
  and only the affected review/result/final cycle was repeated as `-b`.
- Retained open work: none in this tracker. Additional candidates, runtime
  controls, deployment, release, or acting on the disposition remain outside
  scope.
- Terminal tracker closure (2026-08-13): every Block 0–6 remains `accepted`;
  the final independently accepted candidate
  `363596ce10c4c3a39ead387bc9db493c12128c8b` is an ancestor of both this
  branch and installed release source
  `75481f37c3b64d887fdb7fa72fe2742f033c972d`; global release
  `75481f37c3b6-e3e2f2705136` is manifest-verified with candidate root
  `124aaddb656790ab79c55aabf18a56914b44ee18146c39d6cdb1716d92dd6505`,
  and all three stable skill links resolve through that exact release. Fresh
  current validation passed all three skill validators, the inherited core
  tracker verifier (`7` Blocks), and `git diff --check`. This closure changes
  tracker status only; it performs no implementation, promotion, release,
  policy, supervision, lifecycle, Gmail, or target effect.
- Post-block audit: `accepted`.
- Git durability: branch `codex/evolution-mvp`; accepted evidence commit and
  push recorded immediately after this update.

### Stop

Stop after the first capability-evolution cycle is verified and dispositioned;
do not implement additional candidates, runtime controls, or release work.

## 8. Verification matrix

| Capability or invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| Evidence authority and derived-artifact boundary | 0 | 1–3 | 6 |
| Rebuildable content-minimized learning packet | 1 | 2–3 | 6 |
| Lessons, meta-patterns, and broad capability candidates | 2 | 3 | 6 |
| Visible selection dimensions and independent experiment | 2 | 3 | 6 |
| One public supervision writer | 3 | 6 | 6 |
| Source-backed target-product tracker frame | 4 | 5–6 | 6 |
| Proportionate consequential implementation review | 5 | 6 | 6 |
| Terminal target-product capability reconciliation | 6 | — | 6 |
| Exact baseline/candidate behavior comparison | 6 | — | 6 |
| No autonomous promotion or broader runtime platform | 0 | 1–6 | 6 |

## 9. Final completion definition

The tracker is complete only when every Block is accepted at exact current
revisions; the evolution artifact set verifies from explicit source roots; the
first selected capability is implemented through the existing three owners;
paired behavior evidence and exact-candidate independent review support the
recorded disposition; the installed symlink targets expose the accepted files;
all focused and mapped validation passes; retained limitations remain explicit;
and no Block introduced a second operational authority, target write,
autonomous promotion, or broader prospective-control platform.
