# Software Factory v2 Internal Service Runbook

## Boundary

This entrypoint is a single-operator, loopback-only service over the same
durable Factory engine used by the embedded host. It is not a hosted product,
public authentication system, tenant boundary, fleet controller, or Internet
deployment target. The HTTP transport never grants Factory authority.

The two qualified utils packages are unpublished internal artifacts with no
license selected. This runbook does not grant public installability, reuse,
redistribution, or release authority. Never resolve either artifact by a bare
registry name/version and never copy its source into Software Factory.

## Exact qualified inputs

Start only with artifacts that satisfy
`runtime/src/software_factory/provider_pins/qualified-utils.json`. The active
Block 9 pins are:

- utils producer revision
  `a5659745a7cbcbb002b5f06051f6ed9826f721a7`;
- `embedded-service-contract` source commit
  `401f87a64349c636a66be2da656498e7d9cb58e3`, package tree
  `203c809f3d1ab2588df5ed83c08affde99f8010c`, version `0.1.0`, wheel SHA-256
  `2b36d7307c08cd6d7d95bfb86d4a240b6ab2a69de5b2c61bf75a54507c7ea18d`;
- `runtime-manifest` source commit
  `6f7a7ea3c105c7461e6cb4c83944dd094883f187`, package tree
  `42cb7171d3de021a99f75ac741ea0a0cf97c84ae`, version `0.1.0`, wheel SHA-256
  `f2e601d542272187998296f09d33b2235002d108fe07c0b3c89a678ea1d010ac`.

Startup recomputes the exact wheel SHA-256, deterministic content root,
member count, uncompressed byte count, and accepted public-contract hashes.
Any mismatch fails closed before the server binds.

## Credential preparation

Generate a high-entropy transport token using the platform credential manager
or an approved secret generator. Store exactly one printable 32–512 character
token in a regular file readable only by its owner (mode `0600`). Symlinks,
group/world-readable files, multiline values, and oversized files are rejected.
Do not place the token in argv, a URL, the database, a runtime manifest, or a
dashboard-saved browser preference.

The service bearer token authenticates only the HTTP transport. Governed
operator actions additionally require a separately issued, scoped, expiring,
single-use token in `X-Software-Factory-Operator-Token`. A session ID, agent ID,
or service bearer token cannot substitute for that authority.

## Start

From an installed exact Software Factory candidate, run:

```sh
software-factory-api \
  --home /absolute/private/factory-home \
  --host 127.0.0.1 \
  --port 8765 \
  --service-token-file /absolute/private/service-token \
  --embedded-contract-wheel /absolute/qualified/embedded_service_contract-0.1.0-py3-none-any.whl \
  --runtime-manifest-wheel /absolute/qualified/runtime_manifest-0.1.0-py3-none-any.whl \
  --component-root <64-lowercase-hex-content-root>
```

The component root must identify the exact deployed Factory component content,
not a branch name or floating version. The process refuses non-loopback binds.

## Probes and operational routes

- `GET /health` is unauthenticated, content-minimal process liveness.
- `GET /ready` is unauthenticated, content-minimal readiness and returns `503`
  until the database, engine service, exact qualified utilities, and descriptive
  runtime manifest are all valid.
- Every `/api/*` route requires `Authorization: Bearer <service-token>`.
- `GET /api/health` is the authenticated component readiness projection.
- `GET /api/runtime-manifest` returns exact descriptive compatibility metadata;
  it contains no authorization, acceptance, or release authority.
- `GET /api/factory-floor` and `GET /api/missions/<id>` return bounded,
  content-minimized operator projections. Authority roots, resource payloads,
  external task/thread identifiers, repository paths, command bodies, and
  unbounded evidence JSON are excluded.
- `POST /api/engine/{start,status,continue,outcome,events}` is the closed service
  operation set. Every POST also requires the exact current service protocol
  root (the 64 hexadecimal digits after `sha256:` for the
  `software-factory-loopback-service` protocol in the authenticated runtime
  manifest) in
  `X-Software-Factory-Workflow-Root`; stale or missing roots fail closed.
  Cancellation is intentionally absent from this general route.
- `POST /api/operator-actions` requires both transport authentication and a
  distinct one-time operator token.

Requests are JSON objects with an explicit content length of at most one MiB;
request targets and response bodies are also bounded. Chunked transfer,
arbitrary commands, arbitrary paths, unknown effects, and raw exception detail
are rejected.

## Restart and shutdown

`SIGINT` and `SIGTERM` stop request handling, close the listener, and retain all
mission truth in the existing durable Factory database. A new process opened on
the same home observes the same mission status, event cursor, and outcomes. It
must re-verify the exact utilities and receive the service token file again.

After restart, check `/health`, then `/ready`, then authenticated `/api/health`.
Do not infer Factory completion from process uptime, transport success, an HTTP
`200`, or a runtime manifest. Only the existing server-side workflow,
currentness, QA, independent review, acceptance, and terminal outcome owners
can establish those facts.
