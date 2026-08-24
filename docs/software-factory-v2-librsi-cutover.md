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
adapter verifies the installed distribution/import version and PEP 610 commit for
VCS installs. It never resolves `libRSI` by a bare registry name/version, imports
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

## Authoritative slices and shadow receipt

The following exact slices are authoritative through libRSI:

1. a terminal failed, abandoned, or cancelled execution maps to an exact target
   snapshot, one observation, two competing hypotheses, non-discriminating
   boundary evidence, and one bounded strategy/context discriminator;
2. an unexpected successful execution maps to an exact target snapshot, one
   observation, reusable-effect and contextual-effect hypotheses, boundary
   evidence, and one bounded matched replay/counterexample experiment; and
3. exact experiment observations update the exact hypothesis version. A failed
   experiment is zero-weight null evidence, never falsification. Reuse follow-up
   work appears only after bounded supporting evidence reaches libRSI's supported
   posture, and remains proposed/pending until Factory authority advances it.

Before each source execution becomes authoritative, the adapter compares the two
expected competing roles and route against the canonical result. The content-rooted
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
| learning signal detector/runtime tables | retained Factory classifier execution | existing Factory owner | not used as the hypothesis/experiment writer for the migrated slices |
| evolution/program and problem-solving host tables | retained Factory operational compatibility and work/effect coordination | existing Factory owner | cannot authorize effects from a libRSI result; later storage retirement requires Block 11 preservation and parity evidence |

The cutover does not claim that retained historical or compatibility schemas are
libRSI records. The owner-uniqueness guarantee is narrower and exact: for the
migrated failed/unexpected-execution epistemic and experimental semantics, only
libRSI canonical records are current semantic outputs, and the prior local
reflection writer is absent.
