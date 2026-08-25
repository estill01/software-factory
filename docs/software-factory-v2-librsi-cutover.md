# Software Factory v2 libRSI cutover and deletion map

## Immutable dependency admission

Software Factory consumes libRSI in one direction at exact accepted identities:

| Identity | Accepted value |
|---|---|
| producer acceptance revision | `dbcb60edfbcab53ff7e5cc25403bfbc33b458329` |
| source commit | `1d81f6180b40435e10145756a2d99e6f334d31bc` |
| repository tree | `d9ff421192e3582a6b8e908bf8a02cf2d7678acc` |
| package tree/content root | `2653cb551e69bf2f45c95216982f70b50258c92e` (`git-tree:src/librsi`) |
| distribution/import/version | `libRSI` / `librsi` / `0.2.0` |
| accepted wheel SHA-256 | `6b06612150d2f3a11b23de14870738ea9cd6b704574c8cea2c8e811392454659` |
| accepted sdist SHA-256 | `e3ca4a817b80043ea59ba153e4d3ba105c86ad74183cb28816d66dd6d0f813c0` |
| schema versions | semantic record `1`; outcome projection `1`; event projection `1` |
| Factory adapter | `software-factory.librsi/v1` |

The runtime dependency and generated lock both name the exact source commit. The
adapter requires the installed distribution/import version and exact PEP 610
URL/VCS/requested/installed commit. Absence of `direct_url.json` fails closed; a
future wheel admission would require a separate explicit artifact-hash installer
owner. It never resolves `libRSI` by a bare registry name/version, imports
from the producer's dirty checkout, copies producer source, or modifies the libRSI
repository. The recorded producer artifacts are unpublished internal artifacts;
this repository makes no installability, license, redistribution, or release claim.

## Owner boundary

`LibRSIIntegration` maps complete observed Factory state to canonical `TargetRef`,
`TargetSnapshot`, `Observation`, `Evidence`, `Hypothesis`, and `ExperimentSpec`
records. Software Factory owns the adapter, immutable record cache, operational
bindings, execution of experiments, work creation, effects, governance, QA,
acceptance, delivery, and lifecycle state.

Operational IDs are never semantic identities. An execution ID, work ID, and
libRSI root remain distinct values joined only through
`librsi_record_bindings`. No operational table has a foreign key to
`librsi_records`. A semantic status or recommendation creates at most proposed
Factory work; it does not select, dispatch, accept, apply, or complete that work.

## Authoritative semantics and shadow receipt

The following semantics are authoritative through libRSI:

1. a terminal failed, abandoned, or cancelled execution maps to an exact target
   snapshot, one observation, two competing hypotheses, non-discriminating
   boundary evidence, and one bounded strategy/context discriminator;
2. an unexpected successful execution maps to an exact target snapshot, one
   observation, reusable-effect and contextual-effect hypotheses, boundary
   evidence, and one bounded matched replay/counterexample experiment; and
3. exact experiment observations update the exact hypothesis version. A failed
   experiment is zero-weight null evidence, never falsification. Reuse follow-up
   work appears only after bounded supporting evidence reaches libRSI's supported
   posture, and remains proposed/pending until Factory authority advances it;
4. `LearningService` maps its compatibility entrypoints to canonical `Hypothesis`,
   `Evidence`, and `ExperimentSpec` records and uses `HypothesisPolicy` and
   `ExperimentPolicy`; `hypotheses_v2` and `hypothesis_evidence_v2` have no runtime
   writer or lifecycle-owner claim, while `experiments_v2` and
   `experiment_runs_v2` retain only host execution state;
5. evidence-bound candidate comparison uses `CandidateTrialBatch`, `RiskPolicy`,
   and `ComparativeSelectionPolicy`; its `SelectionDecision` is cached and bound
   but creates no Factory work or authority transition. A retained operational
   candidate row can advance only after independent Factory review and an exact
   same-group, selected-candidate, currentness-matched decision binding;
6. evolution checkpoint, program-change, portfolio, and selector-policy
   compatibility entrypoints delegate their decisions and gates to the accepted
   `CheckpointPolicy`, `ProgramPolicy`, `PortfolioPolicy`, and `SelectorPolicy`;
   the retained rows are operational projections rather than semantic policy; and
7. complete `ImprovementResult` and governed `RSIResult` records cross one typed
   result-binding boundary. `RSIResult` admission revalidates its exact
   `SelfChangePolicy` request; neither result applies, accepts, schedules, or
   releases a Factory effect.

Before each failed/unexpected source execution becomes authoritative, a preserved
pure legacy projection independently produces the exact roles, statements,
predictions, route, and experiment kind. The adapter compares the complete canonical
projection before any semantic persistence, work creation, binding, receipt, or
cutover event. The content-rooted
receipt in `librsi_cutover_receipts_v2` records exact dependency identity,
currentness, shadow root, semantic-result root, matched parity, and authoritative
posture. Mismatch fails closed.

## Deletion and preservation map

| Prior path | Current treatment | Writer posture | Preservation/removal condition |
|---|---|---|---|
| `ReflectionService._create_hypothesis` and failed/unexpected local proposal logic | deleted | no local writer | replaced after mapped parity by `LibRSIIntegration` |
| `ReflectionService.update_hypothesis` | deleted | no local writer | exact immutable libRSI evidence updates replace mutable local rows |
| legacy `hypotheses` table | schema-history only | no runtime writer and no lifecycle-owner claim | retain bytes for migration/reconciliation; Block 11 may retire storage after preservation proof |
| `librsi_records` | canonical semantic cache | `integrations.librsi.service` only | immutable by root; conflicting content fails closed |
| `librsi_record_bindings` | explicit operational-to-semantic mapping | `integrations.librsi.service` only | never substitute a semantic root for an operational ID |
| `reflections_v2`, `hypotheses_v2`, and `hypothesis_evidence_v2` | schema-history only | no runtime writer and no lifecycle-owner claim | canonical libRSI observations, hypotheses, evidence, and immutable versions replace local mutable semantics; Block 11 owns byte retirement after preservation proof |
| `experiments_v2` and `experiment_runs_v2` | Factory host execution projections | `learning` operational owner | canonical experiment design/evaluation/evidence remains in `librsi_records`; local status cannot manufacture semantic proof |
| learning signal detector/runtime tables | retained Factory classifier execution | `learning` operational owner | route observed operational signals only; they are not a second hypothesis, experiment, comparison, improvement, or self-change authority |
| evolution/program host tables | retained Factory governance/effect coordination | `evolution` operational owner | accepted libRSI policies compute semantic roots and gates; Factory rows attribute review, currentness, and effects |
| `selection_outcomes_v2` | schema-history only | no runtime writer and no lifecycle-owner claim | complete canonical improvement results replace caller-authored local causal outcomes |
| problem-solving host tables | retained Factory scheduling/work coordination | `problem_solving` operational owner | writable-scope scheduling and execution remain Factory; hypotheses/experiments/comparison/results cross the canonical integration boundary |

The cutover does not claim that retained historical or compatibility schemas are
libRSI records. Owner uniqueness is exhaustive: `integrations.librsi.service` is
the only current semantic lifecycle owner in the runtime registry. Learning,
evolution, adaptive outcome, and problem-solving tables are operational projections;
their generic hypothesis/evidence writers are absent and their accepted policy
decisions originate in libRSI.
