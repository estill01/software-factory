# Software Factory v2 provider compatibility

Block 4 exposes one Factory-owned assignment contract through replaceable
provider adapters. Provider completion is submitted evidence only. It does not
select work, approve an effect, satisfy QA, accept work, close an obligation, or
close a mission.

| Provider | Process owner | Durable restart identity | Cancellation | Bounds and callback posture | Qualification |
| --- | --- | --- | --- | --- | --- |
| `DeterministicProvider` | injected host/test owner | Factory execution ID | deterministic observation | prompt-byte bound; no external callback channel | offline fixture and replay |
| `ProcessProvider` / `CodexCLIProvider` | one registry owner per resolved state root | execution ID plus Factory-owned status/output paths and PID observation | process-group termination | prompt/output bounds; command builder is Factory-owned | local-process fallback |
| `CodexAppServerProvider` | one registry owner per explicit composition key | execution, assignment, work, workspace, lease, exact thread/turn, and exact producer roots | exact typed thread/turn interrupt | prompt/event/callback/operation bounds; command and file approvals are declined; external input interrupts fail closed | exact internal wheel and protocol pin below |
| `ExternalAgentProvider` | injected external owner | host-supplied handle under the Factory execution | injected bounded cancel operation | prompt-byte bound; callback token remains Factory-local | consumer-supplied adapter |

The app-server lane consumes only the accepted internal
`codex-app-server-client==0.1.0` wheel. The Factory pin binds utils producer
revision `a5659745a7cbcbb002b5f06051f6ed9826f721a7`, accepted source commit
`08c416da4202b7036110e33e43d34ea590054e2e`, source tree
`794650275e9a583c9f47276a271f65cc1020c4e8`, package tree
`17772f61da62b41d6d3551deebc474792aafe922`, wheel SHA-256
`1e9dc5b9c7f2edb9676b5a47eb2c9b96498f1b429acec474cd26702fe8e3fdb9`,
wheel content root
`6ecc26e75197d06682fe9d8d0612edb1e56ead6d04c3a41cde1132e2618efd8f`,
Codex `0.147.0`, retained schema root
`eb325d394d19f2f8d133203885b3d1c2f74dbc5a176f22078a4f99aae5926faa`,
and selected-surface root
`9a773e75f2e5aa827b4cc711345bd9ca1bc2a037f19d114284a04f306097a42f`.

Resolution by a bare registry name/version and copied utils source are both
prohibited. The similarly named public PyPI wheel is unrelated. The accepted
producer remains unpublished with no selected license; this internal pin
grants no public installability, reuse, redistribution, or release authority.

The adapter's diagnostic is intentionally non-generative: it verifies the
exact wheel, executable, version, retained schema, and selected surface;
initializes one owned app-server generation; performs one typed bounded
`thread/list(limit=1)`; and closes the process. It starts no model turn and
does not inspect or mutate a target repository.
