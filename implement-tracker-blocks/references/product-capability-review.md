# Product-capability review

Use this review to select the implementation level for one active Block. It is
an execution aid, not a new product authority, approval gate, runtime monitor,
or reason to enlarge the Block.

## Contents

- [Trigger and fast path](#trigger-and-fast-path)
- [Reuse the accepted frame](#reuse-the-accepted-frame)
- [Compare three implementation levels](#compare-three-implementation-levels)
- [Required checks](#required-checks)
- [Completion-evidence binding](#completion-evidence-binding)

## Trigger and fast path

Run the review once when either condition is true:

1. the Block's `Target-product capability delta` posture is `consequential`; or
2. live repository evidence exposes a concrete drift trigger despite a routine
   declaration: changed feature behavior, canonical representation,
   architecture strategy, operating model, protected capability, an owner
   bypass, or a Block delta that conflicts with direct product sources.

For a `routine` or `not-applicable` Block with no concrete trigger, do not run
the comparison. Retain the normal implementation path and, when completion
evidence needs the distinction, record only
`Product-capability review: not triggered — <concrete reason>`.

A trigger authorizes this bounded comparison only. It does not override direct
mission authority, expand Block scope, or authorize monitoring, rearchitecture,
or a generalized platform.

## Reuse the accepted frame

Read the tracker-level `Target-product capability frame` and the active Block's
delta once. Record the frame path, content hash, and Block number in the active
execution brief; do not create a new artifact unless the tracker requires it.
The frame content is the exact UTF-8 Markdown bytes from its heading through the
line before the next heading of the same or higher level. Preserve those bytes,
including line endings, and record their SHA-256; do not normalize or hash the
whole tracker as a substitute.
Use the frame's direct product sources, thesis and intended effect, protected
capabilities, architecture strategy, requested capability, proportionality,
tradeoffs, and uncertainty. Reuse the hash for the rest of the Block.

Inspect only the named live owners needed to test those claims. Widen to one
additional source or owner only when one named missing product fact could
materially change the selection. If direct sources do not resolve that fact,
preserve it as the smallest dependency cut; do not invent product intent.
An evident adjacent need must resolve to a named current consumer, accepted
near-term Block, or direct source—not a hypothetical future use.

## Compare three implementation levels

Compare these levels explicitly. A level may be unavailable; say why rather
than fabricating a candidate.

1. **Smallest local path** — a direct change in the narrow local owner. It is
   eligible only if it delivers the full supported capability and preserves
   protected behavior, canonical representation, and evident composability.
2. **Bounded-general path** — the smallest reusable seam needed by the current
   requirement and a concrete evident adjacent need. It must remain bounded to
   named consumers and must not become a platform for hypothetical reuse.
3. **Available architectural owner** — an existing canonical owner, shared
   abstraction, or operating boundary that already governs the capability. Use
   it when local implementation would bypass authority, fragment canonical
   state, or substitute a lower-power behavior.

Select the lowest-complexity eligible level. “Local” does not win when it
under-delivers the supported product capability; “general” does not win because
future reuse is imaginable. Prefer an existing architectural owner when it is
already authoritative, not because architectural work is inherently better.

## Required checks

Before editing, and again against the frozen candidate, answer:

- **Capability:** What operator- or user-visible capability is added or
  preserved, beyond the literal requested mechanism?
- **Protected regression:** Does the path weaken a protected behavior,
  authority, compatibility guarantee, or current operator-visible effect?
- **Canonical owner:** Does it write around, duplicate, or obscure the owner of
  canonical state or behavior?
- **Lower-power substitution:** Does a locally passing implementation omit a
  source-supported consumer, effect, representation, or operating need?
- **Composability:** Does it remove a current or evident adjacent composition
  path that the sources support?
- **Speculative generalization:** Does it add a service, platform, registry,
  framework, remote mode, or abstraction supported only by hypothetical use?
- **Scope and authority:** Does the selection remain inside the active Block
  and direct mission? Product framing never overrides either.

Any supported failure reopens only the narrow affected owner or tracker slice.
Tests and a populated review record are process evidence; current behavior must
still demonstrate the capability.

## Completion-evidence binding

For a triggered review, add this compact record to the Block's existing
completion evidence:

```markdown
- Product-capability review:
  - Trigger: `<consequential posture or exact drift>`
  - Frame identity: `<tracker path, Block, content hash>`
  - Capability added or preserved: `<observable capability>`
  - Paths compared: `<local; bounded-general; architectural owner>`
  - Selected level and owner: `<selection and source-backed reason>`
  - Protected-capability result: `<preserved, changed, or reopened with proof>`
  - Rejected alternatives: `<why lower-power or speculative paths lost>`
  - Tradeoffs and uncertainty: `<accepted costs, limits, and unresolved facts>`
  - Frozen-candidate proof: `<commit/root plus current behavioral evidence>`
```

Do not claim the capability from local test success alone. If a named missing
fact changes the eligible path, record the exact blocked subject, safe frontier,
and revisit trigger under the existing dependency-cut contract.
