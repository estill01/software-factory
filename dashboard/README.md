# Software Factory Operations Dashboard

The dashboard is a local, single-operator control room. It currently provides
the loopback runtime, typed transport, accessible application shell, and a
bounded multi-project catalog. Tracker contents, Codex tasks, supervision,
reports, and lifecycle truth remain visibly unavailable until their owning
tracker Blocks are accepted.

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
plumbing.

## Register projects

Open **Admin** and register an exact canonical Git top-level path. The dashboard
never scans the workstation for repositories. Catalog records contain only a
stable ID, display label, canonical root, optional relative Markdown tracker
globs, optional description, and archived posture. They never copy task, run,
tracker, report, supervision, or completion state.

The versioned catalog is stored at:

```text
~/.codex/software-factory/dashboard/projects.json
```

The file is created only on the first mutation, written atomically with
owner-only permissions, deterministically ordered, and protected by an
optimistic source fingerprint. A valid prior file can be projected read-only
when the current file is malformed. Use `--catalog-path /absolute/path.json`
for isolated testing or an alternate local profile.

The project API surface is deliberately narrow:

```text
GET   /api/v1/projects?include_archived=false
GET   /api/v1/projects/{project-id}
POST  /api/v1/projects
PATCH /api/v1/projects/{project-id}
```

Writes require the exact page origin and per-launch nonce. Supported actions
are registration, presentation updates, archive, and unarchive. Archiving only
removes a project from normal dashboard views; it never deletes files, changes
the repository, stops work, or changes source truth.

Discovery is bounded to registered roots and reports Git revision/branch plus
tracker candidate paths. Candidate contents are not read yet. Each project has
its own observed time, coverage, limitations, and exact discovery errors, so a
missing repository does not hide healthy projects.

## Browser tests

With the production service running on port 8787:

```bash
SOFTWARE_FACTORY_DASHBOARD_URL=http://127.0.0.1:8787 \
  npm --prefix dashboard/web run test:e2e
```

The server never performs broad filesystem discovery and never exposes
arbitrary commands, authentication, remote binding, filesystem deletion, or
background work. Catalog readiness does not imply that tracker, task,
supervision, report, or lifecycle sources are connected.
