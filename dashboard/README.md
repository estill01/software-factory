# Software Factory Operations Dashboard

The dashboard is a local, single-operator control room. Block 1 provides only
the loopback runtime, typed transport, accessible application shell, and honest
integration placeholders. Project discovery and live Factory data arrive in
later tracker Blocks.

## Prerequisites

- Python 3.11 or newer and `uv`
- Node.js 24 and npm 11
- Codex CLI 0.145.0 for the frozen App Server compatibility contract

No global frontend package installation is required.

## Install and validate

```bash
npm --prefix dashboard/web ci
uv sync --project dashboard/server
npm --prefix dashboard/web run check
uv run --project dashboard/server python -m unittest discover \
  -s dashboard/server/tests -p 'test_*.py'
```

## Develop

Run the API on a free loopback port, then start Vite. Both defaults deliberately
avoid port 5173.

```bash
uv run --project dashboard/server software-factory-dashboard --port 8787
SOFTWARE_FACTORY_DASHBOARD_PORT=8787 npm --prefix dashboard/web run dev
```

Open `http://127.0.0.1:5188`. Vite proxies `/api` to the Python service.

## Build and run the production shell

```bash
npm --prefix dashboard/web run build
uv run --project dashboard/server software-factory-dashboard --port 8787
```

Open `http://127.0.0.1:8787`. Choose another free port with `--port`; the
service rejects non-loopback hosts. The production server serves the Vite build,
SPA routes, `/api/v1/health`, security headers, and per-launch mutation-nonce
plumbing. Block 1 intentionally exposes no mutation endpoint.

## Browser tests

With the production service running on port 8787:

```bash
SOFTWARE_FACTORY_DASHBOARD_URL=http://127.0.0.1:8787 \
  npm --prefix dashboard/web run test:e2e
```

The server never scans projects in Block 1 and never exposes broad filesystem
paths, arbitrary commands, authentication, remote binding, or background work.
