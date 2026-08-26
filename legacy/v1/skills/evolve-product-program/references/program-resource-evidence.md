# Product-program resource and outcome evidence

Block 3 owns a deterministic, derived budgeting prior. It keeps outcome quality
and resource use as separate evidence-typed dimensions. It does not rank work,
allocate capacity, claim provider billing, authorize spend, select a candidate,
or create an external effect.

## Source and currentness boundary

One canonical `product-program-resource-source` manifest must be byte-length and
SHA-256 bound to a retained packet `resource_sources` entry. Raw resource records
remain separate retained packet sources. Each non-unavailable resource dimension
must cite one of those raw sources, and the same source/dimension pair cannot be
attributed to more than one work class.

Outcome dimensions must cite observed outcome, protected-capability, product,
decision, or incident evidence. Report or resource hypotheses alone cannot prove
product effect. The derived currentness root binds the exact packet root, packet
currentness root, canonical source-manifest root, and transformation version.

## Evidence classes and dimensions

Every value is explicitly `observed`, `provider-reported`, `estimated`,
`inferred`, or `unavailable`. `provider-reported` is supported only for token
resources and rejects for every outcome.
Observed and provider-reported numeric values are exact bounds; estimated or
inferred values remain ranges. Unavailable dimensions retain the evidence for
the bounded search but carry no numeric or categorical result.

Each work class keeps these outcome dimensions separate:

- completion, product effect, and protected-capability result;
- recurrence/reach, compounding value, reuse, and reversibility;
- opportunity cost.

Each work class separately records elapsed time, tokens, commands, tools,
validation/review, integration, rework, reopened findings, incidents, rollbacks,
and user corrections. Estimated values require the exact retained versioned
estimation profile. Every estimated or inferred row root binds that exact profile
identity, while all-observed rows may be reused across a profile-only change.
Estimates and inferences require genuine lower/upper intervals; point precision
is reserved for observed or provider-reported evidence. An estimate cannot
fabricate completion, product effect, or protected-capability results.

Semantic method and uncertainty values are closed identifiers rather than free
prose. The only v1 estimation method is
`bounded-retained-event-counts-v1`; evidence-class uncertainty identifiers are
fixed by the builder; useful yield requires `association-not-causal` and
`rare-high-value-work-preserved`. Billing, utility, score, ranking, or speed
claims therefore cannot hide in otherwise valid text.

## Useful-yield and economy boundary

Useful yield is a dimension-by-dimension comparison posture over every outcome
and resource dimension plus explicit uncertainty. No score, rank, weighted
utility, price, billing, spend, or aggregate total is accepted. This preserves
rare high-value work and prevents speed or low estimated cost from masquerading
as product value. Observed association is not represented as causal proof.

Exact unchanged packet/source/artifact bytes reuse with zero model work. When a
source manifest changes, the builder may take one rooted prior artifact and
reuse only rows whose normalized source-input roots still match; changed rows
are rebuilt. Derived deletion loses no canonical evidence.

## Stop

Stop after a verified resource-evidence artifact or exact zero-work reuse. Do
not select a candidate, allocate a budget, schedule a lane, place work, write a
tracker, authorize spend, or perform an external effect.
