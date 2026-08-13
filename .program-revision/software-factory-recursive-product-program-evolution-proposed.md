# Software Factory Recursive Product-Program Evolution Implementation Tracker

- Tracker status: `in-progress`
- Tracker sequence: Blocks 0–14
- Repository: `/Users/ethanstillman/code/software_factory-control-plane-candidate`
- Planning baseline: `4ae6a61b15f4c21604e7b9c9912a6272a3bf2330`
- Governing objective: Direct-user request to add one fourth Software Factory skill that recursively reflects on implementation and supervision evidence, discovers and challenges materially useful product work, selects and budgets one or more current or successor implementation programs, and advances them through the existing tracker-authoring, implementation, and supervision owners without derailing already-canonical work.
- Current direct implementation bounds: exactly Blocks 0–4. The direct-user
  amendment `direct-user-019ff991-authoring-supervision-merge-annotation-1`
  adds future program requirements but does not contract, expand, reopen, or
  displace that bounded implementation range.
- Program-revision source: the complete selection-quality tracker at exact commit
  `4df42f757cb71fd7ebaf30c8275d18f73049fb3b`, document SHA-256
  `e4a33fcb636980a6e99a99fd31ffb6d58f72cf7636234bb919971dd39776fd75`,
  is source planning evidence, not prior acceptance or application authority.

## 1. Purpose and intended outcome

Add `evolve-product-program` as the recursive product-program improvement owner.
The initial cycle remains exactly user intent to tracker authoring to implementation
under supervision. During that implementation and after its observable completion,
the new owner may use exact product, repository, implementation, supervision, and
resource evidence to reflect on what the system should become next. It may propose
features, capability areas, refactors, simplifications, removals, reliability or
operational work, experiments, current tracker revisions, or a sequential/parallel
portfolio of successor trackers. It must also be able to conclude that no further
work is presently justified.

Completion means:

- `evolve-product-program` is a separately installable fourth skill with one
  bounded, reproducible evidence-to-portfolio contract;
- the first implementation loop still begins directly from user intent without
  requiring a speculative evolution pass;
- materially changed implementation or supervision evidence can trigger one
  deduplicated recursive reflection cycle during a run or at terminal completion;
- divergent opportunity generation and convergent portfolio selection remain
  distinct, inspectable, counterexample-aware phases;
- every consequential feature/program portfolio is grounded in actual current
  behavior, features, capabilities, and all tracker states, then independently
  reviewed before tracker authoring; selection review and tracker-authoring
  review remain separate accepted boundaries;
- selected work can revise the current tracker or create one or more dependent or
  parallel successor trackers through `author-implementation-trackers`, while
  accepted history and the current requested range remain interpretable;
- consequential tracker authoring—whether RSI-generated or independently
  user-seeded—can bind an explicit `tracker-authoring` supervision profile for
  independent program/feature/Block review, repository-grounded owner and
  architecture challenge, target-owned correction, and exact
  implementation-readiness completion, while ordinary authoring retains its
  one-shot independent review path;
- time, token, command, tool, validation, and review budgets are allocated from
  transparent prior evidence and explicit uncertainty rather than an opaque score;
- current canonical work continues unless new evidence proves a prerequisite,
  protected-capability, architecture, or correctness reason to change its path;
- the four-skill release owner installs, verifies, refreshes, and can roll back the
  complete set without losing access to historical three-skill releases; and
- a frozen dogfood run proves user-seeded first-loop execution, in-run evolution,
  current-program revision, sequential and parallel successor placement, bounded
  resource allocation, a rejected poor selection, a sound reviewed selection,
  outcome-linked selection effectiveness, a versioned selector-policy candidate,
  retained and forward/shadow incumbent comparison, and an unchanged no-op
  recurrence across two exact cycles.

### Mission frame

- Primary outcome: Software Factory continuously improves the target product and
  its implementation program from observed evidence while honoring the user's
  governing intent and completing already-canonical commitments.
- Observable completion: one exact four-skill release and one independently
  reviewed two-cycle dogfood evidence set demonstrate the replayable chain
  `current product/tracker inventory → candidate set → selected portfolio and
  forecasts → independent selection review → authoring and implementation →
  observable outcome → selection-effectiveness evaluation → selector-policy
  revision → incumbent/candidate comparison → next selection cycle`, plus cheap
  unchanged replay.
- Ordinary effect classes needed: source and tracker authoring, derived evidence
  generation, cognitive review, bounded program/tracker revision, implementation
  and supervision integration, local task/role routing, tests, exact review, Git
  checkpoints and push, skill release, compatible monitor refresh, and rollback
  verification.
- Hard direct authority or safety boundaries: direct user intent remains the
  governing product boundary; `author-implementation-trackers` alone writes
  tracker structure; current implementation owners alone change target source;
  supervision remains the canonical event/policy writer; `skill_release.py`
  alone changes the installed release; spend, credentials, destructive effects,
  external communication, deployment, and material product-goal changes remain
  separately reserved.
- Material goal alteration or reversal: replacing the user's product intent,
  silently deleting an expressly requested capability, granting new permissions,
  making autonomous external or destructive decisions, treating resource
  estimates as spend authority, or allowing a generated candidate to self-adopt
  requires renewed direct-user authority.

### Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: this adds a fourth skill, changes the Software Factory
  operating model from a finite three-skill delivery pipeline to a recursively
  improving product-program loop, and introduces bounded portfolio and resource
  allocation decisions.
- Direct product sources: the direct-user 2026-08-13 agreement in this task that
  the first loop remains `user intent → author → implement + supervise`; later or
  concurrent evidence invokes recursive self-reflection over features, feature
  areas, implementations, refactors, removals, and other meaningful progress;
  selected work may modify the current tracker or form multiple sequential or
  parallel trackers; resource budgets should learn from time, token, quality, and
  supervision evidence; and exactly one additional skill should own this loop.
- Product thesis and intended effect: Software Factory should not wait for a user
  to invent every subsequent improvement. It should autonomously form and test
  evidence-grounded views of better product futures, choose a proportional
  program within the established mission, and keep useful implementation moving.
- Protected capabilities: direct-user semantic scope, first-loop cold start,
  accepted tracker history, full-range non-contraction, current-run remediation,
  independent evaluation, one owner per write boundary, safe continuation,
  protected-capability proof, transparent resource evidence, rollback, terminal
  reporting, and the ability to stop when no work is worthwhile.
- Architecture strategy: generalize the accepted Factory Evolution ladder and
  reuse adaptive decisions, program revision, range, successor-transition,
  supervision, reporting, and release owners. Add one skill as the product-program
  reflection and portfolio owner; add no second tracker writer, supervision
  ledger, release pointer, scheduler service, telemetry database, or opaque agent.
- Requested capability: the union of recursive feature/program selection,
  independent online supervision of consequential selection/design before
  authoring, and cross-cycle RSI that improves selector policy from actual
  outcomes without self-evaluation or self-adoption.
- Proportionality: a fourth skill is justified because product-level reflection
  and portfolio judgment are independently invocable and reusable across
  authoring, implementation, and supervision, while placing the entire capability
  inside any one of those owners would conflate proposal, execution, and review.
- Tradeoffs: broader autonomy can compound product value and reduce idle time,
  but it increases the need for explicit mission containment, portfolio
  currentness, non-derailment, role separation, resource ceilings, and no-op
  convergence. High-resolution brainstorming consumes resources and therefore
  runs only after a cheap material-change gate.
- Uncertainty: current supervision provides rich event, effectiveness, elapsed,
  and projected token/cost evidence, but actual provider token and billed-cost
  telemetry may be unavailable. Initial budget learning must preserve estimates
  as estimates and improve only from evidence actually observed.

## 2. Target architecture and authority boundaries

```text
FIRST LOOP
direct user intent
      |
      v
author-implementation-trackers -> implement-tracker-blocks
                                      ^          |
                                      |          v
                                supervise-tracker-runs

RECURSIVE LOOP, DURING OR AFTER IMPLEMENTATION
current product + repository + tracker + outcome + supervision + resource evidence
      |
      v
evolve-product-program
  1. currentness and material-change gate
  2. observation, lesson, and product/program self-reflection
  3. divergent opportunity and future-state generation
  4. counterexample and protected-capability challenge
  5. resource-yield and uncertainty analysis
  6. portfolio selection, dependency graph, budget, and placement
      |
      v
supervise-tracker-runs product-program-selection profile
  Terra currentness -> Sol XHigh semantic review -> Sol Max adjudication if needed
      |
      +--> accepted selection only: tracker authoring and implementation
      +--> revise / rejected / safe-deferred: no authoring authority
      |
      v
observable outcome -> independent selection-effectiveness evaluation
      |
      v
versioned selector-policy candidate -> retained + forward/shadow comparison
      |
      +--> no change / current-run remediation through existing owner
      +--> reviewed current-tracker revision through author owner
      +--> one successor tracker through author owner
      +--> sequential/parallel tracker portfolio through author owner
      +--> bounded experiment or safe deferral
      +--> direct-user decision only for a material goal or reserved boundary
```

Authority rules:

1. The new skill owns derived reflection, candidate-set, portfolio-selection,
   budget-proposal, and placement-handoff artifacts. Those artifacts are
   nonauthorizing until their existing downstream owner accepts them.
2. Canonical repository, tracker, supervision, release, automation, Gmail, and
   lifecycle state remain in their existing owners. The new skill writes none of
   those surfaces directly.
3. `author-implementation-trackers` remains the sole structural tracker writer.
   It may add, remove, reorder, modify, split, merge, reopen, retire, supersede,
   or create Blocks/trackers only from a current accepted evolution handoff and
   its own exact authoring/review contract.
4. `implement-tracker-blocks` owns current-run execution and invokes a cheap
   evolution checkpoint at configured Block and terminal boundaries. It never
   lets prospective work replace an unfinished requested range.
5. `supervise-tracker-runs` owns changed-state triggers, independent semantic
   review, current-run correction routing, effectiveness observations, and
   terminal lifecycle. It may invoke evolution but cannot select its own finding
   into canonical product work without the separate selection/review path.
6. The accepted Factory Evolution ladder supplies the reusable semantic core:
   evidence, observation, lesson, meta-pattern, gap, candidate, experiment, and
   disposition. Target-product profiles extend rather than copy that contract.
7. Multiple tracker lanes remain derived plans until each is separately authored,
   range-bound, admitted, and started. Parallel lanes require disjoint writable
   ownership or one explicit integration owner and shared-resource exclusions.
8. Budget selection allocates only within existing permission and resource
   ceilings. It cannot create spend, credentials, deployment, destructive, or
   external-action authority.
9. New releases contain four skills. Historical accepted three-skill manifests
   remain readable and rollback-eligible, but new state emits only the current
   four-skill schema and no compatibility aliases.
10. `author-implementation-trackers` remains the sole writer for both
    RSI-generated and user-seeded trackers. `supervise-tracker-runs` owns the
    explicit authoring target profile, canonical review/event state, changed-state
    routing, implementation-readiness completion, and bounded lifecycle; a steer
    remains open until later exact tracker evidence proves the target-owned fix.
11. `supervise-tracker-runs` also owns one distinct `product-program-selection`
    profile. Terra is currentness-only, Sol XHigh reviews the exact frozen
    selection, and Sol Max adjudicates only supported consequential uncertainty.
    The supervisor may hold, revise, reject, or safely defer the prospective
    handoff, but it cannot generate/select features or write tracker/source.
12. The selection evaluator, selector-policy proposer, policy comparator, and
    application owners remain distinct. Realized outcomes may propose one bounded
    versioned policy delta, but only retained held-out evidence plus one forward
    or shadow cycle and independent acceptance can make it application-eligible.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Evidence-to-candidate recursive learning ladder | `supervise-tracker-runs/scripts/factory_evolution.py` and `references/factory-evolution-contract.md` | generalize and reuse |
| Product capability and protected-capability reasoning | tracker target-product frames and `implement-tracker-blocks/references/product-capability-review.md` | reuse |
| Current-run path decisions | adaptive decision `continue-unchanged`, `correct-inline`, `compare-candidate`, `amend-structure` | reuse unchanged |
| Structural tracker revision and renumbering | `author-implementation-trackers`, `program_revision.py`, and canonical program-revision review/application | extend through existing owner |
| Original requested range and inserted-work continuation | implementation-range binding/amendment/gate | reuse and preserve |
| Cross-task/mission continuation | successor-transition and mission/range activation owners | reuse |
| Changed-state and effectiveness observations | canonical supervision event ledger, Sol review roles, weekly/terminal reports | reuse |
| Resource evidence | execution-economy records, candidate budget use, weekly-report elapsed/token/cost projections | adapt with evidence-class labels |
| Skill installation, verification, rollback, and refresh | `scripts/skill_release.py` plus accepted automatic release/refresh line | extend from three to four skills |
| Consequential feature/program selection review | `supervise-tracker-runs` canonical policy/events/roles/lifecycle | add a distinct online profile in Block 5; no parallel monitor or ledger |
| Consequential tracker-authoring supervision | `supervise-tracker-runs` canonical policy/events/lifecycle plus `author-implementation-trackers` sole-writer contract | adapt through Blocks 6, 8, 11, and 14; preserve independent user-seeded operation |
| Selection-effectiveness and selector-policy RSI | observable-outcome, Factory Evolution, exact Git/review, release, and refresh owners | add derived evaluation and comparison in Blocks 12–13 without self-adoption |
| Automation and external effects | existing automation, Gmail, release, deployment, credential, spend, and destructive owners | preserve; never infer |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| Accepted Factory Learning and Capability Evolution MVP | tracker Blocks 0–6 accepted through `4a33cd9344f0fbb1d1feaa6caac13521eb3237f3` | adapt | 0–4 | generalize from Factory capability change to target-product program evolution |
| Current control-plane baseline | `4ae6a61b15f4c21604e7b9c9912a6272a3bf2330` | reuse | 0 | freeze current schemas, owners, tests, and telemetry availability |
| Adaptive decision and program-revision machinery | accepted control-plane history through `525024ee3897dd037b8017d20d5ce3b5c8254bea` | reuse | 5–7 | add prospective portfolio placement without weakening current correction |
| Automatic release and supervisor refresh line | `codex/auto-activation-main-integration` at planning-time head `3b155851991ddc390063ac60c5dcec6e73bfbed9` | adapt | 9 | integrate final accepted successor, do not duplicate its release orchestration |
| Active installed three-skill release | `75481f37c3b6-e3e2f2705136`, source `75481f37c3b64d887fdb7fa72fe2742f033c972d` | migrate | 9 | retain historical readability/rollback and emit a four-skill successor |
| Existing fixed three-skill manifest implementation | `scripts/skill_release.py` `SKILLS` tuple and manifest validator | remediate | 9 | version exact release-set schema and stable fourth discovery link |
| Current token/cost report evidence | `weekly_report.py` resource projection and limitation contract | adapt | 3 | distinguish observed actuals from estimates and measure useful yield |
| Earlier “no fourth skill” MVP boundary | Factory Evolution MVP non-goal | retire | 0 | superseded by this exact direct-user fourth-skill instruction; retain as history |
| Tracker-Authoring Supervision implementation tracker | `a01417376b458325b6554ab6007d2a7d145a785d`; document SHA-256 `dc87fde4b7fe4017a82426ad0199dd2ef226eb8d9a658d348ec0aea6ea2dd424` | merge and preserve as history | 6, 8, 11, 14 | implement the exact mapping below through existing authoring/supervision owners; keep the profile independently usable for consequential non-RSI authoring |
| Selection-Quality RSI and Supervision implementation tracker | `4df42f757cb71fd7ebaf30c8275d18f73049fb3b`; document SHA-256 `e4a33fcb636980a6e99a99fd31ffb6d58f72cf7636234bb919971dd39776fd75` | split, merge, and insert through the exact map below | 5–6, 11–14 | preserve online selection review, tracker-authoring review, outcome evaluation, policy comparison, dogfood, and terminal acceptance as distinct owner boundaries |

### Direct-user amendment: tracker-authoring supervision capability map

This exact old-to-new map preserves every still-valid requirement from
`docs/software-factory-tracker-authoring-supervision-implementation-tracker.md`.
That planning tracker is superseded as an execution plan only by this map; it
remains unchanged historical design evidence. No accepted or in-flight RSI
evidence is rewritten.

| Standalone source capability | RSI destination | Preserved requirement and acceptance effect |
|---|---|---|
| Block 0: authoring target/profile, program-quality rubric, evidence-bound dispositions, checkpoints, writer separation, and implementation-run default | Blocks 6 and 8 | Block 6 makes the author-owned candidate and readiness packet implementation-ready; Block 8 owns the explicit profile, rubric, canonical review/event contract, and backward-compatible default. Structural validity remains necessary but insufficient. |
| Block 1: explicit fail-closed target kind in canonical policy/status, blank active-Block support, legacy default, and read-only reviewer permissions | Block 8 | `tracker-authoring` and `implementation-run` remain distinct in the existing supervision owner; legacy state defaults without rewriting history; no supervisor tracker/repository write is allowed. |
| Block 2: independent program, feature, Block, owner, architecture, dependency, acceptance, and Stop review with narrow target-owned correction | Block 8 | Terra remains mechanical; XHigh and Max independently review direct mission, exact tracker delta, and bounded live repository evidence; steers remain open until a later exact target delta proves effectiveness. |
| Block 3: exact implementation-readiness completion, current verifier/repository roots, open-finding reconciliation, and proportionate authoring lifecycle | Blocks 6 and 8 | The author produces exact candidate/verifier/diff evidence; supervision owns independent completion roots, profile-aware lifecycle, and fail-closed shutdown without weakening implementation-run reporting. |
| Block 4: underreach, overreach, malformed-Block, and sound-plan forward cases; one bounded lifecycle; mapped compatibility; demonstrated docs | Blocks 11 and 14 | Dogfood covers both RSI-generated and consequential user-seeded authoring, target-owned correction, no-intervention sound plans, completion, and lifecycle; terminal proof validates compatibility and documents only demonstrated behavior. |
| Cross-cutting ordinary-authoring independence | Blocks 6, 8, 11, and 14 | Consequential user-seeded tracker authoring can invoke the same profile without RSI; routine/low-consequence authoring may retain one-shot `quality-check`; no mandatory continuous supervision or RSI prerequisite is created. |

Dependency effect: accepted Blocks 0–2 and open Blocks 3–4 retain their
exact contracts and direct implementation bounds. Renumbering begins only after
Block 4; the standing bounds remain exactly Blocks 0–4, with Block 3 as the next frontier.
Future authoring-supervision work maps to Blocks 6, 8, 11, and 14.

Amendment acceptance evidence: exact candidate
`5a0e8347f339d08aa66f00efb662c2f9cd647aab` was non-force pushed on
`codex/product-program-evolution-blocks-0-4` and independently accepted by
`/root/amendment_review` with no findings. The reviewer read both complete
trackers, confirmed byte preservation of accepted Blocks 0–1 and prospective
Blocks 2–4, verified every standalone Block 0–4 capability against the map,
confirmed independent non-RSI operation and owner separation, and passed the RSI
full verifier (12 Blocks), standalone inherited/core verifier (5 Blocks), diff
checks, and clean exact worktree proof.

### Direct-user amendment: complete selection-quality capability map

The source tracker at exact `4df42f7` was read in full and is consumed as source
planning evidence only. No source Block is rejected or treated as already
implemented. Its complete capability maps as follows:

| Selection-quality source Block | RSI destination | Integration disposition |
|---:|---:|---|
| 0 | 5, 12, 13 | split: Block 5 owns selection-review packet/result and online dispositions; Block 12 owns outcome/effectiveness lineage; Block 13 owns selector-policy/candidate/comparison lineage. All remain derived and nonauthorizing. |
| 1 | 5 | inserted intact in purpose: one canonical `product-program-selection` profile, currentness gate, XHigh review, bounded Max adjudication, open finding lineage, and no supervisor writes. |
| 2 | 6, 8 | merged by owner: Block 6 consumes only a current accepted selection review at placement/application; Block 8 independently reviews the authored tracker structure. Neither acceptance substitutes for the other. |
| 3 | 12 | inserted after dogfood/outcome: distinct evaluator binds exact forecasts, program/outcome/resource evidence, supported counterfactuals, and truthful inconclusive cases. |
| 4 | 13 | inserted after effectiveness acceptance: at most one versioned policy candidate, retained held-out comparison, one forward/shadow cycle, independent evaluator, application handoff, and rollback identity. |
| 5 | 11 | merged into the existing dogfood owner and expanded to exactly two material cycles plus one unchanged replay, while keeping selection, authoring, implementation, outcome, evaluation, and policy comparison separately attributable. |
| 6 | 14 | merged into the existing final owner: exact source review, four-skill release, safe compatible refresh, rollback, installed selection/effectiveness checkpoint, and genuine terminal lifecycle proof. |

The resulting future dependency chain is `4 → 5 → 6 → 7`, `6 → 8`,
`7 + 8 → 9`, `1 → 10`, `9 + 10 → 11 → 12 → 13 → 14`. Online selection
supervision therefore protects the current choice; tracker-authoring supervision
protects the resulting program structure; implementation supervision protects
execution; and post-outcome selector RSI improves future choices. The shared
canonical supervision roles/ledger, tracker writer, source owner, outcome owners,
Factory Evolution, release pointer, and safe refresh owner are reused; no parallel
writer, monitor, ledger, scheduler, policy store, or release owner is added.

## 5. Scope, non-goals, and proportionality

### In scope

- One new `evolve-product-program` skill with deterministic contracts, references,
  tests, and invocation guidance.
- Recursive reflection over target-product behavior, implementation progress,
  architecture, feature areas, refactors, simplification/removal, operations,
  experiments, and other supported progress.
- Multiple visible candidates, counterexamples, protected-capability analysis,
  explicit selection dimensions, and a retained no-change candidate.
- Consequential feature/program selection grounded in current observable behavior,
  features/capabilities, and planned, active, completed, accepted, rejected,
  retired, and superseded tracker inventories.
- Independent pre-authoring selection/design supervision with exact accepted,
  revise, rejected, and safe-deferred dispositions and later-delta correction.
- One selected program portfolio containing current-program revision, successor,
  sequential, parallel, experimental, deferred, and no-op placements.
- Full tracker evolution: add, remove, reorder, modify, split, merge, reopen,
  retire, supersede, or create work through the existing authoring owner.
- Transparent learned resource bounds based on evidence quality, useful outcome,
  elapsed time, tokens, commands, tools, validation, review, rework, incidents,
  rollbacks, user corrections, reuse, and uncertainty.
- Cheap in-run and terminal invocation from implementation and supervision.
- Outcome-linked selection-effectiveness evaluation, supported counterfactuals,
  and versioned selector-policy comparison on retained held-out and forward/shadow
  evidence without an opaque aggregate score.
- Explicit, independently operable tracker-authoring supervision for
  consequential RSI-generated and user-seeded authoring, with exact
  implementation-readiness completion and target-owned correction evidence.
- Four-skill release, rollback, stable discovery, automatic refresh, and live-role
  currentness.

### Out of scope

- Requiring evolution before the user's first tracker can be authored.
- An unbounded autonomous idea loop, novelty quota, permanent background model,
  arbitrary web/product research, generalized project-management service, or
  portfolio dashboard.
- An opaque quality/utility score that collapses evidence, value, cost, risk, and
  uncertainty into one unexplained number.
- Collapsing feature selection, online selection supervision, tracker-authoring
  supervision, implementation supervision, outcome evaluation, and selector-
  policy adoption into one role or acceptance.
- Treating projected tokens or API-equivalent cost as actual provider usage,
  billing, or spend authority.
- Letting prospective feature work cancel, hide, or indefinitely preempt current
  requested work.
- A second tracker writer, range ledger, supervision ledger, release owner,
  task scheduler, telemetry database, or permissions system.
- Automatic external communication, deployment, credential use, destructive
  mutation, budget expansion, or material product-goal change.
- Making continuous tracker-authoring supervision mandatory for routine or
  low-consequence trackers, or treating RSI as a prerequisite for independently
  user-seeded authoring.

### Proportionality

Generalize the already accepted recursive learning core and compose existing
execution owners. The fourth skill is a method and bounded derived-artifact owner,
not a new service. Deep reflection runs only after an exact material-change or
terminal trigger; unchanged state is O(1) identity comparison and a no-op.

## 6. Block execution contract

1. Execute Blocks 0–14 in dependency order as one full-tracker request.
2. Re-read the selected Block and inspect the live repository, installed release,
   active automatic-release branch, and current accepted evidence before editing.
3. Preserve unrelated, accepted, rejected, and in-flight work. Do not rewrite the
   earlier Factory Evolution MVP or its evidence to imply this capability existed.
4. Keep the first loop user-seeded: tracker authoring may begin directly from
   exact user intent without invoking recursive evolution first.
5. Make every recursive invocation currentness-bound and idempotent. An unchanged
   evidence/program fingerprint produces no model, candidate, authoring, tracker,
   thread, or supervisor work.
6. Keep divergent generation and convergent selection separately attributable.
   The generator may not select, implement, author, or promote its own candidate.
7. Include `continue unchanged` and removal/simplification candidates when they
   are supported. Do not reward novelty, volume, or architectural generality.
8. Current requested work remains authoritative during prospective reflection.
   Preempt or revise it only for a proven prerequisite, correctness defect,
   protected-capability loss, invalid architecture/acceptance contract, or an
   exact later direct-user goal change.
9. Apply structural work only through `author-implementation-trackers` and its
   program-revision review/application owner. Preserve an explicit old-to-new map
   and append-only accepted/rejected history.
10. A full-tracker intent includes accepted inserted, split, merged, reordered,
    or appended mission-preserving work through the new terminal outcome. An
    explicit bounded range gains only required prerequisites unless a separately
    authorized successor range is admitted.
11. Multiple tracker lanes require an acyclic dependency graph, explicit owners,
    integration point, shared-resource exclusions, currentness roots, resource
    ceilings, Stops, and rollback/retirement. No second production authority is
    created by planning parallel work.
12. Allocate resources only within current permission and operator ceilings.
    Preserve observed and estimated evidence classes separately and retain the
    rationale for every widening, parallel lane, experiment, or early stop.
13. Run likely-mutating product/program review before expensive mapped validation.
    Freeze exact candidates; changed source, evidence, portfolio, budget, tracker,
    or owner state stales only affected proof.
14. Commit each cohesive validated slice and non-force push regularly. Before
    every Block transition verify branch, worktree, upstream, accepted evidence,
    current implementation range, and safe frontier.
15. Before terminal response, require current outcome proof for the new skill,
    all integration hooks, four-skill release, installed roots, role refresh,
    dogfood portfolio, resource evidence, and unchanged replay. If work remains,
    continue without asking for manual Resume.
16. Consequential authoring selected by the program binds the explicit
    `tracker-authoring` supervision profile before authoring completion. The same
    profile remains directly invocable for consequential user-seeded authoring;
    routine work may use the existing one-shot independent quality check.
17. Authoring corrections are target-owned and remain open in canonical
    supervision state until a later exact tracker delta and independent review
    prove effectiveness. A steer, green structural verifier, author commit, or
    completion narrative cannot close them by itself.
18. Freeze every consequential candidate set and proposed portfolio with exact
    forecasts, rejected/deferred alternatives, inventory roots, direct mission,
    dependencies, budgets, Stops, and current-range proof. It is nonauthorizing
    until the distinct online selection review is accepted.
19. Keep selection effectiveness separate from policy revision. Evaluate exact
    realized outcomes first; then produce at most one versioned policy candidate,
    compare it independently on chronological retained held-out cases and one
    subsequent/shadow live cycle, and leave the incumbent current on mixed,
    inconclusive, gaming, leakage, or protected-regression evidence.

### Program-evolution disposition and continuation contract

Every deep evolution cycle selects exactly one current disposition:

- `continue-program-unchanged` — no candidate exceeds its evidence, integration,
  opportunity, and resource cost;
- `remediate-current-block` — route a proven active defect through the existing
  inline/candidate owner without structural tracker change;
- `revise-current-program` — route an accepted structural revision to the
  tracker-authoring owner at the earliest safe application boundary;
- `start-successor-program` — author and admit one later tracker without delaying
  the current outcome;
- `start-program-portfolio` — author multiple sequential or parallel trackers
  with one dependency/resource/integration contract;
- `run-bounded-experiment` — gather missing decision evidence without granting
  production or tracker authority;
- `safe-defer-open-fact-or-authority` — preserve the candidate and exact revisit
  trigger while continuing every unaffected frontier; or
- `request-material-goal-authority` — only for a product-purpose, irreversible,
  reserved-effect, or user-specific tradeoff not resolved by current sources.

Current-tracker revision may add, remove, reorder, modify, split, merge, reopen,
retire, or supersede work. Removal never deletes history: every old Block maps to
a retained, replaced, split, merged, retired, or superseded successor. Directly
requested capability may be retired only when exact evidence proves equivalent
coverage, supersession, incompatibility with a later direct instruction, or a
material decision returned to the user. Accepted evidence is reopened only across
the mapped dependency closure of a concrete current defect.

### Resource-learning and portfolio contract

- Preserve separate dimensions for product effect, protected-capability result,
  evidence strength, recurrence/reach, compounding value, reuse, elapsed time,
  actual or estimated tokens, command/tool work, validation/review passes,
  integration cost, rework, incidents, rollbacks, user corrections, uncertainty,
  reversibility, and opportunity cost.
- Never compute a hidden aggregate quality score. Selection and budget records
  expose each dimension, its evidence class, and its role in the decision.
- Calibrate estimates only from exact completed examples. A candidate with weak
  evidence receives an experiment budget, not an implementation presumption.
- Limit active portfolios, trackers, candidate lanes, model passes, elapsed time,
  and writable scopes. Parallelism expands only after prior disjoint lanes show
  clean integration or a current experiment proves the benefit.
- Stop a low-yield or regressing lane early, retain truthful evidence, preserve
  unaffected work, and return unused capacity to the current safe frontier.
- Resource availability never creates relevance or authority; high-value work may
  remain deferred when its owner or evidence is unavailable.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
- External/domain revision or root: `<value or not-applicable with reason>`
- Inputs: `<source, tracker, policy, event, report, release, telemetry roots>`
- Outputs: `<contract, skill, candidate set, portfolio, budget, handoff roots>`
- Focused validation: `<commands and results>`
- Mapped validation: `<selection, commands, counts, and results>`
- Candidate freeze: `<commit/content roots and currentness>`
- Remediation closure: `<finding-to-change-to-proof matrix or not-applicable>`
- Resource posture: `<ceilings, evidence classes, actual use, useful yield>`
- Independent review: `<generator, selector, implementer, evaluator identities>`
- Retained open work: `<candidate, deferred portfolio, or none>`
- Decision/continuation posture: `<disposition, placement, safe frontier, trigger>`
- Post-block audit: `<accepted, reopened, or blocked with reason>`
- Git durability: `<commit, branch, upstream, push>`
```

## 7. Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Freeze the recursive product-program evolution contract | — | `accepted` |
| 1 | Build the fourth skill and deterministic program-evidence packet | 0 | `accepted` |
| 2 | Add self-reflection and divergent future-work generation | 1 | `accepted` |
| 3 | Measure outcome quality, resource use, and useful-yield priors | 1 | `not-started` |
| 4 | Select, budget, schedule, and place one program portfolio | 2, 3 | `not-started` |
| 5 | Supervise consequential feature/program selection before authoring | 4 | `not-started` |
| 6 | Apply tracker evolution and authoring-readiness handoff | 5 | `not-started` |
| 7 | Invoke evolution from implementation boundaries | 6 | `not-started` |
| 8 | Supervise evolution and consequential tracker authoring | 6 | `not-started` |
| 9 | Orchestrate sequential and parallel tracker portfolios | 7, 8 | `not-started` |
| 10 | Extend release ownership from three to four skills | 1 | `not-started` |
| 11 | Dogfood recursion, selection/authoring supervision, and recovery | 9, 10 | `not-started` |
| 12 | Evaluate selection effectiveness and supported counterfactuals | 11 | `not-started` |
| 13 | Revise and compare selector policy without self-evaluation | 12 | `not-started` |
| 14 | Freeze, review, release, refresh, and prove effectiveness | 13 | `not-started` |

Required order:

`0 → 1 → 2 → 4 → 5 → 6 → 7 → 9 → 11 → 12 → 13 → 14`, with
`1 → 3 → 4`, `6 → 8 → 9`, and `1 → 10 → 11`.

## Active-program revision control

- Terminal Block: `14`
- Required order: `0,1,2,3,4,5,6,7,8,9,10,11,12,13,14`
- Prose-reference Blocks: `0,1,2,3,4,5,6,7,8,9,10,11,12,13,14`
- Source-map Blocks: `0,1,2,3,4,5,6,7,8,9,10,11,12,13,14`
- Verification-matrix Blocks: `0,1,2,3,4,5,6,7,8,9,10,11,12,13,14`
- Handoff Block: `3`

### Program revision history

| Revision ID | Predecessor tracker SHA-256 | Current structure SHA-256 | Block map SHA-256 | Affected Blocks | Resume Block |
|---|---|---|---|---|---:|
| `PROGRAM-REVISION-SELECTION-QUALITY-0001` | `5060f20bd6988d2f1eb67c5bb1dc07da2c24c415f2dfe30abb2591b0a0e707e6` | `5d498bd2b1ffc84e57c6e5a5036d5efb4d57fe5fd0edc09b957e22809dbdd337` | `edf1c8bef986a62cc115624cdebd87c921a6246120c27072b673c7041516ea82` | `3,4,5,6,7,8,9,10,11,12,13,14` | `3` |

## Program source map

| Block | Current source basis |
|---:|---|
| 0 | Accepted recursive contract and owner map at exact Block 0 evidence. |
| 1 | Accepted deterministic fourth-skill evidence packet at exact Block 1 evidence. |
| 2 | Accepted concrete-inventory reflection and independent semantic-review contract at exact Block 2 evidence. |
| 3 | Existing typed outcome/resource/useful-yield requirements, preserved unchanged. |
| 4 | Existing independent portfolio selection/budget/scheduling/placement requirements, preserved unchanged. |
| 5 | Selection-quality source Blocks 0–1: exact review packet/result and canonical online selection profile. |
| 6 | Selection-quality source Block 2 plus accepted authoring-supervision Block 0/3 capabilities. |
| 7 | Existing implementation-boundary invocation owner, renumbered only. |
| 8 | Accepted standalone authoring-supervision Blocks 0–3, distinct from online selection review. |
| 9 | Existing sequential/parallel portfolio orchestration owner, renumbered only. |
| 10 | Existing four-skill release migration owner, renumbered only. |
| 11 | Selection-quality source Block 5 plus accepted standalone authoring-supervision dogfood requirements. |
| 12 | Selection-quality source Blocks 0 and 3: exact outcome/effectiveness lineage and supported counterfactuals. |
| 13 | Selection-quality source Blocks 0 and 4: versioned selector policy and retained/forward comparison. |
| 14 | Selection-quality source Block 6 plus existing final release/refresh/rollback/terminal owner. |

## Program verification matrix

| Block | Current verification basis |
|---:|---|
| 0 | Exact schema/owner/no-op and negative direct-write proof retained. |
| 1 | Deterministic packet/currentness/containment and accepted review proof retained. |
| 2 | Concrete inventory, ladder closure, independent semantic receipt, and adversarial proof retained. |
| 3 | Typed evidence classes, unavailable-versus-estimated separation, and useful-yield tests. |
| 4 | Transparent dimension selection, budgets, dependency graph, placement, and no-op tests. |
| 5 | Bad/sound/revise/reject/defer/currentness/current-work online selection-review cases. |
| 6 | Accepted-review handoff, distinct authoring review, range map, stale and duplicate application tests. |
| 7 | Material/terminal/unchanged invocation, deduplication, and safe-continuation tests. |
| 8 | Program/feature/Block/owner/architecture challenge and implementation-readiness lifecycle tests. |
| 9 | Sequential/parallel dependency, writable-scope, integration-owner, interruption, and retirement tests. |
| 10 | Four-skill manifest, historical rollback, staged promotion, discovery, and refresh tests. |
| 11 | Two material cycles plus unchanged replay; poor/sound selection, authoring, execution, outcome, and recovery proof. |
| 12 | Effective/mixed/ineffective/inconclusive, forecast, correction, and supported-counterfactual blind cases. |
| 13 | Held-out leakage, gaming, protected regression, incumbent/candidate, shadow cycle, and rollback tests. |
| 14 | Exact source/release/install/refresh/rollback/current-cycle/terminal lifecycle proof. |

## Block 0 — Freeze the recursive product-program evolution contract

Status: `accepted`

### Objective

Define one exact product-program recursion contract and ownership map that extends
accepted RSI behavior without granting derived artifacts downstream authority.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: establish target-product and implementation-program
  evolution as a first-class fourth-skill capability.
- Potential capability loss or regression: a broad contract could duplicate
  Factory Evolution, tracker authoring, supervision, or release authority.
- Protected-capability effect: preserves first-loop cold start, direct mission,
  existing owners, accepted history, no-op convergence, and current-run priority.
- Architecture and operating-model effect: moves reusable recursive semantics to
  a target-profiled core while keeping Factory and product adoption paths distinct.
- Tradeoff and source evidence: direct user authority supports one new skill;
  existing Factory Evolution supplies the ladder, so a new service or ledger is
  disproportionate.

### Inputs and dependencies

- Direct-user product-program evolution agreement captured in this tracker.
- Planning baseline, active release, and predecessors in Section 4.

### Required work

- Freeze exact roles, artifact classes, state transitions, dispositions, placement
  categories, currentness, deduplication, no-op, history, and authority semantics.
- Define target profiles so Factory capability evolution and target-product
  evolution share the ladder without sharing adoption authority.
- Define the fourth skill's input/output schemas and sibling-skill interfaces.

### Scope and non-goals

- In scope: contracts and source/owner mapping.
- Not in scope: executable packet generation, cognitive candidate work, tracker
  edits, release changes, or a live recursive cycle.
- New machinery is permitted only when the objective cannot be met through an
  existing owner and the acceptance-critical need is stated here.

### Deliverables and recorded state

- `evolve-product-program/references/product-program-evolution-contract.md` and
  exact contract fixtures/source map.

### Resource and economy contract

Read each existing contract once and retain exact roots. No broad history replay;
widen only when one required field cannot be sourced from current accepted code.

### QA and independent review

Mechanical schema review plus independent architecture review for duplicate or
missing ownership.

### Acceptance

- Every proposed fact/write resolves to one owner, every transition has a Stop,
  and unchanged recursion is a deterministic no-op.

### Negative tests

- Reject a contract that lets evolution write trackers, source, supervision,
  releases, automations, or external effects directly.

### Completion evidence

- Repository commit: `f09ce6f0ddabf79905a7953a146f793a62fad9cd`.
- External/domain revision or root: not applicable; Block 0 is a source-only
  contract and performs no release, tracker application, supervision mutation,
  automation, or external effect.
- Inputs: tracker planning snapshot `781a3b653e44bd8570809a8e4665b5e21d19b981`;
  tracker frame SHA-256 `b9b1b623b07ea316b99aeaa70c5f41a36b3f5b9f2c9e6140b9be39629513275a`;
  Factory Evolution contract SHA-256
  `8c8748cb514a3a06bb604b7d9077ce7ed6fed9b59244ff1f79bd9792cde2225b`;
  product-capability review SHA-256
  `68d255c1cd7c03b61b9278e0d1a20290c7452abb661ba00ae47d15e60bfc3017`.
- Outputs: contract SHA-256
  `53a5a0b069c7c23e736ba9d7b8579a7b187159f4d154af2573b42ef28aa73626`;
  exact schema/owner fixture SHA-256
  `42aa542fcb41d269bdbaaf613379609d2db2d6ebaa011f2ead16096b4c87a9f3`;
  immutable/live source map SHA-256
  `4eb84ed57d9f87100ebc5f850f855d49f1bd2909700552a6f72aaddfb02f0e8f`.
- Focused validation: `/usr/bin/python3 -m unittest -v
  evolve-product-program/scripts/test_product_program_contract.py` — 10 tests
  passed; source-map hashes matched; mutation cases rejected missing owners,
  extra fields, altered interfaces, missing roles, checkpoint fields, and Stops.
- Mapped validation: `python3
  author-implementation-trackers/scripts/verify_tracker.py
  docs/software-factory-recursive-product-program-evolution-implementation-tracker.md
  --profile full` — 12 Blocks, PASS before this status-only evidence update.
- Candidate freeze: commit `f09ce6f0ddabf79905a7953a146f793a62fad9cd`,
  tree `628b810555e307b2efeffa892d2c4a190207f97d`; upstream matched after
  non-force push.
- Remediation closure: exact-review findings closed by independently comparing
  fingerprint/currentness identities, freezing exact checkpoint/artifact/
  interface schemas, completing role/artifact ownership, adding mutation-based
  rejection tests, and pinning mutable tracker evidence to immutable planning
  bytes. Rejected checkpoints remain in Git history.
- Resource posture: six exact source-owner reads, one contract package, no
  cognitive candidate lane, no broad history replay, focused tests before the
  tracker verifier, and four bounded independent review passes across the
  original, remediation, interface, and immutable-source deltas.
- Independent review: `/root/block0_review` rejected `74e7ba2` and `b51ea9d`,
  accepted `18ae1be`, then accepted the delta-only immutable-source correction at
  exact revision `f09ce6f0ddabf79905a7953a146f793a62fad9cd`; final focused proof
  was 10/10 with a clean exact HEAD.
- Product-capability review:
  - Trigger: consequential Block 0 operating-model contract.
  - Frame identity: this tracker, Block 0, SHA-256
    `b9b1b623b07ea316b99aeaa70c5f41a36b3f5b9f2c9e6140b9be39629513275a`.
  - Capability added or preserved: one target-profiled recursive contract with
    cold-start, current-range, owner separation, history, and no-op convergence.
  - Paths compared: a local copied Factory contract; a bounded-general
    target-profiled contract in the new skill; modifying the existing Factory
    Evolution owner.
  - Selected level and owner: bounded-general in `evolve-product-program`; it
    reuses the accepted ladder for the named Factory and target-product profiles
    without editing or conflating their adoption owners.
  - Protected-capability result: preserved and mechanically covered at the
    contract level, including negative direct-write and self-selection paths.
  - Rejected alternatives: a local copy would drift and duplicate the ladder;
    changing the existing supervision owner would bypass the source-only boundary
    and conflate proposal with adoption.
  - Tradeoffs and uncertainty: exact schemas add deliberate rigidity; later
    Blocks may implement only these derived artifacts and must leave application
    with existing owners.
  - Frozen-candidate proof: commit `f09ce6f0ddabf79905a7953a146f793a62fad9cd`,
    focused 10/10, exact independent ACCEPT.
- Retained open work: none in Block 0; executable packet generation remains
  deliberately owned by Block 1.
- Decision/continuation posture: contract accepted; continue automatically to
  Block 1. The canonical range-binding classifier incident remains separately
  owner-routed and does not contract or stop the safe Blocks 0–4 frontier.
- Post-block audit: accepted; every required fact/write resolves to one owner,
  every transition has a Stop, unchanged recursion is a deterministic no-op, and
  prohibited downstream writes reject.
- Git durability: commits `7a659c2`, `74e7ba2`, `676448e`, `b51ea9d`,
  `18ae1be`, and `f09ce6f` are pushed on
  `codex/product-program-evolution-blocks-0-4` to
  `origin/codex/product-program-evolution-blocks-0-4`.

### Stop

Stop before creating the executable skill or producing a candidate set.

---

## Block 1 — Build the fourth skill and deterministic program-evidence packet

Status: `accepted`

### Objective

Create `evolve-product-program` and deterministically assemble one bounded,
current, content-minimized evidence packet for a target product/program.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: make recursive product/program evolution independently
  invocable from authoring, implementation, and supervision contexts.
- Potential capability loss or regression: copied Factory logic or unbounded
  target content could create drift, privacy exposure, or a fourth ledger.
- Protected-capability effect: preserves source ownership, reproducibility,
  bounded reads, explicit target identity, and derived-only status.
- Architecture and operating-model effect: adds the fourth skill directory and a
  target-profiled wrapper over the generalized evolution core.
- Tradeoff and source evidence: a separate skill gives reuse and role clarity;
  deterministic code validates/assembles evidence but does not generate judgment.

### Inputs and dependencies

- Block 0 contract and source map.

### Required work

- Add `SKILL.md`, agent metadata, references, fixtures, validator, and deterministic
  packet CLI for the new skill.
- Resolve exact mission, product sources, repository revision/tree, tracker range
  and structure, accepted/remaining frontier, current outcome, protected
  capabilities, decisions/incidents, reports, and resource evidence.
- Apply bounded no-follow/currentness reads and retain hashes/identities rather
  than target transcripts, hidden reasoning, secrets, or broad source content.
- Emit a material-change fingerprint and an O(1) unchanged result.

### Scope and non-goals

- In scope: skill package and deterministic evidence preparation/verification.
- Not in scope: semantic reflection, candidate generation, selection, tracker
  authoring, implementation, or release activation.
- Do not copy the supervision event ledger or target repository into skill state.

### Deliverables and recorded state

- `evolve-product-program/` skill package and one verified packet fixture for a
  running and a completed tracker.

### Resource and economy contract

Use bounded summaries/indexes first; load raw target evidence only for selected
IDs. One packet build per changed fingerprint; exact retry reopens existing bytes.

### QA and independent review

Focused schema/currentness/containment tests and skill validation; substantive
judgment is explicitly absent.

### Acceptance

- Packet rebuild is byte-identical from exact inputs, changes for every governing
  owner/currentness change, and remains nonauthorizing.

### Negative tests

- Reject stale tracker/range, substituted HOME/root, symlinked/unbounded inputs,
  mismatched target, copied hidden output, missing resource evidence class, and
  caller-asserted authority.

### Completion evidence

- Repository commit: `e9d0a6b6a5d7b506861947ae4d106b1876a63f05`;
  tree `421c06f92bac6b9f05b19aae99cc00c6cd227231`.
- External/domain revision or root: not applicable; Block 1 produced only the
  source skill package and derived nonauthorizing fixtures. It performed no
  release, tracker application, supervisor mutation, automation, or external
  effect.
- Inputs: accepted Block 0 contract at `f09ce6f`; immutable planning tracker
  `781a3b653e44bd8570809a8e4665b5e21d19b981`; Block 1 frame SHA-256
  `eda3aef56469064d1e42cfd6c832b9ea51634119d7a2684e2882e527102b0bf0`.
- Outputs: skill root file SHA-256
  `5e69973dcd002df84ca6fbbc9a5397e2b04502eb16eb4603cf7d0bedc219fc02`;
  packet contract SHA-256
  `3d98c84aa60c0730cb1d9c91567012a0c2fe0a805cc03ecccebd15343cf074d1`;
  deterministic CLI SHA-256
  `7891e1ce89b59c90baaa82f58f6cc89ef9bf937b6d9ae1afb5a157108a28b3d3`;
  running/completed fixture SHA-256 values
  `54a66ffdb2b0e61c14032bdbcc369bae9ff3ff249039962f67bea1c9383bed80`
  and `9617293095fe58432a6c73eb8025bc3283b1f57fc9a4e16d2fbcf963695a59dd`.
- Focused validation: `/usr/bin/python3 -m unittest -v
  evolve-product-program/scripts/test_product_program_evidence.py
  evolve-product-program/scripts/test_product_program_contract.py` — 18/18
  passed; both retained packet fixtures verified; `py_compile`, skill
  `quick_validate.py`, and `git diff --check` passed.
- Mapped validation: deterministic replay, semantic/currentness separation,
  zero-cognition unchanged result, exact repository/tracker/range derivation,
  component-wise no-follow reads, source rechecks, authority rejection, retained
  packet verification, and running/completed packet paths were exercised.
- Candidate freeze: initial commit `a09d41f` was rejected; exact successor
  `e9d0a6b6a5d7b506861947ae4d106b1876a63f05` was pushed and remained clean
  throughout fresh review.
- Remediation closure: lexical and actual-HOME containment now reject using
  component-wise `dir_fd`/`O_NOFOLLOW`; retained range is recomputed from tracker
  status/dependencies; product/resource evidence is nonempty in build and
  verification; report prose changes currentness without inventing semantic
  novelty. Direct regressions and 7/7 independent adversarial probes passed.
- Resource posture: one bounded packet build per changed identity, no semantic
  model call in this Block, 4 MiB/64-source ceilings, exact double-read
  currentness, and constant identity comparison after preparation.
- Independent review: `/root/block1_review` rejected exact `a09d41f` with four
  material findings and accepted exact successor
  `e9d0a6b6a5d7b506861947ae4d106b1876a63f05`; 18/18 focused tests, compilation,
  skill validation, two fixture verifications, 7/7 adversarial probes, and clean
  diff all passed without reviewer edits.
- Product-capability review:
  - Trigger: consequential fourth-skill/evidence-owner creation.
  - Frame identity: immutable Block 1 planning bytes at `781a3b6`, SHA-256
    `eda3aef56469064d1e42cfd6c832b9ea51634119d7a2684e2882e527102b0bf0`.
  - Capability added or preserved: independently invocable, reproducible,
    content-minimized product/program evidence with exact no-op convergence and
    no downstream authority.
  - Paths compared: copy Factory evidence logic into supervision; extend an
    existing sibling writer; create the bounded deterministic owner in the new
    skill.
  - Selected level and owner: the bounded owner in `evolve-product-program`,
    leaving semantic reflection and every canonical write to later or existing
    owners.
  - Protected-capability result: source ownership, explicit target/range,
    currentness, content minimization, first-loop independence, and derived-only
    status are preserved and covered by negative tests.
  - Rejected alternatives: copying supervision logic would drift and conflate
    evidence with review; extending an existing writer would weaken separation.
  - Tradeoffs and uncertainty: exact schemas and repeated source reads cost
    bounded local I/O; actual provider usage remains unavailable and is retained
    only as typed source evidence for Block 3.
  - Frozen-candidate proof: exact `e9d0a6b6a5d7b506861947ae4d106b1876a63f05`,
    focused 18/18, independent ACCEPTED.
- Retained open work: semantic interpretation and candidates remain exclusively
  in Block 2; resource projection remains in Block 3; no Block 5–11 owner was
  edited.
- Decision/continuation posture: accept Block 1 and enter the direct-user
  tracker-amendment boundary before Block 2; the exact Blocks 0–4 implementation
  range remains intact and needs no manual Resume.
- Post-block audit: accepted; packet rebuild is deterministic, every governing
  semantic/currentness class changes the correct identity, packet verification
  rejects forged frontier/resources/authority/containment, and outputs remain
  nonauthorizing.
- Git durability: `a09d41f` and remediation `e9d0a6b` are pushed on
  `codex/product-program-evolution-blocks-0-4` to its matching `origin` upstream.

### Stop

Stop before interpreting the packet or proposing work.

---

## Block 2 — Add self-reflection and divergent future-work generation

Status: `accepted`

### Objective

Generate a visible, varied, evidence-bound set of materially plausible future
product/program candidates without choosing or authorizing one.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the system reason beyond incremental tracker
  mechanics toward features, capability areas, architectures, refactors,
  simplification, removal, operations, experiments, and stopping.
- Potential capability loss or regression: novelty bias or unsupported ideation
  could create distraction, over-architecture, or mission drift.
- Protected-capability effect: retains product thesis, direct intent, current
  commitments, counterexamples, uncertainty, and a no-change alternative.
- Architecture and operating-model effect: introduces a nonauthorizing divergent
  cognitive phase distinct from selection and implementation.
- Tradeoff and source evidence: higher-resolution reasoning is useful for
  discovery but runs only on material evidence and under an explicit candidate
  and model-pass ceiling.

### Inputs and dependencies

- Block 1 verified current packet.

### Required work

- Extend the accepted observation/lesson/meta-pattern/capability-gap ladder for
  target-product and implementation-program reflection.
- Require candidates from multiple supported categories plus `continue unchanged`
  when evidence permits; never require a novelty quota.
- Bind each candidate to desired effect, affected users/capabilities, evidence,
  counterexamples/search, protected behavior, architecture level, implementation
  and evaluation owners, uncertainty, smallest sufficient change, and falsifiable
  outcome.
- Keep generator identity distinct from selector, author, implementer, and
  evaluator identities.

### Scope and non-goals

- In scope: divergent semantic review and candidate validation.
- Not in scope: ranking, budget allocation, tracker placement, source changes, or
  automatic adoption.
- Do not expand beyond the product mission merely to populate candidate types.

### Deliverables and recorded state

- Rooted reflection/candidate-set artifact and positive, contrary, and no-op
  fixtures.

### Resource and economy contract

One bounded high-resolution generation pass per changed packet, a declared
candidate ceiling, and at most one counterexample widening pass. Reuse unchanged
lessons/candidates by exact root.

### QA and independent review

Independent review challenges source support, underreach, novelty bias,
over-architecture, missing alternatives, and generator self-selection.

### Acceptance

- Candidate sets are diverse where evidence supports diversity, include contrary
  evidence, remain mission-contained, and confer no selection authority.

### Negative tests

- Reject a single unexplained candidate, invented product doctrine, missing
  no-change comparison, unsupported generalized platform, self-selected idea, or
  candidate without counterexample posture.

### Completion evidence

- Repository commit: `5d3df57e5d04e50c30bbd0fb98ff855b75f048e6`;
  tree `70928e1eade36eb84c1b7ca2fdced3d0ff621d12`.
- External/domain revision or root: not applicable; Block 2 produced only the
  source skill, derived reflection artifacts, and tests. It performed no tracker
  application, implementation dispatch, supervision mutation, release,
  automation, message, or external effect.
- Inputs: accepted Block 1 packet owner at `e9d0a6b`; exact reflection packet
  fixture SHA-256
  `9031e46cc6dcfe50e3a64da983f5ce34a0c85fa1257c72d8bd66d9547110b0bd`;
  hash-bound concrete product/program inventory SHA-256
  `907b281fab327cca700019ff6883bbf2c312a49dc0e9dd2b19de49517f09051b`.
- Outputs: reflection CLI SHA-256
  `6569741d7256ccbfcf0ea867598f6d49ada4ccea443668974632a35f010af1c8`;
  reflection contract SHA-256
  `1d997e8e8c670031bbcef5912aedbb4d1f20bb73cbde65d0440a5a012faa9f06`;
  independently reviewed positive/contrary/no-op artifact SHA-256 values
  `5d784a97310f0882e25f2b604317af41044958672aa2ac142eb1ed82b75c5392`,
  `80ded9876603494b9e467fb2c1167220477db2836eec0b57706b6e0490ad02a1`,
  and `db1804c400c2722bdce7bbdb3bf8c5d742f7fedff84e1b8a60f000b4265ea722`.
- Focused validation: `/usr/bin/python3 -m unittest discover -s
  evolve-product-program/scripts -p 'test_*.py'` — 31/31 Block 0–2 tests
  passed; `py_compile`, skill `quick_validate.py`, three retained fixture
  verifications, full CLI build/review/verify/reuse, and `git diff --check`
  passed.
- Mapped validation: exact one-pass/candidate ceilings, diverse/no-change paths,
  concrete evidence-linked behavior/user/feature/capability and seven-state
  tracker inventory, report-only/dangling evidence rejection, observation to
  lesson to meta-pattern to gap reachability, per-gap transitive closure,
  contrary retention, distinct roles, independent semantic acceptance, stale
  root rejection, and zero-model-call exact reuse were exercised.
- Candidate freeze: initial `e525ff7` was rejected; remediation `0d9f751` and
  `3eba462` were rejected with narrower residuals; exact successor `5d3df57` was
  pushed and remained clean throughout the final independent review.
- Remediation closure: exact inventory records replace asserted role labels;
  every tracker state is present once, evidence-backed, and cross-state unique;
  candidate users/capabilities resolve to the inventory; every changed ladder is
  closed transitively; contrary records remain visible; and lexical checks are
  backed by an exact independent semantic receipt whose reviewer is distinct
  from generator, selector, author, implementer, and evaluator.
- Resource posture: one bounded high-resolution generation pass, at most one
  counterexample widening pass, candidate ceiling 1–12, one exact independent
  semantic review, constant-root reuse with zero model calls, and no prospective
  selection/budget/scheduling work.
- Independent review: `/root/block2_review` rejected exact `e525ff7`, `0d9f751`,
  and `3eba462`, then accepted exact
  `5d3df57e5d04e50c30bbd0fb98ff855b75f048e6` with no findings; the final pass
  reproduced cross-state uniqueness, manifest length/hash binding, concrete
  inventory, semantic-review, authority, and transitive-ladder probes, with
  31/31 tests and exact upstream equality.
- Product-capability review:
  - Trigger: consequential semantic reflection/candidate-generation capability.
  - Capability added or preserved: evidence-bound reflection over actual product
    behavior, features, users, capabilities, all tracker states, contrary
    evidence, and a mandatory no-change alternative.
  - Paths compared: opaque role assertions; generator-only lexical prohibition;
    concrete inventories plus an exact independent semantic receipt.
  - Selected level and owner: the concrete bounded reflection owner inside
    `evolve-product-program`, with semantic acceptance separate from generator
    and all future selection/application owners.
  - Protected-capability result: direct mission, current work, exact lifecycle
    inventory, contrary evidence, no-change, and nonauthorizing status are
    preserved and mechanically/adversarially covered.
  - Rejected alternatives: opaque labels cannot prove actual inventory;
    blacklist-only prose checks cannot prove divergent intent; a generator-owned
    acceptance bit would be self-review.
  - Tradeoffs and uncertainty: exact inventory schemas are deliberately rigid
    and semantic review costs one bounded independent pass; later Blocks alone
    may measure resources and select a portfolio.
  - Frozen-candidate proof: exact `5d3df57`, focused 31/31, independent ACCEPTED.
- Retained open work: outcome/resource/useful-yield evidence remains Block 3;
  ranking, budgets, scheduling, and placement remain Block 4; Blocks 5 onward
  remain outside the active implementation range.
- Decision/continuation posture: accept Block 2 and enter the direct-user
  selection-quality tracker-amendment boundary before Block 3; no manual Resume.
- Post-block audit: accepted; candidate sets are diverse when supported, contain
  contrary and no-change evidence, remain mission-contained, and cannot verify
  or reuse without exact independent non-selection acceptance.
- Git durability: Block 2 commits `e525ff7`, `0d9f751`, `3eba462`, and `5d3df57`
  are pushed on `codex/product-program-evolution-blocks-0-4` to its matching
  `origin` upstream.

### Stop

Stop before selecting, budgeting, or scheduling candidates.

---

## Block 3 — Measure outcome quality, resource use, and useful-yield priors

Status: `not-started`

### Objective

Build a transparent evidence projection that relates prior work classes and
resource use to observed product and implementation outcomes.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: allocate future exploration and execution capacity
  from demonstrated useful output rather than fixed intuition alone.
- Potential capability loss or regression: misleading estimates or an opaque
  score could optimize activity, speed, or low cost instead of product value.
- Protected-capability effect: preserves separate quality/resource dimensions,
  evidence-class labels, uncertainty, rare-high-value work, and operator ceilings.
- Architecture and operating-model effect: adapts existing supervision/report
  evidence into a derived budgeting prior without a telemetry database.
- Tradeoff and source evidence: historical events and reports are sufficient for
  bounded priors; they do not support claims of actual provider billing when only
  projections exist.

### Inputs and dependencies

- Block 1 packet schema and current supervision/report owners.

### Required work

- Derive per-work-class evidence for elapsed time, actual/provider-reported or
  estimated tokens, commands/tools, validation/review, rework, reopened findings,
  incidents, rollbacks, user corrections, reuse, outcome completion, product
  effect, and protected-capability result.
- Preserve `observed`, `provider-reported`, `estimated`, `inferred`, and
  `unavailable` evidence classes with versioned estimation profiles.
- Define useful-yield comparisons and uncertainty without an aggregate score or
  false precision.
- Add cheap currentness and immutable/rebuildable derived records.

### Scope and non-goals

- In scope: evidence projection and budgeting priors.
- Not in scope: provider billing, spend authorization, a telemetry service,
  dashboards, organization-wide benchmarking, or resource allocation itself.
- Do not penalize relevant long work or reward fast irrelevant work.

### Deliverables and recorded state

- Resource/outcome evidence schema, builder, fixtures, and limitation contract.

### Resource and economy contract

Batch existing event/report reads once, reuse accepted aggregates, and recompute
only affected work-class rows after source-root change.

### QA and independent review

Mechanical arithmetic/root tests plus independent review of evidence labels,
causal claims, missing data, and perverse incentives.

### Acceptance

- Every budgeting input is traceable, typed by evidence class, uncertainty-aware,
  and incapable of masquerading as spend or scalar product truth.

### Negative tests

- Reject projected tokens labeled actual, missing estimation profile, fabricated
  outcome value, duplicate resource attribution, speed-only ranking, and a hidden
  aggregate utility score.

### Completion evidence

Pending.

### Stop

Stop before choosing a candidate or allocating a portfolio budget.

---

## Block 4 — Select, budget, schedule, and place one program portfolio

Status: `not-started`

### Objective

Independently select the best current program posture and, when warranted, one
bounded portfolio with explicit dependencies, resources, placement, and Stops.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: turn reflective possibilities into one inspectable,
  proportional product-program choice, including multiple trackers when justified.
- Potential capability loss or regression: selection may starve commitments,
  over-parallelize, hide tradeoffs, or confuse a candidate with authority.
- Protected-capability effect: preserves current range, user intent, explicit
  dimensions, independent selection, resource ceilings, and no-op eligibility.
- Architecture and operating-model effect: adds a derived portfolio DAG and
  placement handoff consumed by existing downstream owners.
- Tradeoff and source evidence: multiple trackers can increase throughput or
  clarity, but only disjoint ownership and measured capacity justify parallelism.

### Inputs and dependencies

- Block 2 candidate set and Block 3 resource/outcome evidence.

### Required work

- Compare candidates on separate product, evidence, architecture, protected,
  risk, cost, uncertainty, reversibility, integration, and opportunity dimensions.
- Select one disposition from the tracker-level continuation contract and retain
  explicit rejected alternatives/rationale.
- For a portfolio, emit tracker candidates, dependency DAG, sequential/parallel
  groups, owners, writable scopes, integration owner, shared-resource exclusions,
  per-lane and aggregate ceilings, expected effects, Stops, rollback/retirement,
  and revisit triggers.
- Allocate a bounded exploration/execution/review budget from current ceilings and
  Block 3 priors; retain unused capacity and early-stop rules.
- Require independent selector and consequential Max adjudication where current
  evidence cannot resolve material placement or tradeoffs.

### Scope and non-goals

- In scope: convergent selection, resource allocation, dependency scheduling,
  and placement proposal.
- Not in scope: authoring trackers, opening tasks, writing source, granting
  permissions, or adopting an experiment.
- Do not select multiple trackers merely to preserve every generated idea.

### Deliverables and recorded state

- Rooted program-selection and portfolio artifact with budget and currentness.

### Resource and economy contract

One selection pass and at most one consequential adjudication per candidate-set
root. Bound active tracker count and concurrency from current operator ceilings;
unchanged selection rehydrates without a model call.

### QA and independent review

Independent mutations cover candidate omission, novelty bias, false parallelism,
resource overrun, mission drift, current-work starvation, and selector conflicts.

### Acceptance

- The selected disposition is reproducible from retained evidence, stays within
  authority/resource ceilings, and leaves one unambiguous downstream owner path.

### Negative tests

- Reject cyclic portfolios, overlapping writers, missing integration owner,
  estimated capacity presented as actual, current-range displacement, self-selected
  candidates, and portfolios whose expected benefit does not exceed coordination
  cost.

### Completion evidence

Pending.

### Stop

Stop before modifying a tracker or starting any work lane.

---

## Block 5 — Supervise consequential feature/program selection before authoring

Status: `not-started`

### Objective

Use the existing supervision owner and role topology to independently accept,
revise, reject, or safely defer an exact consequential feature/design/program
portfolio before any tracker-authoring handoff.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: catch poor product/design choices, duplicate work,
  omissions, and current-work starvation in the current cycle before they consume
  canonical authoring or implementation capacity.
- Potential capability loss or regression: an overactive reviewer could become a
  second selector, impose optional preferences, or stall sound work.
- Protected-capability effect: preserves direct mission, exact current range,
  accepted work, selector/reviewer separation, target-owned correction, and cheap
  unchanged continuation.
- Architecture and operating-model effect: adds one `product-program-selection`
  profile/phase to the canonical supervision policy/events; no parallel monitor,
  ledger, writer, policy store, or release owner.
- Tradeoff and source evidence: mandatory independent review is proportionate for
  consequential choices; explicit routine user choices retain the cheap path.

### Inputs and dependencies

- Block 4 exact selection, portfolio, forecasts, rejected/deferred alternatives,
  budgets, dependency graph, placement proposal, and currentness roots.
- Direct mission; actual current behavior/feature/capability inventory; planned,
  active, completed, accepted, rejected, retired, and superseded tracker inventory;
  current requested range; and canonical supervision policy/event heads.

### Required work

- Define exact derived `selection-review-packet` and `selection-review-result`
  schemas. Bind candidate-set root, selected portfolio, rejected/deferred
  alternatives, selection rationale, product/protected-capability/resource
  forecasts, uncertainty, architecture/owner map, dependencies, budgets, Stops,
  direct mission, inventory roots, current range, selector, and generator.
- Add a fail-closed `product-program-selection` target profile/phase to existing
  supervision. It must be automatically consumable after Block 4 freeze and
  directly bootable for consequential user-seeded selection/authoring.
- Keep Terra mechanical/currentness-only. Route each materially changed exact
  selection to an independent Sol XHigh semantic reviewer; use Sol Max only for
  a supported consequential unresolved tradeoff or bounded deterministic sample.
- Challenge duplicate existing capability, conflict/duplication with planned or
  active work, omitted required work, weak/unnecessary features, underreach,
  unsupported overreach, poor architecture, novelty bias, false parallelism,
  current-work starvation, protected regression, and mission drift.
- Record exactly `accepted`, `revise`, `rejected`, or `safe-deferred`, evidence
  roots, findings, supported alternatives, next action, and correction lineage in
  the existing event ledger. Findings stay open until a later exact selection
  delta proves correction.
- Permit the supervisor to hold the prospective handoff or route an exact
  author-owned program revision. It cannot generate/select features, write
  tracker/source, displace direct intent, or stop unaffected canonical work.
- Trigger at candidate-set freeze, selection freeze before authoring, supported
  design adjudication, tracker application currentness, and post-outcome
  effectiveness—not continuous cognition. Identical/unsupported state is a
  deterministic no-model-call no-op.

### Scope and non-goals

- In scope: online pre-authoring selection currentness, semantic review,
  adjudication, findings/correction lineage, events, status, and lifecycle.
- Not in scope: generating/selecting features, tracker/source writes, tracker-
  structure review, implementation, outcome evaluation, selector-policy learning,
  release, refresh, or ordinary-candidate Gmail.
- A prospective concern never terminalizes or displaces unaffected current work.

### Deliverables and recorded state

- Exact review schemas/builders/validators, supervision profile/policy/events,
  role prompts, helper/status projections, focused tests, and current accepted
  review receipt fixtures.

### Resource and economy contract

Cheap exact currentness gate first; one XHigh review per changed selection root;
at most one Max adjudication per unresolved root; deterministic identical reuse;
zero model calls for unchanged or unsupported evidence.

### QA and independent review

Different-role review covers poor choice, sound choice, revise, reject, defer,
unchanged, self-review, stale inventory/source, duplicate capability/current work,
omission, architecture/owner conflict, and current-range preservation.

### Acceptance

- No consequential selection reaches authoring without one current independent
  accepted review; revise/rejected/deferred selections remain nonauthorizing;
  sound choices proceed exactly once; unchanged state is a no-op; and current
  implementation remains active.

### Negative tests

- Reject caller-supplied reviewer identity, selector self-review, absent or
  contradictory inventory, unbound alternatives/forecasts, stale mission/product/
  policy/tracker/selection, optional preference as finding, closure without an
  exact later delta, duplicate review, authoring before acceptance, and supervisor
  tracker/source writes.

### Completion evidence

Pending.

### Stop

Stop before tracker authoring, tracker application, implementation, outcome
evaluation, or selector-policy learning.

---

## Block 6 — Apply tracker evolution with an authoring-readiness handoff

Status: `not-started`

### Objective

Convert an accepted placement handoff into exact current-tracker revisions or
successor tracker artifacts through the existing authoring owner, with the exact
evidence needed to bind consequential authoring supervision.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the system add, remove, reorder, modify, split,
  merge, reopen, retire, supersede, or create work as product evidence warrants
  and make consequential candidates independently implementation-ready.
- Potential capability loss or regression: unsafe mapping could erase requested
  work, falsify history, deadlock dependencies, or terminalize an open range.
- Protected-capability effect: preserves append-only evidence, direct semantic
  scope, deterministic old/new mapping, full-range continuation, currentness, and
  exact independent authoring review.
- Architecture and operating-model effect: extends the accepted program-revision
  flow; `author-implementation-trackers` remains the sole writer.
- Tradeoff and source evidence: current tracker evolution avoids artificial
  successor fragmentation, while nonblocking separable work belongs in successor
  trackers to protect current delivery.

### Inputs and dependencies

- Block 5 current accepted selection review and Block 4 exact portfolio handoff,
  or an explicit unchanged/no-authoring disposition.

### Required work

- Extend authoring schemas and method guidance for all supported revision
  operations and one-to-many/many-to-one/retired mappings.
- Bind exact selection packet/review, finding lineage, policy/event heads,
  authoring target, current tracker/range, and application preconditions into the
  placement and authoring handoff. Revalidate at authoring start and application.
- Extend the author-owned handoff for consequential tracker candidates with an
  explicit `tracker-authoring` supervision profile request, exact direct mission,
  tracker/repository roots, program/feature/Block proposal, verifier result, and
  implementation-readiness evidence. Keep the same profile independently
  invocable for consequential user-seeded authoring and preserve one-shot
  `quality-check` for routine work.
- Require dependency-valid order, exact affected scope, accepted-history
  preservation, current-range effect, resume frontier, and terminal-count updates.
- Route active defects through existing remediation/structural amendment before
  prospective placement; append nonblocking work after the current outcome or to
  successor trackers.
- Produce separately verified tracker artifacts for every selected portfolio node
  and retain rejected/deferred nodes only in the derived portfolio.
- Keep every supervisor-requested correction in the authoring thread's sole
  writable scope and emit a later exact candidate delta; do not treat a steer,
  structural verifier, or author assertion as correction closure.
- Add real maintained tracker fixtures for current revision, successor, and
  multi-tracker portfolio authoring.

### Scope and non-goals

- In scope: tracker authoring and canonical program-revision application.
- Not in scope: implementing Blocks, starting tasks, implementing the supervision
  profile owned by Block 8, or constructing a parallel tracker ledger.
- Do not add permissive generic legacy parsing or aliases.

### Deliverables and recorded state

- Updated authoring skill/contracts, program-revision schema, mappings, fixtures,
  verifier rules, explicit authoring-supervision request/evidence handoffs, and
  exact tracker handoffs.

### Resource and economy contract

Parse each affected tracker once, apply one atomic proposed delta, and verify only
mapped surfaces plus the full structural verifier. Reuse untouched accepted roots.

### QA and independent review

Independent exact-delta review covers add/remove/reorder/modify/split/merge/reopen/
retire/supersede, real trackers, interruption/retry, and full-range conservation.

### Acceptance

- Every accepted selection/portfolio placement yields valid, current, independently reviewed
  tracker state with an exact implementation range and first eligible frontier;
  consequential candidates are ready for the explicit authoring supervision
  profile without transferring tracker-write authority.

### Negative tests

- Reject erased direct capability, completed-successor collision, unmapped required
  prerequisite, stale policy/target/tracker, unrelated application changes,
  ambiguous merge/split, pre-finding retry, false terminal contraction,
  self-attested implementation-readiness, and supervisor-authored tracker edits.

### Completion evidence

Pending.

### Stop

Stop before invoking implementation, activating the Block 8 authoring-supervision
lifecycle, or opening successor/parallel execution.

---

## Block 7 — Invoke evolution from implementation boundaries

Status: `not-started`

### Objective

Make recursive evolution an idempotent, configurable implementation checkpoint
that cannot be skipped at terminal completion or derail active Block execution.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: implementation evidence can prepare or apply useful
  program evolution without waiting for a separate manual request.
- Potential capability loss or regression: synchronous deep reflection at every
  Block could waste resources, invalidate current work, or become an early return.
- Protected-capability effect: preserves requested range, safe frontier, Block
  acceptance, current correction, checkpointing, and final-response gating.
- Architecture and operating-model effect: adds cheap hooks to the implementer;
  deep work remains owned by the fourth skill and structural edits by the author.
- Tradeoff and source evidence: mandatory cheap checkpoints ensure coverage;
  policy-configured material and terminal triggers control expensive reflection.

### Inputs and dependencies

- Block 6 authoring/application path and current implementation range owner.

### Required work

- Add evolution checkpoints at implementation admission, declared material Block
  transitions, current outcome reconciliation, and before terminal completion.
- Make admission checkpoint a no-op for the user-seeded first loop unless prior
  program evidence exists; never block initial authoring.
- Reuse current adaptive decision paths for active remediation or structural
  invalidation and route only prospective selection through portfolio placement.
- Continue dependency-safe work while prospective authoring/review occurs; apply a
  current revision only at its exact safe boundary and rehydrate range/frontier.
- Expose invocation, dedup, resource, placement, and continuation evidence.

### Scope and non-goals

- In scope: implementer invocation/continuation behavior.
- Not in scope: semantic selection, direct tracker writes, supervisor policy, task
  creation, or terminal lifecycle ownership.
- Do not turn every Block Stop into a mandatory deep model cycle.

### Deliverables and recorded state

- Implementer skill/reference/fixture changes and invocation/continuation receipts.

### Resource and economy contract

O(1) fingerprint at every hook; deep reflection only for a changed supported
trigger. At most one active evolution cycle per target/program fingerprint.

### QA and independent review

Focused current-range, no-op, in-run revision, preemption, interruption, and
final-response cases plus mapped implementation tests.

### Acceptance

- The implementer cannot omit terminal reflection, repeat unchanged evolution, or
  use prospective work as a reason to abandon its current requested range.

### Negative tests

- Reject first-loop cold-start blocking, repeated unchanged model calls, premature
  current Block stop, unreviewed revision, stale resume, and final return while an
  accepted current-range addition remains.

### Completion evidence

Pending.

### Stop

Stop before adding supervisor triggers or starting multiple tracker lanes.

---

## Block 8 — Invoke evolution and supervise consequential tracker authoring

Status: `not-started`

### Objective

Let supervision trigger product-program reflection from material observations,
operate an explicit independent tracker-authoring profile, and feed independently
judged effectiveness/resource evidence into later cycles.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: important opportunities or structural concerns can be
  prepared during a run, consequential trackers can be independently challenged
  before implementation, and actual outcomes improve later selection/budgeting.
- Potential capability loss or regression: a supervisor could feature-creep from
  preference, self-validate its finding, or compete with active remediation.
- Protected-capability effect: preserves mechanical/semantic role separation,
  current-run correction priority, exact event provenance, and nonauthorizing
  derived proposals.
- Architecture and operating-model effect: generalizes the on-demand Factory
  Evolution trigger into a target-product evolution route without a watcher loop.
- Tradeoff and source evidence: supervision has the richest independent evidence,
  but it may nominate/trigger rather than author or implement its own proposal.

### Inputs and dependencies

- Block 6 placement path and existing supervision changed-state/effectiveness owners.

### Required work

- Add the explicit, fail-closed `tracker-authoring` target profile to the existing
  canonical supervision policy/status flow while preserving `implementation-run`
  as the absent/legacy default. Bind profile permissions, allow a blank
  `active_block`, and reuse existing events, incidents, routing, decisions,
  completion, and lifecycle state.
- Make the profile directly bootable for consequential user-seeded tracker
  authoring as well as consumable from Block 6 RSI placement. It must not require
  an evolution packet, candidate, or portfolio when direct mission and repository
  sources already establish the authoring target.
- Require independent program, feature, Block, owner, architecture, dependency,
  acceptance, and Stop review against the exact mission, tracker delta, and
  smallest necessary live repository evidence. Preserve Terra mechanical gating,
  independent XHigh review, Max adjudication, and target-owned writing.
- Keep supported corrections open after steering until a later exact tracker
  delta proves the fix; review underreach, unsupported overreach, and a sound
  proportionate alternative without turning optional ideas into findings.
- Require exact implementation-readiness completion: current full verifier,
  frozen tracker/repository roots, required/supported/deferred/rejected/
  missing-required reconciliation, open-item compatibility, distinct independent
  challenge, and profile-aware bounded lifecycle/shutdown. Do not weaken the
  implementation-run terminal report contract.
- Define material triggers from product gaps, protected regressions, repeated or
  costly implementation patterns, productive patterns, operator-visible outcomes,
  terminal reports, and accepted user feedback.
- Route active defects first to current-run correction; independently open
  prospective evolution only when its evidence threshold is met.
- Add deep-trigger, selection-review, effectiveness, budget-use, and no-op event
  shapes to the existing ledger without a new status database.
- Feed accepted/rejected/revised candidates, actual effects, rework, incidents,
  rollbacks, user corrections, and resource evidence into the next packet.
- Require one final evolution checkpoint before terminal shutdown; terminal report
  and automation pause remain ordered after its accepted no-op or handoff.

### Scope and non-goals

- In scope: authoring-profile binding/review/completion/lifecycle plus product-
  program evolution triggers, routing, review, and feedback evidence.
- Not in scope: supervisor-authored trackers/source, a new schedule, continuous
  brainstorming, mandatory supervision for routine authoring, implementation of
  proposed Blocks, or automatic Gmail about ordinary candidates.
- One supervisor observation alone cannot establish broad product work without
  the declared evidence/counterexample posture.

### Deliverables and recorded state

- Supervision policy/skill/helper/event/test changes, explicit authoring-profile
  contract and completion receipts, and effectiveness projection.

### Resource and economy contract

Reuse scheduled changed-state and effectiveness wakes. Authoring reviewers read
the exact delta first and widen only to the mission and repository owners needed
for the question. Deep reflection occurs only for new eligible evidence; quiet
intervals consume no model tokens.

### QA and independent review

Role/provenance tests plus paired underreach/overreach/sound-plan authoring cases
and independent review of false triggers, self-selection, duplicate cycles,
current-remediation substitution, correction closure, completion roots,
implementation-run compatibility, and terminal ordering.

### Acceptance

- Material evidence can trigger one current evolution cycle and later effectiveness
  updates its priors, while unchanged/unsupported observations remain cheap no-ops.
- A consequential RSI-generated or user-seeded authoring run can bind the same
  explicit profile, receive independent repository-grounded program review,
  preserve target-owned correction, and close only at an exact implementation-
  ready candidate; routine authoring and existing implementation supervision
  remain independently operable.

### Negative tests

- Reject supervisor preference without product evidence, generic praise, duplicate
  triggers, prospect replacing active correction, self-reviewed selection, stale
  outcome/resource evidence, inferred authoring kind, supervisor tracker writes,
  green-verifier-only completion, premature correction closure, use of authoring
  profile to bypass implementation reports, and shutdown before terminal
  evolution disposition.

### Completion evidence

Pending.

### Stop

Stop before opening or coordinating sequential/parallel tracker execution or
claiming authoring-profile dogfood.

---

## Block 9 — Orchestrate sequential and parallel tracker portfolios

Status: `not-started`

### Objective

Admit and run an accepted tracker portfolio through existing range, task,
successor-transition, supervision, and integration owners.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: execute multiple complementary programs in the order
  or parallelism selected by evidence rather than forcing one monolithic tracker.
- Potential capability loss or regression: competing writers, resource overload,
  premature successor start, or fragmented outcome ownership could corrupt work.
- Protected-capability effect: preserves one writer per scope, exact range per
  tracker, dependency gates, integration ownership, mission provenance, and
  terminal outcome reconciliation.
- Architecture and operating-model effect: composes existing threads/ranges and
  successor transitions under a derived portfolio; adds no scheduler service.
- Tradeoff and source evidence: parallelism is valuable only for disjoint lanes
  with measured capacity; sequential execution remains the default.

### Inputs and dependencies

- Blocks 7 and 8 invocation paths plus Block 6 authored tracker set.

### Required work

- Admit each tracker with exact source/portfolio/range/mission identity and one
  current owner; retain a portfolio projection of dependency and status only.
- Start sequential successors through the existing transition/work-start path.
- Start parallel lanes only after disjoint-write, shared-resource, integration,
  currentness, budget, and supervision gates pass.
- Reallocate unused budget and stop/retire/revise failed lanes through the accepted
  portfolio owner without silently widening other lanes.
- Reconcile node outcomes into the governing product-program outcome; process
  completion or a handoff alone cannot terminalize the portfolio.
- Support interruption/retry, duplicate delivery, partial lane failure, integration
  failure, and safe rollback/retirement.

### Scope and non-goals

- In scope: bounded orchestration of accepted tracker portfolios.
- Not in scope: a background scheduler, unrestricted concurrency, direct code
  merge, release, deployment, or external effects.
- Do not create a second canonical tracker or supervision state store.

### Deliverables and recorded state

- Portfolio admission/status/gate/handoff contracts and deterministic replay
  fixtures for sequential, parallel, deferred, and no-op paths.

### Resource and economy contract

Sequential is default. Parallel ceiling begins at two active lanes and may widen
only through later accepted evidence/operator ceiling. Shared scans/tests are
batched by the integration owner; lane-local proof remains separate.

### QA and independent review

Replay and mutation cases cover DAG cycles, overlap, races, resource exhaustion,
partial completion, stale integration, duplicate start, and false terminal state.

### Acceptance

- Every admitted portfolio converges to current execution, safe deferral,
  revision/retirement, or observable completion without manual scheduling.

### Negative tests

- Reject overlapping writers, missing integration owner, dependency inversion,
  stale budget/currentness, duplicate work-start, lane completion as portfolio
  completion, and one failed lane stopping independent safe work.

### Completion evidence

Pending.

### Stop

Stop before changing the installed skill release or claiming integrated dogfood.

---

## Block 10 — Extend release ownership from three to four skills

Status: `not-started`

### Objective

Make the existing release owner validate, seal, activate, verify, refresh, and
roll back the complete four-skill Software Factory set.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: install and auto-refresh the recursive evolution skill
  as a first-class part of Software Factory.
- Potential capability loss or regression: a hard cutover could make historical
  releases unreadable, break rollback, or install a partial skill set.
- Protected-capability effect: preserves exact clean source, tests, immutable
  manifests/history, atomic pointer ownership, fresh-process verification, stable
  links, rollback, and automatic compatible monitor refresh.
- Architecture and operating-model effect: versions the release-set schema from
  the historical three-skill set to the current four-skill set; no new release
  primitive is introduced.
- Tradeoff and source evidence: historical readers are necessary for rollback;
  new producers emit only four-skill state and no aliases or dual canonical form.

### Inputs and dependencies

- Block 1 complete skill package.
- Accepted automatic release/refresh line resolved current at implementation time.

### Required work

- Merge/reconcile the current automatic promotion/refresh implementation before
  editing release semantics; preserve its single release authority.
- Version manifest/candidate/validation/root/discovery schemas for an exact ordered
  four-skill set including `evolve-product-program`.
- Keep existing sealed three-skill manifests readable and rollback-eligible;
  require every new stage/promotion/activation to contain four skills.
- Add fourth stable discovery link, installed-root verification, fresh-process
  invocation proof, rollback restoration, and compatible live-role refresh.
- Update README, validation inventory, release docs, tests, and status projection.

### Scope and non-goals

- In scope: existing release owner and exact installed skill-set migration.
- Not in scope: a second promotion workflow, supervisor pointer writes, generic
  manifest compatibility, or unrelated deployment infrastructure.
- Do not activate before Blocks 10–11 acceptance.

### Deliverables and recorded state

- Four-skill release schema, migration/read path, validation suite, documentation,
  and inactive exact candidate capability.

### Resource and economy contract

Reuse flagless promotion tests and unchanged skill roots. Run new-skill validation
plus mapped affected release tests before full release-line proof.

### QA and independent review

Independent review challenges partial sets, historical rollback, schema confusion,
stable-link substitution, stale refresh, and duplicate release effects.

### Acceptance

- New releases require and verify exactly four skills, historical three-skill
  releases remain exact rollback targets, and no pointer changes in this Block.

### Negative tests

- Reject new three-skill release, missing/extra/fifth skill, mixed schema/root,
  partial activation, unverified discovery link, supervisor pointer write, and
  rollback to an unaccepted historical manifest.

### Completion evidence

Pending.

### Stop

Stop before integrated dogfood, staging, activation, or live role refresh.

---

## Block 11 — Dogfood recursion, selection/authoring supervision, and recovery boundaries

Status: `not-started`

### Objective

Exercise one complete, reproducible two-cycle recursive product-program run and
bounded selection/authoring-supervision lifecycle across poor and sound choices,
current revision, successor, parallel portfolio, unchanged no-op, and recovery.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: prove the four skills cooperate on actual behavior,
  not merely valid schemas and self-asserted handoffs.
- Potential capability loss or regression: synthetic-only fixtures, unstable
  evidence, or uncontrolled dogfood could overclaim autonomy or affect live work.
- Protected-capability effect: verifies first-loop cold start, current-range
  completion, product value, protected behavior, resource bounds, role separation,
  rollback, and no external/reserved effects.
- Architecture and operating-model effect: supplies the first end-to-end program
  evolution evidence and calibration prior.
- Tradeoff and source evidence: one high-precision frozen run plus deterministic
  semantic projection is sufficient for acceptance; broad live deployment is not.

### Inputs and dependencies

- Blocks 9 and 10 plus Block 5 accepted online selection-review profile.

### Required work

- Build a Git-less reproducible dogfood workspace using exact source and installed
  identities; keep disposable writes isolated.
- Prove the first loop starts from user intent without an evolution prerequisite.
- Freeze a realistic current behavior/feature/capability and mixed tracker
  inventory covering every planned, active, completed, accepted, rejected,
  retired, and superseded state.
- Cycle A preserves multiple candidates, rejected/deferred alternatives, and
  forecasts; online independent selection review catches one duplicate, poor
  design, or current-work-starving choice before authoring while accepting one
  sound choice exactly once.
- During implementation, inject supported evidence that selects a non-derailing
  current tracker revision; apply through authoring and resume exact remaining work.
- Select a portfolio containing one sequential successor and two genuinely
  disjoint parallel trackers, then run/reconcile them through existing owners.
- Include feature, refactor/simplification, removal, experiment, and no-change
  candidates; select only those supported by evidence.
- Record resource priors, allocated/actual use, useful outcomes, early stop or
  returned capacity, exact selection forecasts and actual outcomes, at least one
  forecast correction, supported or explicitly unavailable counterfactual, and
  unchanged replay.
- Exercise changed evidence/currentness, interruption after selection/authoring/
  work-start/outcome, failed lane, integration failure, and release rollback in
  isolated fixtures.
- Dogfood the explicit authoring-supervision profile on both one RSI-generated
  tracker and one consequential direct user-seeded tracker. Include blinded
  underreach, unsupported-overreach, malformed-Block, and sound-plan cases;
  demonstrate one narrow target-owned correction remaining open until a later
  delta, exact implementation-readiness completion, profile-aware lifecycle,
  and unchanged ordinary/implementation-run behavior.
- Derive one bounded selector-policy candidate after the Cycle A outcome, compare
  it independently with the incumbent on chronological retained cases, and run
  Cycle B as a subsequent or shadow cycle. Accept only a supported improvement
  without protected regression; otherwise retain the incumbent truthfully.

### Scope and non-goals

- In scope: isolated two-cycle live-behavior dogfood and reproducible evidence.
- Not in scope: external deployment, Gmail, credentials, destructive work,
  production target mutation, unbounded concurrency, or a third recursive cycle
  merely to obtain a favorable result.
- Do not use process completion as product-outcome proof.

### Deliverables and recorded state

- Frozen raw run, deterministic semantic projection, portfolio/tracker artifacts,
  authoring-profile review/completion/lifecycle receipts, current observable-
  outcome proof, and recovery/economy evidence.

### Resource and economy contract

Predeclare total model, elapsed, token, command, validation, review, workspace,
and two-lane concurrency ceilings. Retain completed producer output across
reporting/retry; run exactly two material cycles and one unchanged replay, which
must perform zero generation, review, evaluation, or policy work.

### QA and independent review

Separate product/program reviewer, exact source reviewer, authoring-readiness
reviewer, and evaluator inspect raw evidence, retained projection, candidates,
rejected alternatives, authoring cases/corrections, budgets, effects, and every
Stop.

### Acceptance

- The exact run demonstrates the complete union: sound feature/program selection,
  bad-choice prevention before authoring, distinct tracker-authoring review,
  outcome-linked evaluation, and outcome-driven future-selection improvement,
  while current commitments, authority, resources, and no-op convergence remain
  correct.

### Negative tests

- Reject nonreproducible raw/projection claims, root-consistent synthetic semantic
  changes, hidden current-work displacement, overlap, resource overrun, candidate
  self-adoption, authoring review pre-labeled with its expected conclusion,
  supervisor tracker writes, oversteered sound plans, process-only outcome,
  repeated producer work, and live effects.

### Completion evidence

Pending.

### Stop

Stop before final source acceptance, release activation, or live supervisor refresh.

---

## Block 12 — Evaluate selection effectiveness and supported counterfactuals

Status: `not-started`

### Objective

Independently determine how an exact reviewed selection performed after its
canonical program reaches a current observable outcome, preserving uncertainty
and only evidence-supported missed opportunities.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: learn whether the system chose valuable work, not
  merely whether implementation completed or tests passed.
- Potential capability loss or regression: retrospective narratives could assign
  false causality, fabricate counterfactuals, or optimize activity proxies.
- Protected-capability effect: preserves independent outcome proof, typed and
  contrary evidence, uncertainty, product value, current behavior, and no
  selector self-evaluation.
- Architecture and operating-model effect: adds derived selection-effectiveness
  artifacts over existing canonical outcome/supervision/resource owners.
- Tradeoff and source evidence: causal proof is often incomplete; an explicit
  `inconclusive` result is more truthful than an always-positive score.

### Inputs and dependencies

- Block 11 frozen exact selection/review/authoring/implementation/forecast/outcome
  lineage and current observable-outcome completion.
- Relevant supervision, report, resource, incident, rollback, rework, user-
  correction, coordination, abandoned-work, and returned-capacity evidence.

### Required work

- Define exact `selection-effectiveness` packet/result schemas that bind the
  original selection/forecasts, accepted selection review, authored program,
  implementation revisions, current outcome, policy/event heads, and typed
  product/protected-capability/resource dimensions.
- Use a distinct evaluator to compare forecast and actual product effect,
  adoption/effectiveness, capability preservation, rework, incidents, rollback,
  user correction, elapsed/token/command/tool/validation/review use, coordination
  cost, abandoned work, and returned capacity.
- Preserve `observed`, `provider-reported`, `estimated`, `inferred`, and
  `unavailable` classes. Never convert missing evidence to zero, estimates to
  actuals, or completion/test success/supervisor praise into product value.
- Derive only `effective`, `mixed`, `ineffective`, or `inconclusive`; retain
  contrary evidence and distinguish selection error from implementation defect,
  outcome gap, later mission change, external blocker, or supervisor miss.
- Retain selected-work false positives and independently supported duplication/
  underperformance/protected regressions. Retain rejected/deferred false negatives
  or missed opportunities only when later canonical evidence binds the original
  candidate; do not simulate unobserved worlds.
- Append exact corrections/supersession when later outcome evidence changes;
  only one current head contributes to selector learning. Route evaluator/
  supervisor misses to existing supervision-effectiveness and Factory Evolution.

### Scope and non-goals

- In scope: outcome-linked evaluation, forecast calibration, supported
  counterfactual/missed-opportunity evidence, dispositions, corrections, and
  current projections.
- Not in scope: revising/adopting selector policy, ranking candidates again,
  automatic rollback, deleting useful implemented behavior, or claiming causal
  certainty.
- Negative evaluation routes any current defect through its ordinary owner.

### Deliverables and recorded state

- Deterministic evaluation packet/result builders/validators, exact outcome
  linkage/current projection, limitations, tests, and independent review receipt.

### Resource and economy contract

One evaluation per new current outcome head. Reuse frozen selection and canonical
outcome roots; read only mapped evidence; unchanged or nonterminal state returns a
no-op/inconclusive result without deep review.

### QA and independent review

Blind cases cover effective, mixed, ineffective, inconclusive, implementation-
failure-not-selection-error, later mission change, correction, supported missed
opportunity, unavailable counterfactual, proxy gaming, stale outcome, duplicate
head, and selector/evaluator identity conflict.

### Acceptance

- Every learning-eligible selection has one current, independently reviewed,
  outcome-bound effectiveness disposition whose vector evidence and limitations
  reconstruct without process proxies or self-asserted value.

### Negative tests

- Reject another selection/program's outcome, noncurrent completion, generic
  praise, arbitrary positive category, self-evaluation, aggregate score,
  fabricated counterfactual, estimated-as-observed use, missing contrary evidence,
  duplicate current head, and effectiveness used as rollback/adoption authority.

### Completion evidence

Pending.

### Stop

Stop before proposing, comparing, applying, releasing, or refreshing a selector-
policy change.

---

## Block 13 — Revise and compare selector policy without self-evaluation

Status: `not-started`

### Objective

Turn current selection-effectiveness evidence into at most one bounded versioned
selector-policy candidate and accept it only when an independent comparison shows
a supported improvement without protected regression.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: candidate generation, evidence thresholds, ranking
  dimensions/weights, uncertainty treatment, portfolio composition, resource
  budgeting, and Stop/revisit rules improve from actual selection outcomes.
- Potential capability loss or regression: overfit, reward gaming, opaque scoring,
  reduced diversity, and self-approval could regress direct intent and useful work.
- Protected-capability effect: preserves divergent generation, direct mission,
  independent selection/review/evaluation, current work, visible evidence
  dimensions, no-op eligibility, bounds, and reversible policy history.
- Architecture and operating-model effect: adds derived versioned policy,
  candidate, comparison, and application-handoff artifacts through existing
  source/Git/review/release/refresh owners.
- Tradeoff and source evidence: explicit versioning enables real learning; one
  candidate and one forward/shadow cycle bound recursive churn.

### Inputs and dependencies

- Block 12 current independently accepted effectiveness evidence from one or more
  exact cycles, current selector policy, chronological retained historical cases,
  and current permission/resource ceilings.

### Required work

- Represent the incumbent selector policy explicitly: source coverage, divergence,
  evidence admission, dimension comparisons/weights, uncertainty and contrary
  treatment, dependency/portfolio/resource rules, current-work preservation,
  Stops, and revisit triggers. Prohibit hidden aggregate utility/reward scores.
- Build at most one candidate per eligible evidence root, binding predecessor,
  supporting and contrary effectiveness records, hypothesized effect, affected
  rules, protected invariants, rollback identity, expiry, and revisit trigger.
- Permit bounded changes only to supported generation coverage, thresholds,
  dimension-specific comparisons/weights, portfolio/resource heuristics,
  uncertainty treatment, and evidence widening. Identical/sparse evidence is a
  no-op, not pressure to change.
- Use chronological retained case splits that prevent policy construction from
  reading held-out dispositions. Include sound, poor, no-op, current-work, multi-
  tracker, uncertainty, omission, and goal-boundary cases.
- Have a distinct independent evaluator compare incumbent/candidate on every
  declared dimension, false positives/negatives, missed supported work, resources,
  protected behavior, direct intent, diversity, and no-op economy.
- Require at least one subsequent or shadow live cycle under identical input/
  currentness. Shadow output is nonauthorizing and cannot alter the live choice.
- Accept only dimension-visible improvement without protected regression,
  scheduling leak, gaming, leakage, or overfit. Mixed/inconclusive candidates
  remain rejected/deferred with incumbent unchanged and exact findings open.
- Route an accepted candidate only through existing source implementation,
  independent exact Git review, release owner, and safe refresh; preserve
  immutable predecessor and rollback. Supervisor-policy learning remains with
  supervision-effectiveness/Factory Evolution, preventing infinite self-approval.

### Scope and non-goals

- In scope: versioned policy, bounded candidate, retained/forward comparison,
  independent acceptance, application handoff, expiry/revisit, and rollback.
- Not in scope: online selection review, feature implementation, continuous
  tuning, arbitrary prompt mutation, general model training, supervisor self-
  modification, direct source edit, release, or monitor refresh.
- No policy change is required when evidence is sparse or disagrees.

### Deliverables and recorded state

- Incumbent policy artifact, candidate/comparison builders and schemas, retained
  case corpus, shadow receipt, independent disposition, application handoff, and
  rollback metadata.

### Resource and economy contract

At most one candidate and one retained comparison per new effectiveness root plus
one forward/shadow cycle. Reuse immutable inputs/results; stop on any protected
regression; unchanged evidence performs zero policy work.

### QA and independent review

Challenge held-out leakage, reward gaming, benchmark overfit, self-evaluation,
opaque score/weights, reduced diversity, omitted required work, current-range
displacement, resource inflation, stale predecessor, duplicate application,
shadow authority, and rollback currentness.

### Acceptance

- One exact candidate either proves a dimension-visible, independently reviewed,
  forward-confirmed improvement without protected regression and becomes eligible
  for existing-owner application, or remains rejected/deferred with the incumbent
  unchanged.

### Negative tests

- Reject self-approval, selector-as-evaluator, held-out leakage, pass-count/reward
  optimization, one-episode overgeneralization, opaque aggregate score, missing
  contrary evidence, stale predecessor, protected regression, inconclusive-as-
  improved, shadow output as authority, direct live edit, and policy adoption
  without a separately accepted comparison.

### Completion evidence

Pending.

### Stop

Stop before final integrated acceptance, release promotion, or active supervisor
refresh.

---

## Block 14 — Freeze, independently review, release, refresh, and prove effectiveness

Status: `not-started`

### Objective

Accept one exact integrated successor, install it through the normal release owner,
refresh compatible roles, and prove the recursive loop plus consequential
selection/authoring-supervision profiles and selector-policy loop remain
effective/current.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block validates and activates the
  already implemented capability without adding another product mechanism.

### Inputs and dependencies

- Blocks 11–13 frozen implementation, dogfood, effectiveness, and selector-policy
  comparison evidence.

### Required work

- Run changed-path/focused suites, mapped four-skill suites, release tests, all four
  skill validators, tracker verifier, compile, diff, clean-tree, ancestry,
  currentness, Git-less rebuild, and full maintained validation required by risk.
- Freeze and push the exact candidate; obtain independent exact-revision review;
  remediate findings in successor commits with only affected proof rerun.
- Integrate the accepted automatic release/refresh and product-program evolution
  lines without unrelated later Factory work.
- Use only the flagless release-owner promotion after exact independent acceptance;
  consume its verified four-skill release identity and roots.
- Refresh compatible active implementation/supervision roles at actual safe
  boundaries, preserving mission, range, events, cursors, incidents, automations,
  Gmail, schedules, models, and policy fields.
- Verify installed `product-program-selection` and `tracker-authoring` profiles,
  selector-policy identity, Terra/XHigh/Max separation, current implementation
  continuation, accepted/rejected/no-op behavior, and no duplicated review/effect.
- Run one current material selection checkpoint and one later outcome/
  effectiveness checkpoint using the installed release and accepted policy; run
  one unchanged checkpoint to verify no-op economy. Do not select new work merely
  to manufacture proof.
- Verify the tracker-authoring supervision profile at the exact accepted source:
  direct boot for consequential user-seeded authoring, RSI handoff consumption,
  author/supervisor writer separation, repository-grounded independent review,
  later-delta correction closure, exact implementation-readiness completion,
  bounded lifecycle, ordinary one-shot authoring, and unchanged implementation-
  run compatibility.
- Preserve
  `docs/software-factory-tracker-authoring-supervision-implementation-tracker.md`
  as superseded planning history and verify its Block 0–4 requirements against
  the amendment map in Section 4 before publishing demonstrated guidance.
- On failed install/refresh/effectiveness verification, request owner rollback and
  restore prior role bindings; retain candidate/evidence truthfully.

### Scope and non-goals

- In scope: exact acceptance, release, installed-root verification, safe refresh,
  rollback, installed selection/effectiveness observation, and terminal lifecycle.
- Not in scope: unrelated feature implementation, continuous background ideation,
  generalized deployment, Gmail beyond normal terminal ownership, or widening
  permission/resource ceilings.
- Do not claim completion while any tracker Block, accepted portfolio node,
  supported finding, release identity, role refresh, or effectiveness proof remains
  open.

### Deliverables and recorded state

- Accepted source/tree, four-skill release/manifest/roots, refreshed role receipts,
  selection/authoring-profile and selector-policy identities, implementation-
  readiness evidence, installed selection/effectiveness evidence, rollback proof,
  and final tracker completion evidence.

### Resource and economy contract

Reuse unchanged proof roots, validate affected slices first, run each broad suite
once on the final frozen source, and perform no deep work on unchanged replay.

### QA and independent review

Independent exact candidate, release, installed-root, role-refresh, authoring-
profile dogfood/readiness, online-selection, selector-policy, rollback, resource/
effectiveness, and final observable-outcome reviews.

### Acceptance

- Exact source, four installed skills, refreshed roles, both supervision profiles,
  selector policy, trackers/ranges, recursive portfolio behavior, resource
  evidence, selection/effectiveness checkpoint, and current observable outcome all
  agree; rollback restores the accepted incumbent when exercised in isolation.

### Negative tests

- Reject stale review, changed candidate, partial four-skill install, mismatched
  active roots, unsafe refresh, stale profile/policy, lost mission/cursor/range,
  duplicate selection/review/effect, changed evidence accepted as no-op, stale or
  self-attested authoring readiness, open selection/authoring corrections,
  weakened implementation-run lifecycle, ineffective selected work, rollback to
  an unaccepted release, report-less shutdown, or terminal response with an open
  program node.

### Completion evidence

Pending.

### Stop

Stop after exact accepted effectiveness and terminal proof; do not begin an
unselected next product program merely to demonstrate recursion.

## 8. Verification matrix

| Capability or invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| First loop remains user intent → author → implement + supervise | 0 | 7, 11 | 14 |
| Deterministic current product/program evidence | 1 | 5, 7–8 | 14 |
| Reflective, diverse, counterexample-aware opportunity generation | 2 | 4–5, 8 | 14 |
| Current behavior/features and every tracker state ground candidates/selection | 2 | 4–5, 11 | 14 |
| Transparent quality/resource evidence and learned priors | 3 | 4, 7, 12–13 | 14 |
| Independent portfolio selection, budget, forecasts, and placement | 4 | 5–6, 9 | 14 |
| Consequential choice is independently reviewed before authoring | 5 | 6, 11 | 14 |
| Terra/XHigh/Max remain separated and unchanged selection is a no-op | 5 | 11 | 14 |
| Bad choices reject/revise without displacing canonical current work | 5 | 6–7, 11 | 14 |
| Full current/successor tracker evolution preserves history/range | 6 | 7, 9 | 14 |
| Accepted selection reaches one author; selection and tracker review stay distinct | 6 | 8, 11 | 14 |
| Consequential RSI/user-seeded authoring binds an explicit independent supervision profile | 6 | 8, 11 | 14 |
| Authoring review challenges program/features/Blocks against mission and live owners | 8 | 11 | 14 |
| Target-owned selection/authoring findings remain open through later exact evidence | 5 | 8, 11 | 14 |
| Exact implementation-readiness completion and bounded authoring lifecycle | 8 | 11 | 14 |
| Routine one-shot authoring and implementation-run supervision remain compatible | 8 | 11 | 14 |
| Implementer invokes without derailing current work | 7 | 9 | 14 |
| Sequential/parallel portfolios preserve ownership and converge | 9 | 11 | 14 |
| Existing release owner installs/rolls back exactly four skills | 10 | 11 | 14 |
| Selection quality is judged from outcomes, not process proxies | 12 | 11, 13 | 14 |
| Supported false positives/negatives and missed opportunities remain typed | 12 | 13 | 14 |
| Selector policy is versioned, independently compared, forward-confirmed, reversible | 13 | 11 | 14 |
| Two-cycle union dogfood and unchanged replay are exact and bounded | 11 | 12–14 | 14 |
| Installed profiles/policy preserve mission/range/cursors and rollback | 14 | — | 14 |

## 9. Final completion definition

The tracker is complete only when all 15 Blocks are accepted at exact current
revisions; `evolve-product-program` is installed as the fourth Software Factory
skill; the first user-intent loop remains direct; implementation and supervision
invoke recursive reflection from material and terminal evidence; divergent
candidate generation over actual behavior/features/all tracker states, independent
portfolio selection with forecasts, online independent selection review before
authoring, transparent resource allocation, current/successor tracker evolution,
sequential/parallel execution, and outcome-bound selection effectiveness are
proven from exact dogfood evidence; consequential
RSI-generated and independently user-seeded tracker authoring bind the explicit
supervision profile and prove repository-grounded program/feature/Block review,
target-owned correction, exact implementation-readiness, and bounded lifecycle;
selection review and tracker-authoring review remain distinct; one versioned
selector-policy candidate is independently compared with its incumbent on
chronological retained held-out evidence and a forward/shadow cycle and either
proves a protected-regression-free improvement or leaves the incumbent unchanged;
routine one-shot authoring and implementation-run supervision remain compatible;
two-cycle dogfood catches a bad selection, advances a sound one, evaluates its
outcome, and improves future selection without retroactive authorization;
unchanged replay performs no deep work; current commitments and protected
capabilities are not displaced; historical three-skill rollback remains valid;
the standalone authoring-supervision tracker is preserved as exactly mapped
superseded planning history; the selection-quality source tracker is preserved as
fully mapped source planning evidence; and exact source, release, installed roots,
refreshed roles/profiles/policy, ranges, portfolios, reviews, authoring-readiness
receipts, selection-effectiveness, and observable outcome reconcile. A candidate
list, favorable review, tracker amendment, green verifier, completed task,
release, or populated telemetry record alone is not recursive product improvement.
