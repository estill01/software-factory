# Software Factory v2 neutral content and external-extension contract

Block 10 proves that target profiles change physical targets while the existing
Factory runtime continues to own missions, programs, obligations, work,
scheduling, agents, QA, supervision, staged acceptance, and terminal outcome
closure. A target profile cannot accept its own output.

## Maintained neutral content profile

`ContentTargetProfile` is composed into every `CoreService`. A host registers a
target with one empty target root plus a fixed title, audience, factual sources,
and source-bound section plan. Effect calls remain exact-revision and
exact-currentness fenced by `TargetProfileRegistry`.

| Fixed effect | Closed operation | Observable target result |
| --- | --- | --- |
| `workspace` | `collect_sources` | canonical source inventory |
| `command` | `plan`, `draft`, `revise` | plan, initial draft, and cited document |
| `test` | `review_factual`, `review_structural`, `review_style` | exact source, structure, and quality reports |
| `build` | `render` | deterministic escaped HTML artifact |
| `release` | `deliver` | internal delivered artifact and exact receipt |
| `test` | `verify_delivery` | byte- and definition-bound delivery report |

The effect argument contract admits only the registered operation name. It does
not accept caller paths, commands, authority, approval, acceptance, release
policy, or free-form content. Rendering requires all three content reviews;
delivery requires the exact reviewed render; delivery verification requires
the exact artifact and receipt. Symlinks and non-regular target members fail
closed.

The maintained dogfood creates a real mission, capability, obligation, program,
selected work item, implementer execution, and independently reviewed
candidate/integrated/installed/terminal acceptance chain. The generic QA owner
submits the profile snapshot as the work candidate only when the successful
execution, work declaration, registered profile/target, exact revision, and
exact currentness root all agree. Program range closure, capability
end-to-end verification, obligation satisfaction, terminal verification, and
mission completion then use the ordinary runtime owners.

## External extension proof

`runtime/tests/external_extension_fixture.py` is intentionally outside
`runtime/src/software_factory`. It implements the public target-profile protocol,
registers through the existing `TargetProfileRegistry`, and completes a separate
delivered mission through the same QA and acceptance helper as the maintained
content profile. Its target identifiers, record schema, and physical effect code
never enter the Factory package.

An external profile must:

- expose one stable key and a nonempty subset of the fixed `EffectClass` values;
- bind the registry-provided authority once and reject every direct executor call;
- return exact target revision and currentness snapshots;
- keep an explicit closed argument contract for each physical effect;
- submit candidates through `QAService.submit_profile_candidate`; and
- leave mission, agent, evidence, review, acceptance, and outcome authority in
  Factory.

Registration does not grant acceptance and provider/execution completion does
not establish QA. A consumer remains responsible for its profile code, target
schema, fixtures, physical effects, and product-specific policy outside this
repository.

## Leakage and negative boundary

Mapped tests scan the installed package source for the external fixture's key,
target ID, and schema markers, as well as prohibited consumer product names.
They also verify that the content profile contains no repository, branch, or Git
snapshot schema. Tests reject unregistered arguments, direct adapter execution,
out-of-order effects, stale target bytes, missing quality review, artifact drift,
receipt drift, target-profile substitution, and a terminal claim before the
independent acceptance chain and actual delivered outcome are current.
