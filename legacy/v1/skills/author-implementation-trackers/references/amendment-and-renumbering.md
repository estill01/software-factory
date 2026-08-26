# Amendment and renumbering

Treat a tracker amendment as a controlled planning change. Preserve history and
make future execution unambiguous.

## Before editing

1. Read the full live tracker and repository instructions.
2. Inspect Git status and preserve unrelated or in-flight changes.
3. Identify the active implementation/audit boundary. Do not relabel, interrupt,
   or contaminate it merely to land a planning amendment.
4. Separate historical evidence from prospective requirements.
5. List every surface that carries block numbers: headings, status table,
   dependencies, required-order chain, prose references, source maps,
   verification matrix, terminal count, and external handoff notes.

## Adding or splitting blocks

- Insert at the earliest correct dependency point.
- Keep each new block single-focused and give it its own acceptance and stop.
- Shift later numbers continuously.
- Leave new work `not-started` unless exact current evidence independently
  proves the entire new contract.
- Do not reopen accepted work unless a concrete in-scope defect requires a
  bounded remediation.

## Renumbering

1. Build an explicit old-to-new mapping.
2. Change headings and status rows first.
3. Update dependencies and required-order expressions.
4. Update semantic references one by one; do not use an unreviewed global digit
   substitution.
5. Update source/adaptation maps, verification matrices, completion-ledger
   scope, terminal block, and final completion definition.
6. Add a concise renumbering note when historical commits, reviews, or evidence
   use the old numbers.
7. Verify continuous headings, table agreement, acyclic dependencies, and no
   stale sequence claim.

## Preserving accepted history

- Never rewrite an accepted commit, review, finding, or prior evidence row to
  manufacture present-day closure.
- Append remediation evidence and a fresh corrected-revision review.
- Preserve rejected candidates when their history matters.
- Mechanically corrected forward references may change without changing the
  substantive accepted evidence.
- Status must describe current tracker truth: accepted work remains accepted;
  reopened work states why and what exact dependency or finding reopened it.

## Amendment completion

Before handing off:

- run the tracker verifier;
- run repository documentation/change-mapping checks;
- inspect the diff for unrelated substantive edits;
- state exactly which sections and blocks changed;
- state the new first eligible block and preserved stop boundary.
