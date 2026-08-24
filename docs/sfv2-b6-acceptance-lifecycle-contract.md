# SFV2 Block 6 acceptance lifecycle contract

## Purpose

This contract binds Software Factory acceptance to the exact revision, exact
currentness root, independent review, and reconstructed actual outcome. It does
not treat a successful process, provider completion, commit, or test result as
the operator-visible outcome.

## Authority composition

| Concern | Authority | Block 6 composition rule |
|---|---|---|
| Mechanical QA observations | acceptance probes and existing QA execution lanes | evidence input only; cannot count as semantic review |
| Semantic review and decision | `GovernanceService` | exact-revision role grant, independent provider identity, review record, and acceptance decision remain authoritative |
| Acceptance-stage projection | `AcceptanceLifecycleService` | records candidate, integrated, installed, and terminal state after consuming the governance decision |
| Work acceptance | `WorkItemService` | receives a bounded candidate/integrated/installed promotion or outcome-regression call; no second work writer |
| Capability regression and obligation | `CapabilityService` | receives the exact capability disagreement and creates the correction obligation |
| Incident and effectiveness | `SupervisionService` | records containment/correction/effectiveness without becoming acceptance authority |
| Terminal mission transition | `ContinuationService` | reduces remaining range, required capabilities, obligations, terminal evidence, accepted terminal stage, and aligned outcome |

The stage coordinator writes only `acceptance_stage_records_v2` and
`outcome_reconciliations_v2`. Cross-lifecycle changes are routed through the
existing public owners inside one nested transaction. There is no second QA,
governance, work, capability, incident, or mission writer.

## Stage invariants

The stage order is:

1. `candidate`
2. `integrated`
3. `installed`
4. `terminal`

Each stage binds:

- mission and optional narrow work scope;
- exact target revision and currentness root;
- implementer identity;
- governance acceptance contract and decision;
- explicit operator-visible or protected-capability outcome contract;
- remaining requested scope;
- exact accepted predecessor for every non-candidate stage.

A changed revision or currentness root stales every prepared, accepted, or
reopened stage in the same scope, invalidates its governance decision/review,
and requires a new chain. An exact duplicate preparation is idempotent; the same
revision/currentness tuple cannot be rebound to different contract material.

## Mechanical versus semantic review

The lifecycle rejects `independent_review`, `review`, `semantic_review`, and
`architecture_review` as mechanical probe types. Mechanical probes require
current evidence at the exact revision. They still cannot produce an acceptance
decision until the governance owner has consumed an exact role grant and an
independent semantic review from a session other than the implementer.

The semantic reviewer reconstructs operator-visible behavior and protected
capabilities from evidence. A caller-asserted reviewer label, stale currentness,
same-author review, or mismatched provider identity fails closed.

## Actual-outcome reconciliation

After governance accepts the process evidence, an independent outcome reviewer
records the observed outcome at the same revision/currentness root. The reducer
compares every declared expected path without applying a universal score. An
identical observation/evidence packet deduplicates by content root, avoiding
replay of unchanged accepted proof.

When expected and observed state disagree, the reducer requires exactly one
narrow operational owner:

- the stage work item;
- one mission capability; or
- the mission itself.

It records the mismatch, reopens/regresses that owner where applicable, creates
one correction obligation, opens one deduplicated incident, and marks the stage
`reopened`. A later aligned observation does not erase history or self-close the
correction: its obligation must be satisfied and its incident must receive an
independent effectiveness disposition before promotion.

## Terminal reducer

A successful terminal-verification execution without accepted actual-outcome
state yields `reconcile_terminal_acceptance`, not `complete_mission`.

Terminal-stage promotion and mission completion both require:

- accepted candidate, integrated, and installed predecessors at the same exact
  revision and currentness root;
- one accepted governance decision plus aligned independent outcome;
- no unresolved outcome disagreement;
- an empty remaining requested range;
- no required capability gap;
- no open obligation;
- no selected, uncancelled work below installed acceptance;
- terminal or installed evidence whose revision equals the accepted terminal
  revision; and
- an independent terminal verifier who produced the terminal execution.

This reducer preserves the complete requested range and blocks terminal return
when any remaining Block or outcome obligation exists.

## Economy and exclusions

- Review is stage- and change-bound; unchanged evidence packets deduplicate.
- Accepted proof is not replayed for a later stage or currentness root.
- Existing supervision `no_change` checks remain the sampling mechanism.
- There is no per-action critic or universal quality score.
- This Block does not begin libRSI cutover or consume any utils artifact.
