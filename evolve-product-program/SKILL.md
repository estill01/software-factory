---
name: evolve-product-program
description: Reflect on current product, implementation-program, supervision, outcome, and resource evidence; generate and challenge future-work candidates; and select one bounded nonauthorizing program portfolio for existing Software Factory owners. Use after a material implementation or supervision change, at a terminal checkpoint, or when an explicit product-program evolution cycle is requested. Do not require it before the first user-seeded tracker.
---

# Evolve Product Program

Turn one exact, current product/program checkpoint into a bounded derived
evidence packet and, only after the later semantic stages apply, one
nonauthorizing placement handoff. The user's governing product intent and the
current requested implementation range remain authoritative throughout.

## Load the contract

Read `references/product-program-evolution-contract.md` completely. For packet
preparation, also read `references/program-evidence-packet.md`. Later reflection,
resource, selection, and placement stages must read their own references when
present; do not infer later-stage authority from the packet contract.

## Preserve the first loop

Do not invoke evolution as a prerequisite for the first tracker. The cold-start
path remains direct intent to tracker authoring to implementation plus optional
supervision. Invoke this skill only from an exact material-change, terminal, or
explicit maintenance checkpoint.

## Prepare deterministic evidence

Use the repository-owned CLI from the repository root:

```bash
/usr/bin/python3 evolve-product-program/scripts/product_program_evolution.py \
  prepare --input <checkpoint.json> [--prior-packet <packet.json>]
```

The checkpoint must match the exact schema in
`fixtures/product_program_contract_v1.json`. The preparer validates exact Git,
tracker, range, outcome, protected-capability, supervision, decision, incident,
report, and resource-source currentness. It reads bounded regular files through
no-follow paths and retains identities, hashes, evidence classes, and byte
counts—not source content, transcripts, prompts, hidden reasoning, or secrets.

Verify a retained packet independently:

```bash
/usr/bin/python3 evolve-product-program/scripts/product_program_evolution.py \
  verify --packet <packet.json>
```

Identical semantic and currentness identities return
`continue-program-unchanged` with zero cognitive/model work. A changed identity
prepares one successor packet; it does not itself start reflection.

## Authority boundary

Every output is derived and nonauthorizing. This skill does not write trackers,
target source, supervision policy/events, release state, automations, messages,
deployments, credentials, spend, destructive effects, or other external state.
Existing sibling owners must independently revalidate and accept a later
placement handoff before any canonical application.

## Stop

For packet preparation, stop after a verified packet or deterministic unchanged
result. Do not interpret evidence, generate candidates, select work, allocate a
portfolio, edit a tracker, create a task, or perform an external effect.
