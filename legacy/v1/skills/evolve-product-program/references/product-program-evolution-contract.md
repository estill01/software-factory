# Product-program evolution contract

This contract extends the accepted Factory Evolution ladder from Factory-skill
maintenance to target-product and implementation-program evolution. It creates a
derived reflection and portfolio owner; it does not create a tracker writer,
source writer, supervision ledger, release owner, scheduler, or permission
system.

## Cold start and recursion boundary

The first delivery loop is always available as `direct intent -> tracker author
-> tracker implementation + supervision`. Product-program evolution is never a
prerequisite for authoring that first tracker.

A recursive cycle begins only from one exact material-change or terminal
checkpoint over current product, repository, tracker, outcome, supervision, and
resource evidence. The cycle stops after it emits one verified, nonauthorizing
placement handoff. The receiving existing owner decides whether and how to apply
that handoff under its own contract.

An unchanged checkpoint is a deterministic no-op. Equality of the prior and
current `material_change_fingerprint` values, together with equality of the
prior and current `currentness_root` values, returns
`continue-program-unchanged` without cognition, candidates, selection,
authoring, task creation, source writes, or supervisor work. The two identity
classes are never compared with each other.

## Target profiles

The shared evolution ladder is:

`evidence -> observation -> lesson -> meta-pattern -> capability gap ->
candidate -> experiment -> disposition`.

Target profiles extend that ladder without sharing adoption authority:

- `software-factory-capability` uses canonical supervision evidence and the
  Factory Evolution adoption path. Its downstream owner is determined by the
  existing Factory candidate-type map.
- `target-product-program` adds product thesis, user/capability effects,
  protected capabilities, current requested range, program structure, resource
  evidence, and placement. Its outputs can be applied only by the existing
  tracker-authoring, implementation, supervision, or reserved-effect owner.

A profile changes the evidence and decision vocabulary, never the canonical
writer. A target-product artifact cannot enter the Factory skill-adoption path,
and a Factory artifact cannot change a target product or tracker directly.

## Roles and separation

| Role | Owns | Must not own in the same decision |
|---|---|---|
| Evidence assembler | deterministic source validation, minimization, and packet identity | semantic judgment or authority claims |
| Reflection generator | observations, lessons, meta-patterns, gaps, and divergent candidates | selection, authoring, implementation, or evaluation |
| Resource-evidence builder | typed resource/outcome projection and useful-yield priors | allocation, billing claims, spend, or selection |
| Portfolio selector | one disposition, rejected alternatives, budget, DAG, and placement handoff | candidate generation, downstream writes, or self-evaluation |
| Consequential adjudicator | unresolved material placement review | generation, implementation, or promotion |
| Tracker author | tracker structure and program-revision history | source implementation or derived-evidence ownership |
| Implementation owner | current target source and current-range execution | tracker structure, supervision ledger, or release pointer |
| Supervision owner | canonical policy/events, changed-state review, and outcome evidence | target/tracker source or candidate self-selection |
| Evaluator | independently observed baseline/candidate outcomes | proposal, implementation, or promotion |
| Release/external-effect owners | their already-established effect surfaces | inferred authority from an evolution artifact |

Generator, selector, implementer, and evaluator identities are distinct. A
separately attributed consequential adjudicator is also required when current
evidence cannot resolve a material placement tradeoff.

## Artifact classes and authority

Every artifact is canonical JSON with exact keys, deterministic ordering, one
schema version, declared transformation version where a deterministic builder
exists, source identities, source hashes, currentness root, and its own root.
`product_program_contract_v1.json` is the machine-readable source for the exact
checkpoint input, artifact field sets, producing roles, and sibling interfaces;
unknown, omitted, or extra keys reject. Artifacts contain hashes and bounded
facts, not transcripts, hidden reasoning, secrets, or copied repositories.
The source map distinguishes a live owner path from an immutable `revision:path`
snapshot so truthful tracker status/evidence updates do not rewrite the accepted
planning source or create false currentness failures.

1. `product-program-evidence-packet` is deterministic, content-minimized, and
   nonauthorizing.
2. `product-program-reflection` contains observations, lessons, meta-patterns,
   gaps, counterexamples, and divergent candidates. It proposes no winner.
3. `product-program-resource-evidence` projects separately typed outcome and
   resource dimensions. It is neither billing truth nor spend authority.
4. `product-program-selection` records one disposition, comparison dimensions,
   rejected alternatives, and any independent adjudication.
5. `product-program-portfolio` describes zero or more tracker candidates, a
   dependency DAG, budgets, ownership, Stops, rollback/retirement, and placement.
6. `product-program-placement-handoff` names exactly one existing downstream
   owner and the preconditions it must revalidate. It is never an authorization.

The evidence assembler owns only `product-program-evidence-packet`; the
reflection generator owns only `product-program-reflection`; the resource-
evidence builder owns only `product-program-resource-evidence`; and the
portfolio selector owns `product-program-selection`, `product-program-portfolio`,
and `product-program-placement-handoff`. Producing an artifact never grants its
consumer role or any canonical write authority.

Deleting a derived artifact deletes no canonical evidence. The exact inputs can
rebuild it byte-for-byte.

## State transitions and Stops

The valid cycle is:

1. `checkpointed -> unchanged`: stop with a no-op result.
2. `checkpointed -> packet-prepared`: stop before semantic interpretation.
3. `packet-prepared -> reflected`: stop before ranking, budgeting, or placement.
4. `packet-prepared -> resource-projected`: stop before allocation.
5. `reflected + resource-projected -> selected`: stop before downstream writes.
6. `selected -> handoff-ready`: stop before authoring, task creation, source
   mutation, scheduling effects, release, or external action.

Any stale source, target mismatch, role conflict, failed validation, exceeded
ceiling, authority ambiguity, protected-capability regression, cyclic/overlapping
portfolio, or unsupported material-goal change stops the affected cycle. Safe
current-program work continues independently.

## Dispositions and placement

Selection chooses exactly one disposition:

- `continue-program-unchanged`
- `remediate-current-block`
- `revise-current-program`
- `start-successor-program`
- `start-program-portfolio`
- `run-bounded-experiment`
- `safe-defer-open-fact-or-authority`
- `request-material-goal-authority`

Placement is one of `none`, `current-block-owner`, `current-program-author`,
`successor-program-author`, `program-portfolio-author`, `experiment-owner`,
`reserved-effect-owner`, or `direct-user`. The disposition-to-placement map is
fixed in `product_program_contract_v1.json`; caller prose cannot override it.

`request-material-goal-authority` is limited to product-purpose changes,
irreversible or separately reserved effects, and user-specific tradeoffs not
resolved by current sources. Missing ordinary engineering judgment is not such
authority.

## Current work, history, and non-derailment

The direct requested range and accepted history remain authoritative while
prospective work is assessed. Evolution may recommend current-program revision
only for an evidenced prerequisite, correctness defect, protected-capability
loss, invalid architecture/acceptance contract, or later direct-user goal
change. It never contracts a range or treats a Block Stop, handoff, candidate,
budget, or successor as completion.

Structural application belongs solely to `author-implementation-trackers` and
must preserve an append-only old-to-new map. Accepted evidence is reopened only
across the mapped dependency closure of a concrete defect. Parallel plans remain
derived until every lane is separately authored, range-bound, admitted, and
started.

## Currentness, identity, and no-op convergence

The evidence packet binds the exact mission source/root, target profile,
repository realpath and revision/tree, product-source hashes, tracker path/hash/
structural root, requested and accepted Block sets, range head, outcome root,
protected-capability root, supervision policy/event heads, decision/incident
roots, report roots, resource-source roots, and transformation version.

The `material_change_fingerprint` covers only adjudicating semantic inputs. The
`currentness_root` additionally covers the current owner identities and heads.
Packaging, ordering-neutral duplicates, retry identity, and report prose cannot
create novelty. Identical fingerprints and currentness roots reuse identical
bytes. A changed owner head stales only artifacts that bind that owner.

## Resource and portfolio invariants

Resource evidence keeps product effect, protected-capability result, evidence
strength, recurrence/reach, compounding value, reuse, elapsed time, tokens,
commands/tools, validation/review, integration, rework, incidents, rollbacks,
user correction, uncertainty, reversibility, and opportunity cost separate.
Evidence classes are `observed`, `provider-reported`, `estimated`, `inferred`,
and `unavailable`. No aggregate utility or quality score is permitted.

A portfolio is acyclic. Every lane has one writer, writable scope, expected
effect, dependency set, resource ceiling, Stop, rollback/retirement posture, and
revisit trigger. Parallel lanes have disjoint writable scopes or one explicit
integration owner plus shared-resource exclusions. Aggregate ceilings never
exceed current operator ceilings. Unused capacity is retained; resource
availability creates neither relevance nor authority.

## Sibling-skill interfaces

- `author-implementation-trackers` may consume only a current accepted placement
  handoff for tracker structure. It revalidates mission, source roots, requested
  range, old-to-new mapping, review, and authoring scope.
- `implement-tracker-blocks` may request a cheap checkpoint and may consume only
  `remediate-current-block` through its existing adaptive decision owner. It
  continues the current requested range regardless of prospective work.
- `supervise-tracker-runs` remains the canonical event/policy and changed-state
  owner. It may provide source identities and independent review but cannot
  select its own finding into product work.
- `skill_release.py`, automation, Gmail, deployment, credential, spend,
  destructive, and other external-effect owners accept no authority from these
  artifacts.

The exact interface records in `product_program_contract_v1.json` bind each
consumer, accepted input kind, produced output kind, revalidation fields, and
whether the interface may apply an effect. The three sibling skill interfaces
are nonauthorizing requests or handoffs until the named existing owner accepts
them; the release/external interface always has `apply_effect: false` in this
contract.

## Rejection rules

Reject any artifact or transition that lets evolution directly write a tracker,
target source, supervision state, release pointer, automation, message, or
external effect; treats a report or estimate as canonical fact; copies bounded
source content beyond the contract; changes product intent; hides a conflicting
observation; omits the unchanged option; permits self-selection/self-evaluation;
overlaps parallel writers; loses accepted history; starves current requested
work; or lacks a deterministic Stop.
