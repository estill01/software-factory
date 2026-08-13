import type { FactoryFloorEnvelope, FactoryFloorRow } from "@/lib/floor-api"

const observed = "2026-08-09T17:55:00.000Z"

function row(
  id: string,
  projectId: string,
  posture: FactoryFloorRow["light"]["posture"],
  options: { supervised?: boolean; block?: string; issues?: number } = {},
): FactoryFloorRow {
  const supervised = options.supervised ?? true
  const issues = options.issues ?? 0
  const blockNumber = options.block ? Number(options.block) : null
  const trackerTotal = options.block ? (options.block === "6" ? 26 : 8) : 4
  const acceptedBlocks = options.block ? (options.block === "6" ? 5 : 3) : 2
  const blockTitle = options.block
    ? options.block === "6"
      ? "Factory Floor composition"
      : `Tracker-owned Block ${options.block}`
    : null
  const blockRef = blockNumber === null
    ? []
    : [{
        number: blockNumber,
        title: blockTitle,
        status: "in-progress",
        line: 120 + blockNumber,
        route: `/trackers/${projectId[0].repeat(64)}/blocks?block=${blockNumber}`,
      }]
  const roles: FactoryFloorRow["supervision"]["roles"] = supervised
    ? [
        {
          role: "routine_watcher",
          label: "Watcher",
          thread_id: `watcher-${id}`,
          binding_status: "bound",
          task_status: "idle",
          automation_status: "available",
        },
        {
          role: "semantic_reviewer",
          label: "Reviewer",
          thread_id: `reviewer-${id}`,
          binding_status: "bound",
          task_status: "idle",
          automation_status: "unavailable",
        },
      ]
    : []
  return {
    id: `${supervised ? "run" : "task"}:${id}`,
    project: {
      status: "bound",
      project_id: projectId,
      label: projectId[0].toUpperCase() + projectId.slice(1),
      reason: "Exact current source binding.",
    },
    implementation: {
      task_id: id,
      name: `${projectId[0].toUpperCase() + projectId.slice(1)} implementation`,
      status: posture === "neutral" ? "idle" : "active",
      status_label: posture === "neutral" ? "Idle" : "Active",
      updated_at: observed,
      source_status: "available",
    },
    supervision: {
      run_id: supervised ? id : null,
      group_id: supervised ? `group-${id}` : null,
      target_thread_id: id,
      status: supervised ? "active" : "unmonitored",
      status_label: supervised ? "Supervising" : "Unmonitored",
      binding_integrity: supervised ? "valid" : "unavailable",
      roles,
      role_count: roles.length,
      last_check: supervised
        ? {
            record_id: `check-${id}`,
            kind: "check",
            status: "ok",
            severity: null,
            category: "routine",
            summary: "Latest supervisor check.",
            action: "Continue.",
            resolution: null,
            observed_at: observed,
            source: null,
          }
        : null,
      next_check: {
        status: "unavailable",
        at: null,
        reason: "No canonical next occurrence.",
      },
    },
    work: {
      active_block: options.block ?? null,
      checkpoint: options.block ? "Implementation" : null,
      mission_root: supervised ? "m".repeat(64) : null,
      last_action: supervised ? "Continue bounded work." : null,
      tracker: {
        status: options.block ? "exact" : "candidate",
        id: `${projectId[0]}`.repeat(64),
        title: `${projectId} tracker`,
        relative_path: `docs/${projectId}-implementation-tracker.md`,
        candidates: [],
      },
      block_claims: {
        posture: options.block ? "exact" : "partial",
        tracker_total: {
          value: trackerTotal,
          posture: options.block ? "exact" : "partial",
          reason: options.block
            ? "Maintained verifier Block set for the exact canonical tracker binding."
            : "Maintained verifier Block set for a noncanonical tracker candidate.",
        },
        tracker_progress: {
          accepted: acceptedBlocks,
          remaining: trackerTotal - acceptedBlocks,
          posture: options.block ? "exact" : "partial",
          is_complete: options.block ? false : null,
          reason: options.block
            ? "Maintained tracker counts for the exact canonical tracker binding."
            : "Maintained tracker counts for a noncanonical tracker candidate; row progress is partial.",
        },
        claims: [
          {
            source: "tracker",
            label: "Tracker",
            status: options.block ? "exact" : "partial",
            blocks: blockRef,
            range: null,
            reason: options.block
              ? "Maintained tracker status identifies the current Block set."
              : "Current Blocks come from a project-local tracker candidate.",
            source_identity: "tracker-markdown/status",
            route: `/trackers/${projectId[0].repeat(64)}/blocks`,
          },
          {
            source: "task",
            label: "Implementation task",
            status: options.block ? "exact" : "unavailable",
            blocks: blockRef,
            range: blockNumber === null ? null : { start: blockNumber, end: blockNumber },
            reason: options.block
              ? "The active task's exact dashboard workflow marker names one Block."
              : "The task owner exposes no exact current Block claim.",
            source_identity: "codex-app-server/task-workflow-marker",
            route: `/tasks/${id}`,
          },
          {
            source: "supervision",
            label: "Current supervision mission",
            status: options.block ? "exact" : "unavailable",
            blocks: blockRef,
            range: null,
            reason: options.block
              ? "The current mission's latest activity names this active Block."
              : "No current supervision mission is available.",
            source_identity: "supervise-tracker-runs/current-mission-activity",
            route: supervised ? `/runs/${id}` : "/runs",
          },
        ],
      },
    },
    issues: { incidents: issues, decisions: 0, transitions: 0, total: issues },
    conclusion: supervised
      ? {
          record_id: `conclusion-${id}`,
          kind: "meta-review",
          status: "accepted",
          severity: null,
          category: "outcome",
          summary: "The current review accepted the predecessor.",
          action: "Advance in order.",
          resolution: null,
          observed_at: observed,
          source: null,
        }
      : null,
    light: {
      posture,
      label: posture === "red" ? "Action required" : posture === "green" ? "On track" : "Unmonitored",
      reason: posture === "red"
        ? "A current incident remains open."
        : posture === "green"
          ? "No current issue rule is active."
          : "No supervision group is bound to this implementation task.",
      observed_at: observed,
      source_identity: supervised ? "supervise-tracker-runs/operating-light" : "codex-app-server/task-state",
      completion_claim: false,
    },
    freshness: {
      status: "current",
      observed_at: observed,
      reason: "Newest exact observation.",
    },
    disagreements: [],
    detail: {
      kind: supervised ? "run" : "task",
      id,
      route: `/?inspect=${supervised ? "run" : "task"}:${id}`,
      source_refs: [{
        kind: supervised ? "supervision-run" : "codex-task",
        identity: id,
        record_id: supervised ? null : id,
        path: supervised ? `/sources/${id}` : null,
        line: null,
        revision: supervised ? "e".repeat(64) : null,
        route: `/?inspect=${supervised ? "run" : "task"}:${id}`,
      }],
    },
  }
}

const metric = (key: string, label: string, value: number | null, estimate = false) => ({
  key,
  label,
  value,
  unit: estimate ? "USD estimate" : "count",
  period: "Current owner period",
  coverage: "3 registered projects",
  source_identity: `fixture/${key}`,
  estimate,
  available: value !== null,
})

export function makeFactoryFloorEnvelope(): FactoryFloorEnvelope {
  return {
    data: {
      catalog_fingerprint: "a".repeat(64),
      recovered_from_previous: false,
      summary: {
        registered_projects: 3,
        active_implementations: 2,
        supervisor_groups: 2,
        action_required: 1,
        postures: { red: 1, amber: 0, green: 1, neutral: 1 },
      },
      projects: [
        { id: "alpha", label: "Alpha" },
        { id: "beta", label: "Beta" },
        { id: "gamma", label: "Gamma" },
      ],
      rows: [
        row("target-alpha", "alpha", "red", { block: "6", issues: 1 }),
        row("target-beta", "beta", "green", { block: "3" }),
        row("task-gamma", "gamma", "neutral", { supervised: false }),
      ],
      rows_truncated: false,
      attention: [
        {
          id: "attention:alpha:incident",
          rank: 1,
          rule: "open-incident",
          severity: "red",
          target_thread_id: "target-alpha",
          project_id: "alpha",
          reason: "A current incident remains open.",
          owner: "supervise-tracker-runs/incidents",
          safe_frontier: "Continue only dependency-safe work.",
          observed_at: observed,
          source: {
            identity: "supervise-tracker-runs/incidents",
            record_id: "INC-1",
            path: "/sources/alpha/events.jsonl",
            line: 8,
            route: "/?inspect=attention:target-alpha:INC-1",
          },
        },
        {
          id: "attention:gamma:unmonitored",
          rank: 2,
          rule: "unmonitored-implementation",
          severity: "neutral",
          target_thread_id: "task-gamma",
          project_id: "gamma",
          reason: "A recent task has no exact supervision run.",
          owner: "codex-app-server/task-state",
          safe_frontier: null,
          observed_at: observed,
          source: {
            identity: "codex-app-server/task-state",
            record_id: "task-gamma",
            path: null,
            line: null,
            route: "/?inspect=task:task-gamma",
          },
        },
      ],
      attention_summary: {
        total: 2,
        returned: 2,
        truncated: false,
        critical_total: 1,
        critical_returned: 1,
        critical_omitted: 0,
      },
      conclusions: [{
        id: "conclusion:target-alpha:review-1",
        target_thread_id: "target-alpha",
        target_label: "Alpha implementation",
        author: null,
        author_status: "unavailable",
        disposition: "accepted",
        summary: "The current review accepted the predecessor.",
        next_action: "Advance in order.",
        current: true,
        superseded: false,
        observed_at: observed,
        source: {
          identity: "supervise-tracker-runs/events.jsonl",
          record_id: "review-1",
          path: "/sources/alpha/events.jsonl",
          line: 9,
          revision: "c".repeat(64),
          route: "/?inspect=conclusion:target-alpha:review-1",
        },
        retained_open_work: 1,
      }],
      accepted_outcomes: [{
        id: "outcome:beta:2",
        project_id: "beta",
        tracker_id: "b".repeat(64),
        tracker_title: "Beta implementation tracker",
        block: 2,
        title: "Typed owner adapter",
        status: "accepted",
        evidence_revision: "d".repeat(64),
        accepted_at: null,
        observed_at: observed,
        currentness: "current",
        retained_open_work: 4,
        source: {
          identity: "tracker/beta",
          record_id: null,
          path: "docs/beta-implementation-tracker.md",
          line: 122,
          revision: "d".repeat(64),
          route: "/?inspect=outcome:beta:2",
        },
      }],
      metrics: [
        metric("active-projects", "Active projects", 2),
        metric("active-tasks", "Active tasks", 2),
        metric("active-implementations", "Active implementations", 2),
        metric("supervision-runs", "Supervision runs", 2),
        metric("unmonitored-implementations", "Unmonitored implementations", 1),
        metric("degraded-groups", "Degraded groups", 0),
        metric("orphaned-supervisors", "Orphaned supervisors", 0),
        metric("accepted-blocks", "Accepted Blocks", 8),
        metric("blocks-in-progress", "Blocks in progress", 2),
        metric("blocks-not-started", "Blocks not started", 10),
        metric("open-items", "Open issues", 1),
        metric("supervisor-checks", "Supervisor checks", 12),
        metric("semantic-conclusions", "Current conclusions", 1),
        metric("api-equivalent", "API-equivalent estimate", 3.25, true),
      ],
      source_health: [
        {
          family: "catalog",
          label: "Project catalog",
          status: "available",
          identity: "fixture/catalog",
          revision: "1".repeat(64),
          observed_at: observed,
          reason: "Available",
          coverage: { status: "complete", observed: ["catalog"], missing: [] },
        },
        {
          family: "operations",
          label: "Supervision",
          status: "available",
          identity: "fixture/operations",
          revision: "2".repeat(64),
          observed_at: observed,
          reason: "Available",
          coverage: { status: "partial", observed: ["runs"], missing: ["wake-receipts"] },
        },
        {
          family: "trackers",
          label: "Trackers",
          status: "available",
          identity: "fixture/trackers",
          revision: "3".repeat(64),
          observed_at: observed,
          reason: "Available",
          coverage: { status: "complete", observed: ["trackers"], missing: [] },
        },
        {
          family: "tasks",
          label: "Codex tasks",
          status: "partial",
          identity: "fixture/tasks",
          revision: "4".repeat(64),
          observed_at: observed,
          reason: "Later task pages were not loaded.",
          coverage: { status: "partial", observed: ["first-page"], missing: ["later-pages"] },
        },
      ],
      fingerprint: "f".repeat(64),
    },
    source: {
      kind: "factory-floor-composition",
      identity: "software-factory-dashboard/factory-floor",
      revision: "f".repeat(64),
    },
    observed_at: observed,
    fingerprint: "9".repeat(64),
    coverage: {
      status: "partial",
      observed: ["catalog", "operations", "trackers", "tasks"],
      missing: ["tasks"],
    },
    limitations: ["Operating lights never imply completion."],
    error: null,
  }
}
