import { describe, expect, it, vi } from "vitest"

import { DashboardApiError } from "@/lib/api"
import {
  fetchReport,
  fetchReportArtifactText,
  fetchMetrics,
  fetchReports,
  fetchRun,
  fetchRuns,
  metricsEnvelopeSchema,
  reportArtifactSchema,
  reportDetailEnvelopeSchema,
  reportListEnvelopeSchema,
  runDetailEnvelopeSchema,
  runListEnvelopeSchema,
  supervisionMetricsSchema,
} from "@/lib/operations-api"

const hash = (character: string) => character.repeat(64)
const revision = (character: string) => character.repeat(40)
const observedAt = "2026-08-09T11:30:00.000Z"

const owners = {
  supervision: {
    identity: "supervise-tracker-runs/scripts/supervision_log.py",
    path: "/owner/supervision_log.py",
    sha256: hash("a"),
    owning_revision: revision("1"),
  },
  weekly_report: {
    identity: "supervise-tracker-runs/scripts/weekly_report.py",
    path: "/owner/weekly_report.py",
    sha256: hash("b"),
    owning_revision: revision("2"),
  },
  terminal_report: {
    identity: "supervise-tracker-runs/scripts/terminal_report.py",
    path: "/owner/terminal_report.py",
    sha256: hash("c"),
    owning_revision: revision("3"),
  },
  factory_evolution: {
    identity: "supervise-tracker-runs/scripts/factory_evolution.py",
    path: "/owner/factory_evolution.py",
    sha256: hash("d"),
    owning_revision: revision("4"),
  },
} as const

const record = {
  record_id: "EVT-000002",
  timestamp: "2026-08-09T11:20:00+00:00",
  kind: "meta-review",
  status: "accepted",
  severity: "info",
  category: "effectiveness-review",
  summary: "Current semantic conclusion.",
} as const

const projectBinding = {
  status: "bound",
  project_id: "demo",
  evidence: [{ source_record: "POLICY-2", field: "project_root", value: "/work/demo" }],
  limitations: [],
} as const

const automation = {
  id: "watcher-demo",
  status: "available",
  name: "Demo watcher",
  kind: "heartbeat",
  owner_status: "ACTIVE",
  rrule: "RRULE:FREQ=MINUTELY;INTERVAL=20",
  target_thread_id: "watcher-thread-1",
  created_at: observedAt,
  updated_at: observedAt,
  next_scheduled_at: null,
  manifest_sha256: hash("e"),
  source_path: "/automations/watcher-demo/automation.toml",
  limitations: ["No canonical next occurrence."],
  error: null,
} as const

const topology = {
  supervisor_group_id: hash("f"),
  implementation: {
    thread_id: "target-thread-1",
    status: "unavailable",
    reason: "Codex task state begins in Block 5.",
  },
  project_binding: projectBinding,
  tracker_binding: {
    status: "unavailable",
    tracker_path: null,
    tracker_sha256: null,
    reason: "No canonical tracker association owner.",
  },
  roles: [
    {
      role: "watcher",
      label: "Routine watcher",
      thread_id: "watcher-thread-1",
      binding_status: "bound",
      task_state: { status: "unavailable", reason: "Live task state begins in Block 5." },
      automation,
      last_activity: null,
      activity_attribution: {
        status: "unavailable",
        reason: "Canonical events do not expose the emitting task.",
      },
    },
  ],
  binding_integrity: "valid",
  anomalies: [],
} as const

const light = {
  posture: "red",
  label: "Action required",
  facts: [
    {
      rule: "open-high-or-critical-incident",
      severity: "red",
      record_id: "EVT-000003",
      observed_at: "2026-08-09T11:21:00+00:00",
      detail: "Current high incident.",
      source_identity: "supervise-tracker-runs/events.jsonl",
      source_path: "/supervision/target-thread-1/events.jsonl",
      source_line: 3,
    },
  ],
  derived: true,
  completion_claim: false,
} as const

const availableSummary = {
  status: "available",
  target_thread_id: "target-thread-1",
  target_label: "Demo target",
  observed_at: observedAt,
  fingerprint: hash("0"),
  current_mission: {
    root: hash("1"),
    source_record: "direct-item-44",
    policy_sha256: hash("2"),
  },
  project_binding: projectBinding,
  event_count: 4,
  current_event_count: 3,
  predecessor_count: 1,
  lifecycle: { status: null, record: null },
  counts: {
    open_incidents: 1,
    open_decisions: 0,
    open_successor_transitions: 0,
    activities: 3,
    conclusions: 1,
    reports: { "weekly:available": 1 },
  },
  last_check: { ...record, kind: "check", status: "no-intervention" },
  latest_activity: record,
  latest_conclusion: record,
  light,
  topology,
  source: {
    identity: "supervise-tracker-runs/scripts/supervision_log.py",
    root: "/supervision/target-thread-1",
    revision: hash("a"),
    event_head_sha256: hash("3"),
    policy_head_sha256: hash("2"),
    cache_status: "miss",
  },
  coverage: {
    status: "partial",
    observed: ["event-ledger", "automations", "metrics"],
    missing: ["codex-app-server-task-state"],
  },
  limitations: ["Traffic light is derived."],
  error: null,
} as const

const unavailableSummary = {
  status: "unavailable",
  target_thread_id: "target-thread-2",
  target_label: "target-threa",
  observed_at: observedAt,
  fingerprint: null,
  current_mission: null,
  project_binding: { status: "unassigned", project_id: null, evidence: [], limitations: [] },
  event_count: null,
  current_event_count: null,
  predecessor_count: null,
  lifecycle: { status: null, record: null },
  counts: null,
  last_check: null,
  latest_activity: null,
  latest_conclusion: null,
  light: {
    posture: "red",
    label: "Action required",
    facts: [
      {
        rule: "source-integrity-failure",
        severity: "red",
        record_id: null,
        observed_at: observedAt,
        detail: "Broken hash chain.",
        source_identity: "supervise-tracker-runs/source-validation",
        source_path: null,
        source_line: null,
      },
    ],
    derived: true,
    completion_claim: false,
  },
  topology: null,
  source: null,
  coverage: { status: "unavailable", observed: [], missing: ["supervision-integrity"] },
  limitations: ["Source-local failure."],
  error: { code: "supervision_integrity_failed", message: "Broken hash chain.", retryable: false },
} as const

const metrics = {
  schema_version: 1,
  kind: "supervision-weekly-review",
  report_id: "weekly-demo",
  target_label: "Demo target",
  coverage: {
    start: "2026-08-09T11:00:00+00:00",
    end: "2026-08-09T11:20:00+00:00",
    timezone: "America/Los_Angeles",
    calendar_days: ["2026-08-09"],
    elapsed_hours: 0.33,
    partial_week: true,
  },
  source: {
    source_root: hash("4"),
    event_count: 3,
    first_record_id: "EVT-000001",
    last_record_id: "EVT-000003",
    policy_record_count: 1,
    policy_sha256_at_generation: hash("2"),
    projection_inventory: {
      incident_reports: { count: 1, names_sha256: hash("5") },
      review_reports: { count: 1, names_sha256: hash("6") },
      note: "Derived projections only.",
    },
  },
  headline: {
    recorded_events: 3,
    changed_state_routes: 1,
    incidents_opened: 1,
    incidents_terminal: 0,
    incidents_open_at_end: 1,
    incidents_open_high_or_critical: 1,
    corrections_issued: 0,
    max_samples: 0,
    roundups: 0,
    blocks_observed: 1,
    tooling_change_records: 0,
  },
  rates: {
    incidents_per_100_changed_state_routes: 100,
    terminal_share_of_opened_percent: 0,
    incident_detection_to_terminal_median_hours: null,
    incident_detection_to_terminal_p90_hours: null,
    denominator_note: "Exact changed-state routes.",
  },
  availability: {
    report_period_hours: 0.33,
    observed_event_span_hours: 0.33,
    core_heartbeats_scheduled_active_hours: 0.33,
    core_heartbeats_explicitly_paused_hours: 0,
    core_heartbeats_scheduled_active_percent: 100,
    explicit_pause_intervals: [],
    recorded_target_read_successes: 1,
    recorded_target_read_failures: 0,
    recorded_target_read_availability_percent: 100,
    continuous_process_uptime_measured: false,
    interpretation: "Recorded reads only.",
  },
  resource_estimate: {
    measurement_posture: "estimated-from-content-minimized-records",
    actual_provider_tokens_available: false,
    actual_provider_cost_available: false,
    pricing_profile_id: "pricing-v1",
    pricing_profile_sha256: hash("7"),
    currency: "USD",
    method: "Versioned estimate.",
    models: [],
    totals: {
      recorded_model_attributed_events: 0,
      excluded_unpriced_or_unattributed_records: 3,
      estimated_input_tokens_base: 0,
      estimated_output_tokens_base: 0,
      estimated_tokens_base: 0,
      estimated_tokens_low: 0,
      estimated_tokens_high: 0,
      projected_cost_usd_low: 0,
      projected_cost_usd_base: 0,
      projected_cost_usd_high: 0,
    },
    daily: [],
    assumptions: {
      characters_per_token: 4,
      low_multiplier: 0.6,
      high_multiplier: 1.6,
      reasoning_output_multipliers: { unspecified: 1 },
      models: {},
    },
    disclaimer: "Not billing telemetry.",
  },
  counts: {
    by_kind: { check: 1, incident: 1, "meta-review": 1 },
    by_status: { "no-intervention": 1, detected: 1, accepted: 1 },
    by_severity: { info: 2, high: 1 },
    by_category: { "changed-state-review": 1, integrity: 1, effectiveness: 1 },
    by_model_reasoning: { "unspecified / unspecified": 3 },
  },
  daily_activity: [
    {
      date: "2026-08-09",
      mechanical: 1,
      review: 1,
      routing: 0,
      intervention: 1,
      communication: 0,
      maintenance: 0,
      other: 0,
    },
  ],
  daily_incidents: [{ date: "2026-08-09", opened: 1, terminal: 0 }],
  monitoring_roles: {
    configured_thread_count: 2,
    core_role_count: 2,
    support_role_count: 0,
    roles: [
      {
        role: "Routine watcher",
        purpose: "Mechanical checks.",
        configured: true,
        recorded_action_count: 1,
        activity_label: "watcher checks",
      },
    ],
    interpretation: "Recorded actions are lower bounds.",
  },
  task_activity: [{ task: "Watcher checks", recorded_count: 1, cadence: "Every 20 minutes." }],
  incidents: {
    opened_ids: ["INC-1"],
    terminal_ids: [],
    open_at_end_ids: ["INC-1"],
    terminal_statuses: {},
    effectiveness_statuses: {},
    false_positive_terminal_count: 0,
    sampled_false_negative_mentions: 0,
  },
  limitations: ["Recorded activity is a lower bound."],
  blocks: [
    {
      block: 1,
      first_seen: "2026-08-09T11:00:00+00:00",
      last_seen: "2026-08-09T11:20:00+00:00",
      event_count: 3,
      checkpoint_count: 1,
    },
  ],
} as const

const reportMetricSummary = {
  ...metrics,
  line_items: [
    {
      active_block: "1",
      category: "integrity",
      kind: "incident",
      record_id: "EVT-000003",
      severity: "high",
      status: "detected",
      summary: "Source integrity failure detected.",
      timestamp: "2026-08-09T11:20:00+00:00",
    },
  ],
  tooling_changes: [
    {
      category: "supervision-maintenance",
      record_id: "EVT-000002",
      status: "configured",
      summary: "Maintained watcher policy updated.",
      timestamp: "2026-08-09T11:10:00+00:00",
    },
  ],
} as const

const report = {
  id: "weekly-demo",
  target_thread_id: "target-thread-1",
  family: "weekly",
  stage: "verified",
  status: "available",
  source_root: hash("4"),
  manifest_root: hash("8"),
  disposition: "effective",
  coverage: metrics.coverage,
  review_summary: { headline: "Supervisor effective.", assessment: "Evidence-bound." },
  verification: {
    valid: true,
    report_id: "weekly-demo",
    source_root: hash("4"),
    manifest_root: hash("8"),
    page_count: 8,
    pdf_path: "/reports/weekly-demo/report.pdf",
    report_sha256: hash("9"),
    review_sha256: hash("a"),
    pdf_sha256: hash("b"),
  },
  members: [
    {
      name: "report.pdf",
      path: "/reports/weekly-demo/report.pdf",
      media_type: "application/pdf",
      bytes: 2048,
      sha256: hash("b"),
      read_only: true,
    },
  ],
  limitations: ["Report is not completion authority."],
  error: null,
} as const

const projectedEvent = {
  record_id: "EVT-000002",
  timestamp: "2026-08-09T11:20:00+00:00",
  kind: "meta-review",
  status: "accepted",
  severity: "info",
  category: "effectiveness-review",
  active_block: "1",
  checkpoint: "candidate-a",
  state_fingerprint: "state-1",
  incident_id: null,
  decision_id: null,
  transition_id: null,
  phase: null,
  classification: null,
  safe_frontier: null,
  outcome: null,
  model: "gpt-5.6-sol",
  reasoning: "max",
  summary: "Current semantic conclusion.",
  action: null,
  resolution: null,
  notice_disposition: null,
  resolution_owner: null,
  user_action_required: null,
  policy_sha256: hash("2"),
  record_sha256: hash("3"),
  evidence: ["candidate-a"],
  mission_root: hash("1"),
  actor: {
    status: "unavailable",
    role: null,
    thread_id: null,
    reason: "Canonical events do not expose the emitting task.",
  },
  source: { path: "/supervision/target-thread-1/events.jsonl", line: 2, read_only: true },
} as const

const detail = {
  ...availableSummary,
  policy: {
    version: 2,
    sha256: hash("2"),
    schedule: { routine_minutes: 20 },
    reports: {},
    source_path: "/supervision/target-thread-1/policy.json",
    read_only: true,
  },
  policy_history: [
    {
      record_id: "POLICY-2",
      timestamp: "2026-08-09T11:10:00+00:00",
      kind: "policy-mission-successor",
      policy_version: 2,
      policy_sha256: hash("2"),
      mission_root: hash("1"),
    },
  ],
  mission_segments: [
    {
      mission_root: hash("1"),
      mission_source_record: "direct-item-44",
      posture: "current",
      policy_sha256s: [hash("2")],
      first_recorded_at: "2026-08-09T11:10:00+00:00",
      last_recorded_at: "2026-08-09T11:20:00+00:00",
      event_count: 3,
      incident_count: 1,
      open_incident_count: 1,
      conclusion_count: 1,
      terminal_record: null,
      superseded_by: null,
    },
  ],
  incidents: [{ incident_id: "INC-1", open: true, head: record }],
  decisions: [],
  successor_transitions: [],
  activities: [projectedEvent],
  activities_truncated: false,
  conclusions: [projectedEvent],
  conclusions_truncated: false,
  timeline: [projectedEvent],
  timeline_truncated: false,
  operating_history: [{ from: "neutral", to: "red", trigger: "open-high", record }],
  reports: [report],
  metrics: {
    status: "available",
    definition_owner: "supervise-tracker-runs/scripts/weekly_report.py",
    metrics,
    error: null,
  },
} as const

const source = {
  kind: "operations-projection",
  identity: "software-factory-dashboard/runs",
  revision: hash("c"),
} as const

const coverage = {
  status: "partial",
  observed: ["supervision", "automations", "reports", "metrics"],
  missing: ["codex-app-server-task-state"],
} as const

const runListEnvelope = {
  data: {
    catalog_fingerprint: hash("d"),
    recovered_from_previous: false,
    owners,
    runs: [availableSummary, unavailableSummary],
    attention: [
      {
        rank: 1,
        rule: "open-high-or-critical-incident",
        severity: "red",
        target_thread_id: "target-thread-1",
        source_record_id: "EVT-000003",
        source_identity: "supervise-tracker-runs/events.jsonl",
        source_path: "/supervision/target-thread-1/events.jsonl",
        source_line: 3,
        observed_at: "2026-08-09T11:21:00+00:00",
        detail: "Current high incident.",
        detail_route: "/runs/target-thread-1",
      },
    ],
    orphan_automations: [],
    unmonitored_projects: [],
  },
  source,
  observed_at: observedAt,
  fingerprint: hash("e"),
  coverage,
  limitations: ["Source families remain isolated."],
  error: null,
} as const

const runDetailEnvelope = {
  ...runListEnvelope,
  data: {
    catalog_fingerprint: hash("d"),
    recovered_from_previous: false,
    owners,
    run: detail,
  },
} as const

const reportEnvelope = {
  ...runListEnvelope,
  data: {
    catalog_fingerprint: hash("d"),
    recovered_from_previous: false,
    owners,
    reports: [report],
  },
} as const

const reportDetailEnvelope = {
  ...reportEnvelope,
  data: {
    owners,
    report: {
      ...report,
      metric_summary: reportMetricSummary,
      artifacts: [
        {
          ...report.members[0],
          previewable: true,
          preview_url: "/api/v1/reports/target-thread-1/weekly/weekly-demo/artifacts/report.pdf",
          download_url: "/api/v1/reports/target-thread-1/weekly/weekly-demo/artifacts/report.pdf?download=true",
        },
      ],
    },
  },
} as const

const metricsEnvelope = {
  ...runListEnvelope,
  data: {
    catalog_fingerprint: hash("d"),
    recovered_from_previous: false,
    owners,
    aggregate: {
      status: "available",
      definition: "Active missions only.",
      run_count: 2,
      available_run_count: 1,
      historical_segment_count: 1,
      contract_count: 1,
      contracts: [{
        schema_version: metrics.schema_version,
        kind: metrics.kind,
        coverage: metrics.coverage,
        denominator_note: metrics.rates.denominator_note,
        target_thread_ids: ["target-thread-1"],
        run_count: 1,
      }],
      headline: { recorded_events: 3 },
      api_equivalent_estimate: {
        label: "API-equivalent estimate",
        actual_billing_data: false,
        coverage_run_count: 1,
        totals: { projected_cost_usd_base: 0 },
      },
      limitations: ["No synthetic cross-run percentiles."],
    },
    factory_history: {
      definition: "Bounded current-mission supervision history.",
      current_postures: { red: 2 },
      supervisor_group_count: 1,
      bound_project_count: 1,
      unmonitored_project_count: 0,
      availability: {
        status: "available",
        scheduled_active_hours: 1,
        explicitly_paused_hours: 0,
        recorded_target_read_successes: 1,
        recorded_target_read_failures: 0,
        continuous_uptime_measured: false,
      },
      conclusions: {
        by_kind: { "meta-review": 1 },
        by_category: { "effectiveness-review": 1 },
      },
      posture_transition_count: 1,
      posture_transitions: [{
        target_thread_id: "target-thread-1",
        target_label: "Demo target",
        project_id: "demo",
        from: "neutral",
        to: "red",
        trigger: "open-high",
        record,
      }],
      posture_transitions_truncated: false,
      unsupported: ["Task concurrency history is unavailable."],
    },
    per_run: [
      {
        target_thread_id: "target-thread-1",
        target_label: "Demo target",
        supervisor_group_id: hash("8"),
        project_binding: projectBinding,
        observed_at: observedAt,
        current_mission_root: hash("1"),
        lifecycle: { status: null, record: null },
        light,
        operating_history: [{ from: "neutral", to: "red", trigger: "open-high", record }],
        conclusion_counts: {
          by_kind: { "meta-review": 1 },
          by_category: { "effectiveness-review": 1 },
        },
        report_counts: { "weekly:available": 1 },
        status: "available",
        cost_label: "API-equivalent estimate",
        metrics,
        error: null,
      },
      {
        target_thread_id: "target-thread-2",
        target_label: "Unavailable target",
        supervisor_group_id: null,
        project_binding: { status: "unassigned", project_id: null, evidence: [], limitations: [] },
        observed_at: observedAt,
        current_mission_root: null,
        lifecycle: { status: null, record: null },
        light,
        operating_history: [],
        conclusion_counts: { by_kind: {}, by_category: {} },
        report_counts: {},
        status: "unavailable",
        cost_label: "API-equivalent estimate",
        metrics: null,
        error: {
          code: "supervision_integrity_failed",
          message: "Broken hash chain.",
          retryable: false,
        },
      },
    ],
  },
} as const

const errorEnvelope = {
  data: null,
  source: { kind: "runtime", identity: "software-factory-dashboard/http", revision: "0.1.0" },
  observed_at: observedAt,
  fingerprint: hash("f"),
  coverage: { status: "partial", observed: ["runtime"], missing: [] },
  limitations: [],
  error: { code: "run_not_found", message: "Run was not found.", retryable: false },
} as const

describe("operations API contracts", () => {
  it("keeps active, predecessor, unavailable, action, and conclusion truth distinct", () => {
    const listed = runListEnvelopeSchema.parse(runListEnvelope)
    const parsedDetail = runDetailEnvelopeSchema.parse(runDetailEnvelope)

    expect(listed.data.runs.map((run) => run.status)).toEqual(["available", "unavailable"])
    expect(parsedDetail.data.run.current_event_count).toBe(3)
    expect(parsedDetail.data.run.predecessor_count).toBe(1)
    expect(parsedDetail.data.run.activities[0].kind).toBe("meta-review")
    expect(parsedDetail.data.run.conclusions[0].kind).toBe("meta-review")
    expect(parsedDetail.data.run.light).toMatchObject({ posture: "red", completion_claim: false })
  })

  it("validates report manifests and API-equivalent estimate labels without widening", () => {
    expect(reportArtifactSchema.parse(report).verification).toMatchObject({ valid: true })
    expect(reportArtifactSchema.parse({
      ...report,
      id: "terminal-demo",
      family: "terminal",
      verification: {
        valid: true,
        report_set_id: "terminal-demo",
        source_root: hash("4"),
        state_fingerprint: "state-1",
        completion_record_id: "EVT-10",
        lifecycle_record_id: "EVT-11",
        manifest_root: hash("8"),
        delta_pdf_path: "/reports/terminal-demo/delta.pdf",
        full_pdf_path: "/reports/terminal-demo/full.pdf",
        delta_pdf_sha256: hash("c"),
        full_pdf_sha256: hash("d"),
        delta_page_count: 2,
        full_page_count: 4,
      },
    }).family).toBe("terminal")
    expect(reportArtifactSchema.parse({
      ...report,
      id: "evolution-demo",
      family: "factory-evolution",
      stage: "evaluated",
      verification: {
        action: "verify",
        evolution_id: "evolution-demo",
        stage: "evaluated",
        packet_id: "packet-1",
        packet_root: hash("1"),
        review_id: "review-1",
        review_root: hash("2"),
        evaluation_id: "evaluation-1",
        evaluation_root: hash("3"),
        disposition: "retain",
      },
    }).family).toBe("factory-evolution")
    expect(reportListEnvelopeSchema.parse(reportEnvelope).data.reports).toHaveLength(1)
    expect(reportDetailEnvelopeSchema.parse(reportDetailEnvelope).data.report.artifacts[0]).toMatchObject({
      previewable: true,
    })
    const parsedMetrics = metricsEnvelopeSchema.parse(metricsEnvelope)
    expect(parsedMetrics.data.aggregate.status).toBe("available")
    expect(parsedMetrics.data.aggregate.contracts).toHaveLength(1)
    expect(parsedMetrics.data.aggregate.api_equivalent_estimate).toMatchObject({
      label: "API-equivalent estimate",
      actual_billing_data: false,
    })
    expect(supervisionMetricsSchema.parse(metrics).rates).toMatchObject({
      incident_detection_to_terminal_p90_hours: null,
    })
    expect(() => runListEnvelopeSchema.parse({ ...runListEnvelope, canonical_light: "green" })).toThrow()
  })

  it("uses bounded read routes, preserves aborts, and parses structured failures", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => runListEnvelope })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => runDetailEnvelope })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => reportEnvelope })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => metricsEnvelope })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => reportDetailEnvelope })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ "Content-Type": "text/markdown; charset=utf-8" }),
        text: async () => "# Exact report",
      })
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => errorEnvelope })
    vi.stubGlobal("fetch", fetchMock)
    const controller = new AbortController()

    await fetchRuns(controller.signal)
    await fetchRun("target-thread-1", controller.signal)
    await fetchReports(controller.signal)
    await fetchMetrics(controller.signal)
    await fetchReport("target-thread-1", "weekly", "weekly-demo", controller.signal)
    await expect(
      fetchReportArtifactText(
        "/api/v1/reports/target-thread-1/weekly/weekly-demo/artifacts/report.md",
        controller.signal,
      ),
    ).resolves.toBe("# Exact report")
    await expect(fetchRun("missing-target-1")).rejects.toBeInstanceOf(DashboardApiError)
    await expect(fetchRun("../escaped")).rejects.toThrow("invalid")

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/runs/target-thread-1",
      expect.objectContaining({ signal: controller.signal }),
    )
    expect(fetchMock).toHaveBeenCalledTimes(7)
  })
})
