import { z } from "zod"

import {
  apiErrorEnvelopeSchema,
  coverageSchema,
  DashboardApiError,
  sourceSchema,
} from "@/lib/api"

const nonnegativeInteger = z.number().int().nonnegative()
const fingerprintSchema = z.string().regex(/^[0-9a-f]{64}$/)
const gitRevisionSchema = z.string().regex(/^[0-9a-f]{40,64}$/)
const nullableString = z.string().nullable()
const countMapSchema = z.record(z.string(), nonnegativeInteger)
const numberMapSchema = z.record(z.string(), z.number())
const jsonMapSchema = z.record(z.string(), z.json())

const projectionErrorSchema = z
  .object({
    code: z.string().min(1),
    message: z.string().min(1),
    retryable: z.boolean(),
  })
  .strict()

const recordRefSchema = z
  .object({
    record_id: nullableString,
    timestamp: nullableString,
    kind: nullableString,
    status: nullableString,
    severity: nullableString,
    category: nullableString,
    summary: nullableString,
  })
  .strict()

const recordSourceSchema = z
  .object({
    path: z.string().min(1),
    line: z.number().int().positive(),
    read_only: z.literal(true),
  })
  .strict()

const unavailableActorSchema = z
  .object({
    status: z.literal("unavailable"),
    role: z.null(),
    thread_id: z.null(),
    reason: z.string().min(1),
  })
  .strict()

export const supervisionEventSchema = z
  .object({
    record_id: nullableString,
    timestamp: nullableString,
    kind: nullableString,
    status: nullableString,
    severity: nullableString,
    category: nullableString,
    active_block: nullableString,
    checkpoint: nullableString,
    state_fingerprint: nullableString,
    incident_id: nullableString,
    decision_id: nullableString,
    transition_id: nullableString,
    phase: nullableString,
    classification: nullableString,
    safe_frontier: nullableString,
    outcome: nullableString,
    model: nullableString,
    reasoning: nullableString,
    summary: nullableString,
    action: nullableString,
    resolution: nullableString,
    notice_disposition: nullableString,
    resolution_owner: nullableString,
    user_action_required: nullableString,
    policy_sha256: nullableString,
    record_sha256: nullableString,
    evidence: z.array(z.string()),
    mission_root: z.string().min(1),
    actor: unavailableActorSchema,
    source: recordSourceSchema,
  })
  .strict()

const projectBindingEvidenceSchema = z
  .object({
    source_record: z.string(),
    field: z.string(),
    value: z.string(),
  })
  .strict()

const projectBindingSchema = z
  .object({
    status: z.enum(["bound", "ambiguous", "unassigned"]),
    project_id: nullableString,
    evidence: z.array(projectBindingEvidenceSchema),
    limitations: z.array(z.string()),
  })
  .strict()

const automationSchema = z
  .object({
    id: z.string().min(1),
    status: z.enum(["available", "unavailable"]),
    name: nullableString,
    kind: nullableString,
    owner_status: nullableString,
    rrule: nullableString,
    target_thread_id: nullableString,
    created_at: nullableString,
    updated_at: nullableString,
    next_scheduled_at: z.null(),
    manifest_sha256: fingerprintSchema.nullable(),
    protected_sha256: fingerprintSchema.nullable().optional(),
    source_path: z.string().min(1),
    limitations: z.array(z.string()),
    error: projectionErrorSchema.nullable(),
    binding_status: z.literal("unreferenced").optional(),
  })
  .strict()

const roleSchema = z
  .object({
    role: z.string().min(1),
    label: z.string().min(1),
    thread_id: nullableString,
    binding_status: z.enum([
      "bound",
      "missing-thread",
      "duplicate-thread",
      "duplicate-automation",
      "missing-automation",
      "automation-unavailable",
      "automation-target-mismatch",
    ]),
    task_state: z
      .object({
        status: z.literal("unavailable"),
        reason: z.string().min(1),
      })
      .strict(),
    automation: automationSchema.nullable(),
    last_activity: recordRefSchema.nullable(),
    activity_attribution: z
      .object({
        status: z.literal("unavailable"),
        reason: z.string().min(1),
      })
      .strict(),
  })
  .strict()

const topologySchema = z
  .object({
    supervisor_group_id: fingerprintSchema,
    implementation: z
      .object({
        thread_id: z.string().min(1),
        status: z.literal("unavailable"),
        reason: z.string().min(1),
      })
      .strict(),
    project_binding: projectBindingSchema,
    tracker_binding: z
      .object({
        status: z.literal("unavailable"),
        tracker_path: z.null(),
        tracker_sha256: z.null(),
        reason: z.string().min(1),
      })
      .strict(),
    roles: z.array(roleSchema),
    binding_integrity: z.enum(["valid", "degraded"]),
    anomalies: z.array(z.string()),
  })
  .strict()

const lightSchema = z
  .object({
    posture: z.enum(["red", "amber", "green", "neutral"]),
    label: z.string().min(1),
    facts: z.array(
      z
        .object({
          rule: z.string().min(1),
          severity: z.enum(["red", "amber"]),
          record_id: nullableString,
          observed_at: z.string().min(1),
          detail: z.string().min(1),
          source_identity: z.string().min(1),
          source_path: nullableString,
          source_line: z.number().int().positive().nullable(),
        })
        .strict(),
    ),
    derived: z.literal(true),
    completion_claim: z.literal(false),
  })
  .strict()

const currentMissionSchema = z
  .object({
    root: fingerprintSchema.nullable(),
    source_record: nullableString,
    policy_sha256: fingerprintSchema,
  })
  .strict()

const nestedCoverageSchema = z
  .object({
    status: z.enum(["complete", "partial", "unavailable"]),
    observed: z.array(z.string()),
    missing: z.array(z.string()),
  })
  .strict()

const runSourceSchema = z
  .object({
    identity: z.literal("supervise-tracker-runs/scripts/supervision_log.py"),
    root: z.string().min(1),
    revision: fingerprintSchema,
    event_head_sha256: fingerprintSchema.nullable(),
    policy_head_sha256: fingerprintSchema,
    cache_status: z.enum(["hit", "miss"]),
  })
  .strict()

const runCountsSchema = z
  .object({
    open_incidents: nonnegativeInteger,
    open_decisions: nonnegativeInteger,
    open_successor_transitions: nonnegativeInteger,
    activities: nonnegativeInteger,
    conclusions: nonnegativeInteger,
    reports: countMapSchema,
  })
  .strict()

export const runSummarySchema = z
  .object({
    status: z.enum(["available", "unavailable"]),
    target_thread_id: z.string().min(1),
    target_label: z.string().min(1),
    observed_at: z.string().min(1),
    fingerprint: fingerprintSchema.nullable(),
    current_mission: currentMissionSchema.nullable(),
    project_binding: projectBindingSchema,
    event_count: nonnegativeInteger.nullable(),
    current_event_count: nonnegativeInteger.nullable(),
    predecessor_count: nonnegativeInteger.nullable(),
    lifecycle: z
      .object({ status: nullableString, record: recordRefSchema.nullable() })
      .strict(),
    counts: runCountsSchema.nullable(),
    last_check: recordRefSchema.nullable(),
    latest_activity: recordRefSchema.nullable(),
    latest_conclusion: recordRefSchema.nullable(),
    light: lightSchema,
    topology: topologySchema.nullable(),
    source: runSourceSchema.nullable(),
    coverage: nestedCoverageSchema,
    limitations: z.array(z.string()),
    error: projectionErrorSchema.nullable(),
  })
  .strict()

const policySchema = z
  .object({
    version: nonnegativeInteger,
    sha256: fingerprintSchema,
    schedule: jsonMapSchema,
    reports: jsonMapSchema,
    adjustable: z
      .object({
        routine_minutes: nonnegativeInteger.nullable(),
        meta_review_hours: nonnegativeInteger.nullable(),
        max_sample_denominator: nonnegativeInteger.nullable(),
        cooldown_minutes: nonnegativeInteger.nullable(),
        max_escalations_per_hour: nonnegativeInteger.nullable(),
        gmail_quiet_minutes: nonnegativeInteger.nullable(),
        gmail_active_minutes: nonnegativeInteger.nullable(),
        gmail_active_window_minutes: nonnegativeInteger.nullable(),
        skill_maintenance_mode: nullableString,
      })
      .strict(),
    adjustment_contract: z
      .object({
        fields: z.array(
          z
            .object({
              field: z.enum([
                "routine_minutes",
                "meta_review_hours",
                "max_sample_denominator",
                "cooldown_minutes",
                "max_escalations_per_hour",
                "gmail_quiet_minutes",
                "gmail_active_minutes",
                "gmail_active_window_minutes",
                "skill_maintenance_mode",
              ]),
              kind: z.enum(["integer", "enum"]),
              minimum: nonnegativeInteger.nullable(),
              maximum: nonnegativeInteger.nullable(),
              automation_role: z
                .enum(["watcher", "reviewer", "gmail_gate"])
                .nullable(),
            })
            .strict(),
        ).length(9),
        skill_maintenance_modes: z.array(z.enum([
          "apply-allowlisted-skill-maintenance-with-review",
          "apply-supervision-maintenance",
          "propose-only",
        ])).length(3),
      })
      .strict(),
    automation_reconciliation: z.array(
      z
        .object({
          field: z.enum([
            "routine_minutes",
            "meta_review_hours",
            "gmail_cadence",
            "roundup_schedule",
            "weekly_report_schedule",
          ]),
          role: z.enum([
            "watcher",
            "reviewer",
            "gmail_gate",
            "roundup_writer",
            "weekly_report",
          ]),
          automation_id: nullableString,
          actual_automation_id: nullableString.optional(),
          expected_rrule: nullableString,
          actual_rrule: nullableString,
          owner_status: nullableString,
          target_thread_id: nullableString,
          actual_target_thread_id: nullableString.optional(),
          purpose: nullableString.optional(),
          timezone: nullableString.optional(),
          actual_timezone: nullableString,
          duplicate_coverage: z.enum(["exact", "unavailable"]),
          active_target_owner_ids: z.array(z.string().min(1)),
          mode: z.enum(["active", "quiet"]).nullable(),
          state: z.enum(["reconciled", "partial", "unavailable"]),
          repairable: z.boolean().optional(),
          reason: z.string().min(1),
        })
        .strict(),
    ),
    source_path: z.string().min(1),
    read_only: z.literal(true),
  })
  .strict()

const policyHistorySchema = z
  .object({
    record_id: z.string().min(1),
    timestamp: z.string().min(1),
    kind: z.string().min(1),
    policy_version: nonnegativeInteger,
    policy_sha256: fingerprintSchema,
    mission_root: z.union([fingerprintSchema, z.literal("unbound")]),
  })
  .strict()

const missionSegmentSchema = z
  .object({
    mission_root: z.union([fingerprintSchema, z.literal("unbound")]),
    mission_source_record: nullableString,
    posture: z.enum(["current", "predecessor", "unbound-history"]),
    policy_sha256s: z.array(fingerprintSchema),
    first_recorded_at: nullableString,
    last_recorded_at: nullableString,
    event_count: nonnegativeInteger,
    incident_count: nonnegativeInteger,
    open_incident_count: nonnegativeInteger,
    conclusion_count: nonnegativeInteger,
    terminal_record: recordRefSchema.nullable(),
    superseded_by: z.union([fingerprintSchema, z.literal("unbound")]).nullable(),
  })
  .strict()

const incidentSchema = z
  .object({
    incident_id: z.string().min(1),
    open: z.boolean(),
    head: recordRefSchema,
  })
  .strict()

const decisionSchema = z
  .object({
    decision_id: z.string().min(1),
    open: z.boolean(),
    head: recordRefSchema,
    phase: nullableString,
    safe_frontier: nullableString,
  })
  .strict()

const successorTransitionSchema = z
  .object({
    transition_id: z.string().min(1),
    open: z.boolean(),
    head: recordRefSchema,
    phase: nullableString,
    tracker_sha256: fingerprintSchema.nullable(),
    tracker_source_record: nullableString,
    requested_block_range: nullableString,
    first_eligible_block: nullableString,
    source_mission_root: fingerprintSchema.nullable(),
    governing_authority_source_class: nullableString,
    governing_authority_source_record: nullableString,
    successor_thread_id: nullableString,
    successor_mission_root: fingerprintSchema.nullable(),
    successor_group_id: nullableString,
    handoff_record: nullableString,
    acknowledgement_record: nullableString,
    started_block: nullableString,
    state_fingerprint: nullableString,
  })
  .strict()

const operatingTransitionSchema = z
  .object({
    from: z.enum(["red", "amber", "green", "neutral"]),
    to: z.enum(["red", "amber", "green", "neutral"]),
    trigger: z.string().min(1),
    record: recordRefSchema,
  })
  .strict()

const metricHistoryTransitionSchema = operatingTransitionSchema
  .extend({
    target_thread_id: z.string().min(1),
    target_label: z.string().min(1),
    project_id: nullableString,
  })
  .strict()

const factoryHistorySchema = z
  .object({
    definition: z.string().min(1),
    current_postures: countMapSchema,
    supervisor_group_count: nonnegativeInteger,
    bound_project_count: nonnegativeInteger,
    unmonitored_project_count: nonnegativeInteger,
    availability: z
      .object({
        status: z.enum(["available", "incompatible", "unavailable"]),
        scheduled_active_hours: z.number().nonnegative().nullable(),
        explicitly_paused_hours: z.number().nonnegative().nullable(),
        recorded_target_read_successes: nonnegativeInteger.nullable(),
        recorded_target_read_failures: nonnegativeInteger.nullable(),
        continuous_uptime_measured: z.literal(false),
      })
      .strict(),
    conclusions: z
      .object({ by_kind: countMapSchema, by_category: countMapSchema })
      .strict(),
    posture_transition_count: nonnegativeInteger,
    posture_transitions: z.array(metricHistoryTransitionSchema),
    posture_transitions_truncated: z.boolean(),
    unsupported: z.array(z.string().min(1)),
  })
  .strict()

const metricCoverageSchema = z
  .object({
    start: z.string().min(1),
    end: z.string().min(1),
    timezone: z.string().min(1),
    calendar_days: z.array(z.string()),
    elapsed_hours: z.number().nonnegative(),
    partial_week: z.boolean(),
  })
  .strict()

const projectionInventorySchema = z
  .object({
    incident_reports: z
      .object({ count: nonnegativeInteger, names_sha256: fingerprintSchema })
      .strict(),
    review_reports: z
      .object({ count: nonnegativeInteger, names_sha256: fingerprintSchema })
      .strict(),
    note: z.string().min(1),
  })
  .strict()

const resourceTotalsSchema = z
  .object({
    recorded_model_attributed_events: nonnegativeInteger,
    excluded_unpriced_or_unattributed_records: nonnegativeInteger,
    estimated_input_tokens_base: nonnegativeInteger,
    estimated_output_tokens_base: nonnegativeInteger,
    estimated_tokens_base: nonnegativeInteger,
    estimated_tokens_low: nonnegativeInteger,
    estimated_tokens_high: nonnegativeInteger,
    projected_cost_usd_low: z.number().nonnegative(),
    projected_cost_usd_base: z.number().nonnegative(),
    projected_cost_usd_high: z.number().nonnegative(),
  })
  .strict()

const pricingAssumptionSchema = z
  .object({
    api_price_assumption: z.string().min(1),
    input_usd_per_million_tokens: z.number().nonnegative(),
    output_usd_per_million_tokens: z.number().nonnegative(),
    per_record_input_overhead_tokens: nonnegativeInteger,
    per_record_output_floor_tokens: nonnegativeInteger,
    source_url: z.string().url(),
  })
  .strict()

const resourceEstimateSchema = z
  .object({
    measurement_posture: z.literal("estimated-from-content-minimized-records"),
    actual_provider_tokens_available: z.literal(false),
    actual_provider_cost_available: z.literal(false),
    pricing_profile_id: z.string().min(1),
    pricing_profile_sha256: fingerprintSchema,
    currency: z.string().min(1),
    method: z.string().min(1),
    models: z.array(
      z
        .object({
          model: z.string().min(1),
          recorded_model_attributed_events: nonnegativeInteger,
          reasoning_event_counts: countMapSchema,
          estimated_input_tokens_base: nonnegativeInteger,
          estimated_output_tokens_base: nonnegativeInteger,
          projected_cost_usd_base: z.number().nonnegative(),
          api_price_assumption: z.string().min(1),
          input_usd_per_million_tokens: z.number().nonnegative(),
          output_usd_per_million_tokens: z.number().nonnegative(),
          source_url: z.string().url(),
          estimated_tokens_base: nonnegativeInteger,
          estimated_tokens_low: nonnegativeInteger,
          estimated_tokens_high: nonnegativeInteger,
          projected_cost_usd_low: z.number().nonnegative(),
          projected_cost_usd_high: z.number().nonnegative(),
        })
        .strict(),
    ),
    totals: resourceTotalsSchema,
    daily: z.array(
      z
        .object({
          date: z.string().min(1),
          estimated_tokens_base: nonnegativeInteger,
          projected_cost_usd_base: z.number().nonnegative(),
        })
        .strict(),
    ),
    assumptions: z
      .object({
        characters_per_token: z.number().positive(),
        low_multiplier: z.number().positive(),
        high_multiplier: z.number().positive(),
        reasoning_output_multipliers: numberMapSchema,
        models: z.record(z.string(), pricingAssumptionSchema),
      })
      .strict(),
    disclaimer: z.string().min(1),
  })
  .strict()

export const supervisionMetricsSchema = z
  .object({
    schema_version: nonnegativeInteger,
    kind: z.literal("supervision-weekly-review"),
    report_id: z.string().min(1),
    target_label: z.string().min(1),
    coverage: metricCoverageSchema,
    source: z
      .object({
        source_root: fingerprintSchema,
        event_count: nonnegativeInteger,
        first_record_id: nullableString,
        last_record_id: nullableString,
        policy_record_count: nonnegativeInteger,
        policy_sha256_at_generation: fingerprintSchema,
        projection_inventory: projectionInventorySchema,
      })
      .strict(),
    headline: z
      .object({
        recorded_events: nonnegativeInteger,
        changed_state_routes: nonnegativeInteger,
        incidents_opened: nonnegativeInteger,
        incidents_terminal: nonnegativeInteger,
        incidents_open_at_end: nonnegativeInteger,
        incidents_open_high_or_critical: nonnegativeInteger,
        corrections_issued: nonnegativeInteger,
        max_samples: nonnegativeInteger,
        roundups: nonnegativeInteger,
        blocks_observed: nonnegativeInteger,
        tooling_change_records: nonnegativeInteger,
      })
      .strict(),
    rates: z
      .object({
        incidents_per_100_changed_state_routes: z.number().nullable(),
        terminal_share_of_opened_percent: z.number().nullable(),
        incident_detection_to_terminal_median_hours: z.number().nullable(),
        incident_detection_to_terminal_p90_hours: z.number().nullable(),
        denominator_note: z.string().min(1),
      })
      .strict(),
    availability: z
      .object({
        report_period_hours: z.number().nonnegative(),
        observed_event_span_hours: z.number().nonnegative(),
        core_heartbeats_scheduled_active_hours: z.number().nonnegative(),
        core_heartbeats_explicitly_paused_hours: z.number().nonnegative(),
        core_heartbeats_scheduled_active_percent: z.number().nonnegative(),
        explicit_pause_intervals: z.array(
          z
            .object({
              start: z.string().min(1),
              end: z.string().min(1),
              hours: z.number().nonnegative(),
              pause_record_id: nullableString,
              resume_record_id: nullableString,
            })
            .strict(),
        ),
        recorded_target_read_successes: nonnegativeInteger,
        recorded_target_read_failures: nonnegativeInteger,
        recorded_target_read_availability_percent: z.number().nullable(),
        continuous_process_uptime_measured: z.literal(false),
        interpretation: z.string().min(1),
      })
      .strict(),
    resource_estimate: resourceEstimateSchema,
    counts: z
      .object({
        by_kind: countMapSchema,
        by_status: countMapSchema,
        by_severity: countMapSchema,
        by_category: countMapSchema,
        by_model_reasoning: countMapSchema,
      })
      .strict(),
    daily_activity: z.array(
      z
        .object({
          date: z.string().min(1),
          mechanical: nonnegativeInteger,
          review: nonnegativeInteger,
          routing: nonnegativeInteger,
          intervention: nonnegativeInteger,
          communication: nonnegativeInteger,
          maintenance: nonnegativeInteger,
          other: nonnegativeInteger,
        })
        .strict(),
    ),
    daily_incidents: z.array(
      z
        .object({ date: z.string().min(1), opened: nonnegativeInteger, terminal: nonnegativeInteger })
        .strict(),
    ),
    monitoring_roles: z
      .object({
        configured_thread_count: nonnegativeInteger,
        core_role_count: nonnegativeInteger,
        support_role_count: nonnegativeInteger,
        roles: z.array(
          z
            .object({
              role: z.string().min(1),
              purpose: z.string().min(1),
              configured: z.boolean(),
              recorded_action_count: nonnegativeInteger,
              activity_label: z.string().min(1),
            })
            .strict(),
        ),
        interpretation: z.string().min(1),
      })
      .strict(),
    task_activity: z.array(
      z
        .object({
          task: z.string().min(1),
          recorded_count: nonnegativeInteger,
          cadence: z.string().min(1),
        })
        .strict(),
    ),
    incidents: z
      .object({
        opened_ids: z.array(z.string()),
        terminal_ids: z.array(z.string()),
        open_at_end_ids: z.array(z.string()),
        terminal_statuses: countMapSchema,
        effectiveness_statuses: countMapSchema,
        false_positive_terminal_count: nonnegativeInteger,
        sampled_false_negative_mentions: nonnegativeInteger,
      })
      .strict(),
    limitations: z.array(z.string()),
    blocks: z.array(
      z
        .object({
          block: nonnegativeInteger,
          first_seen: z.string().min(1),
          last_seen: z.string().min(1),
          event_count: nonnegativeInteger,
          checkpoint_count: nonnegativeInteger,
        })
        .strict(),
    ),
  })
  .strict()

const reportMetricSummarySchema = supervisionMetricsSchema
  .extend({
    line_items: z.array(
      z
        .object({
          active_block: z.string(),
          category: z.string(),
          kind: z.string(),
          record_id: z.string().min(1),
          severity: z.string(),
          status: z.string(),
          summary: z.string(),
          timestamp: z.string().min(1),
        })
        .strict(),
    ),
    tooling_changes: z.array(
      z
        .object({
          category: z.string(),
          record_id: z.string().min(1),
          status: z.string(),
          summary: z.string(),
          timestamp: z.string().min(1),
        })
        .strict(),
    ),
  })
  .strict()

const metricsOwner = z.literal("supervise-tracker-runs/scripts/weekly_report.py")
const metricsProjectionSchema = z.discriminatedUnion("status", [
  z
    .object({
      status: z.literal("available"),
      definition_owner: metricsOwner,
      metrics: supervisionMetricsSchema,
      error: z.null(),
    })
    .strict(),
  z
    .object({
      status: z.literal("unavailable"),
      definition_owner: metricsOwner,
      metrics: z.null(),
      error: projectionErrorSchema,
    })
    .strict(),
])

const reportMemberSchema = z
  .object({
    name: z.string().min(1),
    path: z.string().min(1),
    media_type: z.string().min(1),
    bytes: nonnegativeInteger,
    sha256: fingerprintSchema,
    read_only: z.literal(true),
  })
  .strict()

const weeklyVerificationSchema = z
  .object({
    valid: z.literal(true),
    report_id: z.string().min(1),
    source_root: fingerprintSchema,
    manifest_root: fingerprintSchema,
    page_count: nonnegativeInteger,
    pdf_path: z.string().min(1),
    report_sha256: fingerprintSchema,
    review_sha256: fingerprintSchema,
    pdf_sha256: fingerprintSchema,
  })
  .strict()

const weeklyDeliverySchema = z
  .object({
    status: z.enum(["not-ready", "unavailable", "pending", "delivered", "stale"]),
    configured: z.boolean(),
    retryable: z.boolean(),
    record_id: nullableString,
    message_id: nullableString,
    thread_id: nullableString,
    reason: nullableString,
  })
  .strict()

const weeklyReportWorkflowSchema = z
  .object({
    status: z.enum(["available", "unavailable"]),
    stage: z.enum([
      "prepare",
      "review-finalize",
      "finalize-verify",
      "delivery",
      "delivery-stale",
      "verified",
      "delivered",
      "unavailable",
    ]),
    next_action: z.enum(["prepare", "review-finalize", "finalize-verify", "deliver"]).nullable(),
    actionable: z.boolean(),
    report_id: nullableString,
    coverage: metricCoverageSchema.nullable(),
    coverage_days: nonnegativeInteger.nullable(),
    timezone: nullableString,
    source_root: fingerprintSchema.nullable(),
    manifest_root: fingerprintSchema.nullable(),
    fingerprint: fingerprintSchema.nullable(),
    writer_role: z.literal("roundup_writer"),
    writer_task_id: nullableString,
    expected_members: z.array(z.string().min(1)),
    members: z.array(reportMemberSchema),
    stages: z.array(
      z
        .object({
          id: z.enum([
            "prepare",
            "source-currentness",
            "cognitive-review",
            "finalize",
            "verify",
            "display",
            "delivery",
          ]),
          label: z.string().min(1),
          status: z.enum(["pending", "current", "complete", "unavailable"]),
          owner: z.string().min(1),
        })
        .strict(),
    ),
    delivery: weeklyDeliverySchema,
    limitations: z.array(z.string()),
    error: projectionErrorSchema.nullable(),
  })
  .strict()

const terminalReportWorkflowSchema = z
  .object({
    status: z.enum(["available", "unavailable"]),
    stage: z.enum([
      "prepare",
      "review-finalize",
      "finalize-verify",
      "delivery",
      "delivery-stale",
      "verified",
      "delivered",
      "unavailable",
    ]),
    next_action: z.enum(["prepare", "review-finalize", "finalize-verify", "deliver"]).nullable(),
    actionable: z.boolean(),
    report_set_id: nullableString,
    source_root: fingerprintSchema.nullable(),
    manifest_root: fingerprintSchema.nullable(),
    fingerprint: fingerprintSchema.nullable(),
    state_fingerprint: z.string().min(1).max(128).nullable(),
    mission_root: fingerprintSchema.nullable(),
    completion: z
      .object({
        status: z.enum(["reconciled", "unavailable"]),
        record_id: nullableString,
        lifecycle_record_id: nullableString,
        reconciled: z.boolean(),
      })
      .strict(),
    coverage: z
      .object({
        delta_start: z.string().min(1),
        full_start: z.string().min(1),
        end: z.string().min(1),
        delta_anchor_record_id: z.string().min(1),
        delta_anchor_kind: z.enum(["roundup", "supervision-inception", "verified-prior-report"]),
      })
      .strict()
      .nullable(),
    prior_reports: z.array(
      z
        .object({
          report_id: z.string().min(1),
          source_root: fingerprintSchema,
          manifest_root: fingerprintSchema,
          coverage: metricCoverageSchema.nullable(),
        })
        .strict(),
    ),
    writer_role: z.literal("base_reviewer"),
    writer_task_id: nullableString,
    expected_members: z.array(z.string().min(1)),
    members: z.array(reportMemberSchema),
    stages: z.array(
      z
        .object({
          id: z.enum([
            "prepare",
            "source-currentness",
            "cognitive-review",
            "finalize",
            "verify",
            "display",
            "delivery",
          ]),
          label: z.string().min(1),
          status: z.enum(["pending", "current", "complete", "unavailable"]),
          owner: z.string().min(1),
        })
        .strict(),
    ),
    delivery: z
      .object({
        status: z.enum(["not-ready", "unavailable", "pending", "delivered", "stale"]),
        configured: z.boolean(),
        required: z.boolean(),
        retryable: z.boolean(),
        record_id: nullableString,
        message_id: nullableString,
        thread_id: nullableString,
        readback_root: fingerprintSchema.nullable(),
        reason: z.string().min(1),
      })
      .strict(),
    shutdown: z
      .object({
        status: z.literal("separate-owner"),
        permitted: z.literal(false),
        reason: z.string().min(1),
      })
      .strict(),
    limitations: z.array(z.string()),
    error: projectionErrorSchema.nullable(),
  })
  .strict()

const factoryEvolutionCandidateSchema = z
  .object({
    candidate_id: z.string().min(1),
    candidate_type: z.enum([
      "detector",
      "correction",
      "exculpator",
      "skill-method",
      "tracker-method",
      "supervision",
      "execution",
      "evaluation",
      "resource-policy",
      "architecture",
      "removal",
      "experiment",
    ]),
    capability_gap: z.string().min(1),
    effect: z.string().min(1),
    protected_capabilities: z.array(z.string().min(1)),
    applicability: z.string().min(1),
    tradeoffs: z.array(z.string().min(1)),
    uncertainty: z.string().min(1),
  })
  .strict()

const factoryEvolutionComparisonPlanSchema = z
  .object({
    experiment_id: z.string().min(1),
    selected_candidate: factoryEvolutionCandidateSchema,
    rejected_paths: z.array(factoryEvolutionCandidateSchema),
    selection_rationale: z.string().min(1),
    dimensions_considered: z.array(z.enum([
      "effect",
      "recurrence",
      "reach",
      "compounding_value",
      "reliability",
      "product_gain",
      "evidence_strength",
      "cost",
      "regression_risk",
      "complexity",
      "reversibility",
      "time_to_evidence",
    ])),
    comparison_mode: z.enum(["improvement", "non-inferiority"]),
    positive_case_ids: z.array(z.string().min(1)),
    exception_case_ids: z.array(z.string().min(1)),
    expected_effects: z.array(z.string().min(1)),
    resource_bounds: z.array(z.string().min(1)),
    rollback_condition: z.string().min(1),
    success_measures: z.array(z.string().min(1)),
    regression_measures: z.array(z.string().min(1)),
    stop_condition: z.string().min(1),
    minimum_expected_delta: z.string().min(1),
    non_inferiority_justification: z.string(),
  })
  .strict()

const factoryEvolutionResultSchema = z
  .object({
    case_id: z.string().min(1),
    evidence_class: z.enum(["observed", "shadow", "synthetic"]),
    evidence_ids: z.array(z.string().min(1)),
    outcome: z.enum(["pass", "fail", "mixed"]),
    observed_effect: z.string().min(1),
    resource_cost: z.string().min(1),
    regressions: z.array(z.string().min(1)),
    condition_revision: gitRevisionSchema,
    evidence_root: fingerprintSchema,
  })
  .strict()

const factoryEvolutionComparisonResultsSchema = z
  .object({
    baseline_results: z.array(factoryEvolutionResultSchema),
    candidate_results: z.array(factoryEvolutionResultSchema),
    contrary_evidence_ids: z.array(z.string().min(1)),
    regression_findings: z.array(z.string().min(1)),
    rationale: z.string().min(1),
  })
  .strict()

const factoryEvolutionWorkflowSchema = z
  .object({
    status: z.enum(["available", "unavailable"]),
    stage: z.enum([
      "prepare",
      "finalize",
      "awaiting-implementation",
      "verified",
      "unavailable",
    ]),
    next_action: z.enum(["prepare", "finalize", "evaluate"]).nullable(),
    actionable: z.boolean(),
    evolution_id: nullableString,
    packet_id: nullableString,
    packet_root: fingerprintSchema.nullable(),
    review_id: nullableString,
    review_root: fingerprintSchema.nullable(),
    evaluation_id: nullableString,
    evaluation_root: fingerprintSchema.nullable(),
    disposition: z.enum(["promote", "advisory", "revise", "reject"]).nullable(),
    comparison_plan: factoryEvolutionComparisonPlanSchema.nullable(),
    comparison_results: factoryEvolutionComparisonResultsSchema.nullable(),
    source_report_id: nullableString,
    source_report_root: fingerprintSchema.nullable(),
    event_head_sha256: fingerprintSchema.nullable(),
    manifest_root: fingerprintSchema.nullable(),
    fingerprint: fingerprintSchema.nullable(),
    proposer: z
      .object({ role: z.literal("base_reviewer"), task_id: nullableString })
      .strict(),
    implementer: z
      .object({
        status: z.enum(["not-selected", "awaiting-owner-proof", "evaluation-evidence-recorded"]),
        task_id: nullableString,
        baseline_revision: gitRevisionSchema.nullable(),
        candidate_revision: gitRevisionSchema.nullable(),
      })
      .strict(),
    evaluator: z
      .object({ role: z.literal("reviewer"), task_id: nullableString })
      .strict(),
    expected_members: z.array(z.string().min(1)),
    members: z.array(reportMemberSchema),
    stages: z.array(
      z
        .object({
          id: z.enum(["prepare", "finalize", "external-implementation", "evaluate", "verify"]),
          label: z.string().min(1),
          status: z.enum(["pending", "current", "complete", "unavailable"]),
          owner: z.string().min(1),
        })
        .strict(),
    ),
    limitations: z.array(z.string()),
    recovery: z
      .object({
        posture: z.enum(["available", "blocked", "not-required", "unavailable"]),
        guidance: z.string().min(1),
        preserved_roots: z.array(fingerprintSchema),
      })
      .strict(),
    error: projectionErrorSchema.nullable(),
  })
  .strict()

const terminalVerificationSchema = z
  .object({
    valid: z.literal(true),
    report_set_id: z.string().min(1),
    source_root: fingerprintSchema,
    state_fingerprint: z.string().min(1),
    completion_record_id: z.string().min(1),
    lifecycle_record_id: z.string().min(1),
    manifest_root: fingerprintSchema,
    delta_pdf_path: z.string().min(1),
    full_pdf_path: z.string().min(1),
    delta_pdf_sha256: fingerprintSchema,
    full_pdf_sha256: fingerprintSchema,
    delta_page_count: nonnegativeInteger,
    full_page_count: nonnegativeInteger,
  })
  .strict()

const evolutionVerificationSchema = z
  .object({
    action: z.literal("verify"),
    evolution_id: z.string().min(1),
    stage: z.enum(["prepared", "finalized", "evaluated"]),
    packet_id: z.string().min(1),
    packet_root: fingerprintSchema,
    review_id: z.string().min(1).optional(),
    review_root: fingerprintSchema.optional(),
    evaluation_id: z.string().min(1).optional(),
    evaluation_root: fingerprintSchema.optional(),
    disposition: z.string().min(1).optional(),
  })
  .strict()

export const reportArtifactSchema = z
  .object({
    id: z.string().min(1),
    target_thread_id: z.string().min(1),
    family: z.enum(["weekly", "terminal", "factory-evolution"]),
    stage: z.string().min(1),
    status: z.enum(["available", "unavailable"]),
    source_root: fingerprintSchema.nullable(),
    manifest_root: fingerprintSchema.nullable(),
    disposition: nullableString,
    coverage: metricCoverageSchema.nullable(),
    review_summary: z
      .object({ headline: nullableString, assessment: nullableString })
      .strict()
      .nullable(),
    verification: z
      .union([weeklyVerificationSchema, terminalVerificationSchema, evolutionVerificationSchema])
      .nullable(),
    delivery: weeklyDeliverySchema.nullable(),
    members: z.array(reportMemberSchema),
    limitations: z.array(z.string()),
    error: projectionErrorSchema.nullable(),
  })
  .strict()

const reportDownloadSchema = reportMemberSchema
  .extend({
    previewable: z.boolean(),
    preview_url: z.string().startsWith(`/api/v1/reports/`).nullable(),
    download_url: z.string().startsWith(`/api/v1/reports/`).nullable(),
  })
  .strict()

export const reportDetailSchema = reportArtifactSchema
  .extend({
    metric_summary: reportMetricSummarySchema.nullable(),
    artifacts: z.array(reportDownloadSchema),
  })
  .strict()

export const runDetailSchema = runSummarySchema
  .extend({
    policy: policySchema.nullable(),
    policy_history: z.array(policyHistorySchema),
    mission_segments: z.array(missionSegmentSchema),
    incidents: z.array(incidentSchema),
    decisions: z.array(decisionSchema),
    successor_transitions: z.array(successorTransitionSchema),
    activities: z.array(supervisionEventSchema),
    activities_truncated: z.boolean(),
    conclusions: z.array(supervisionEventSchema),
    conclusions_truncated: z.boolean(),
    timeline: z.array(supervisionEventSchema),
    timeline_truncated: z.boolean(),
    operating_history: z.array(operatingTransitionSchema),
    reports: z.array(reportArtifactSchema),
    weekly_report_workflow: weeklyReportWorkflowSchema,
    terminal_report_workflow: terminalReportWorkflowSchema,
    factory_evolution_workflow: factoryEvolutionWorkflowSchema,
    metrics: metricsProjectionSchema,
  })
  .strict()

const ownerSchema = z
  .object({
    identity: z.string().min(1),
    path: z.string().min(1),
    sha256: fingerprintSchema,
    owning_revision: gitRevisionSchema.nullable(),
  })
  .strict()

const ownerBundleSchema = z
  .object({
    supervision: ownerSchema,
    weekly_report: ownerSchema,
    terminal_report: ownerSchema,
    factory_evolution: ownerSchema,
  })
  .strict()

export const attentionItemSchema = z
  .object({
    rank: nonnegativeInteger,
    rule: z.string().min(1),
    severity: z.enum(["red", "amber"]),
    target_thread_id: z.string().min(1),
    source_record_id: nullableString,
    source_identity: z.string().min(1),
    source_path: nullableString,
    source_line: z.number().int().positive().nullable(),
    observed_at: z.string().min(1),
    detail: z.string().min(1),
    detail_route: z.string().min(1),
  })
  .strict()

const envelopeMetadata = {
  source: sourceSchema.strict(),
  observed_at: z.iso.datetime({ offset: true }),
  fingerprint: fingerprintSchema,
  coverage: coverageSchema.strict(),
  limitations: z.array(z.string()),
  error: z.null(),
}

export const runListEnvelopeSchema = z
  .object({
    data: z
      .object({
        catalog_fingerprint: fingerprintSchema,
        recovered_from_previous: z.boolean(),
        owners: ownerBundleSchema,
        runs: z.array(runSummarySchema),
        attention: z.array(attentionItemSchema),
        orphan_automations: z.array(automationSchema),
        unmonitored_projects: z.array(
          z
            .object({
              project_id: z.string().min(1),
              project_label: z.string().min(1),
              root: z.string().min(1),
              status: z.literal("unmonitored"),
              reason: z.string().min(1),
            })
            .strict(),
        ),
      })
      .strict(),
    ...envelopeMetadata,
  })
  .strict()

export const runDetailEnvelopeSchema = z
  .object({
    data: z
      .object({
        catalog_fingerprint: fingerprintSchema,
        recovered_from_previous: z.boolean(),
        owners: ownerBundleSchema,
        run: runDetailSchema,
      })
      .strict(),
    ...envelopeMetadata,
  })
  .strict()

export const reportListEnvelopeSchema = z
  .object({
    data: z
      .object({
        catalog_fingerprint: fingerprintSchema,
        recovered_from_previous: z.boolean(),
        owners: ownerBundleSchema,
        reports: z.array(reportArtifactSchema),
        terminal_workflows: z.array(
          z
            .object({
              target_thread_id: z.string().min(1),
              target_label: z.string().min(1),
              project_binding: projectBindingSchema,
              workflow: terminalReportWorkflowSchema,
            })
            .strict(),
        ),
        evolution_workflows: z.array(
          z
            .object({
              target_thread_id: z.string().min(1),
              target_label: z.string().min(1),
              project_binding: projectBindingSchema,
              workflow: factoryEvolutionWorkflowSchema,
            })
            .strict(),
        ),
      })
      .strict(),
    ...envelopeMetadata,
  })
  .strict()

export const reportDetailEnvelopeSchema = z
  .object({
    data: z
      .object({
        owners: ownerBundleSchema,
        report: reportDetailSchema,
      })
      .strict(),
    ...envelopeMetadata,
  })
  .strict()

const aggregateMetricsSchema = z
  .object({
    status: z.enum(["available", "incompatible", "unavailable"]),
    definition: z.string().min(1),
    run_count: nonnegativeInteger,
    available_run_count: nonnegativeInteger,
    historical_segment_count: nonnegativeInteger,
    contract_count: nonnegativeInteger,
    contracts: z.array(
      z
        .object({
          schema_version: nonnegativeInteger,
          kind: z.literal("supervision-weekly-review"),
          coverage: metricCoverageSchema,
          denominator_note: z.string().min(1),
          target_thread_ids: z.array(z.string().min(1)),
          run_count: nonnegativeInteger,
        })
        .strict(),
    ),
    headline: countMapSchema.nullable(),
    api_equivalent_estimate: z
      .object({
        label: z.literal("API-equivalent estimate"),
        actual_billing_data: z.literal(false),
        coverage_run_count: nonnegativeInteger,
        totals: numberMapSchema.nullable(),
      })
      .strict(),
    limitations: z.array(z.string()),
  })
  .strict()

export const metricsEnvelopeSchema = z
  .object({
    data: z
      .object({
        catalog_fingerprint: fingerprintSchema,
        recovered_from_previous: z.boolean(),
        owners: ownerBundleSchema,
        aggregate: aggregateMetricsSchema,
        factory_history: factoryHistorySchema,
        per_run: z.array(
          z.discriminatedUnion("status", [
            z
              .object({
                target_thread_id: z.string().min(1),
                target_label: z.string().min(1),
                supervisor_group_id: fingerprintSchema.nullable(),
                project_binding: projectBindingSchema,
                observed_at: z.string().min(1),
                current_mission_root: fingerprintSchema.nullable(),
                lifecycle: z
                  .object({ status: nullableString, record: recordRefSchema.nullable() })
                  .strict(),
                light: lightSchema,
                operating_history: z.array(operatingTransitionSchema),
                conclusion_counts: z
                  .object({ by_kind: countMapSchema, by_category: countMapSchema })
                  .strict(),
                report_counts: countMapSchema,
                status: z.literal("available"),
                cost_label: z.literal("API-equivalent estimate"),
                metrics: supervisionMetricsSchema,
                error: z.null(),
              })
              .strict(),
            z
              .object({
                target_thread_id: z.string().min(1),
                target_label: z.string().min(1),
                supervisor_group_id: fingerprintSchema.nullable(),
                project_binding: projectBindingSchema,
                observed_at: z.string().min(1),
                current_mission_root: fingerprintSchema.nullable(),
                lifecycle: z
                  .object({ status: nullableString, record: recordRefSchema.nullable() })
                  .strict(),
                light: lightSchema,
                operating_history: z.array(operatingTransitionSchema),
                conclusion_counts: z
                  .object({ by_kind: countMapSchema, by_category: countMapSchema })
                  .strict(),
                report_counts: countMapSchema,
                status: z.literal("unavailable"),
                cost_label: z.literal("API-equivalent estimate"),
                metrics: z.null(),
                error: projectionErrorSchema,
              })
              .strict(),
          ]),
        ),
      })
      .strict(),
    ...envelopeMetadata,
  })
  .strict()

export type RunSummary = z.infer<typeof runSummarySchema>
export type RunDetail = z.infer<typeof runDetailSchema>
export type ReportArtifact = z.infer<typeof reportArtifactSchema>
export type ReportDetail = z.infer<typeof reportDetailSchema>
export type RunListEnvelope = z.infer<typeof runListEnvelopeSchema>
export type RunDetailEnvelope = z.infer<typeof runDetailEnvelopeSchema>
export type ReportListEnvelope = z.infer<typeof reportListEnvelopeSchema>
export type ReportDetailEnvelope = z.infer<typeof reportDetailEnvelopeSchema>
export type MetricsEnvelope = z.infer<typeof metricsEnvelopeSchema>

async function parsedResponse<T>(response: Response, schema: z.ZodType<T>): Promise<T> {
  const payload: unknown = await response.json()
  if (!response.ok) {
    throw new DashboardApiError(response.status, apiErrorEnvelopeSchema.parse(payload))
  }
  return schema.parse(payload)
}

export async function fetchRuns(signal?: AbortSignal): Promise<RunListEnvelope> {
  return parsedResponse(
    await fetch("/api/v1/runs", { headers: { Accept: "application/json" }, signal }),
    runListEnvelopeSchema,
  )
}

export async function fetchRun(
  targetThreadId: string,
  signal?: AbortSignal,
): Promise<RunDetailEnvelope> {
  if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{3,127}$/.test(targetThreadId)) {
    throw new Error("Run target ID is invalid.")
  }
  return parsedResponse(
    await fetch(`/api/v1/runs/${encodeURIComponent(targetThreadId)}`, {
      headers: { Accept: "application/json" },
      signal,
    }),
    runDetailEnvelopeSchema,
  )
}

export async function fetchReports(signal?: AbortSignal): Promise<ReportListEnvelope> {
  return parsedResponse(
    await fetch("/api/v1/reports", { headers: { Accept: "application/json" }, signal }),
    reportListEnvelopeSchema,
  )
}

const reportIdentityPattern = /^[A-Za-z0-9][A-Za-z0-9._:-]{3,127}$/

export async function fetchReport(
  targetThreadId: string,
  family: ReportArtifact["family"],
  reportId: string,
  signal?: AbortSignal,
): Promise<ReportDetailEnvelope> {
  if (!reportIdentityPattern.test(targetThreadId) || !reportIdentityPattern.test(reportId)) {
    throw new Error("Report identity is invalid.")
  }
  const path = [targetThreadId, family, reportId].map(encodeURIComponent).join("/")
  return parsedResponse(
    await fetch(`/api/v1/reports/${path}`, {
      headers: { Accept: "application/json" },
      signal,
    }),
    reportDetailEnvelopeSchema,
  )
}

export async function fetchReportArtifactText(
  artifactUrl: string,
  signal?: AbortSignal,
): Promise<string> {
  if (!/^\/api\/v1\/reports\/[A-Za-z0-9%._:-]+\/[A-Za-z0-9%._:-]+\/[A-Za-z0-9%._:-]+\/artifacts\/[A-Za-z0-9%._:-]+$/.test(artifactUrl)) {
    throw new Error("Report artifact URL is invalid.")
  }
  const response = await fetch(artifactUrl, {
    headers: { Accept: "application/json, text/markdown" },
    signal,
  })
  if (!response.ok) {
    const payload: unknown = await response.json()
    throw new DashboardApiError(response.status, apiErrorEnvelopeSchema.parse(payload))
  }
  const contentType = response.headers.get("Content-Type")?.split(";", 1)[0]
  if (contentType !== "application/json" && contentType !== "text/markdown") {
    throw new Error("Report artifact is not a previewable text type.")
  }
  return response.text()
}

export async function fetchMetrics(signal?: AbortSignal): Promise<MetricsEnvelope> {
  return parsedResponse(
    await fetch("/api/v1/metrics", { headers: { Accept: "application/json" }, signal }),
    metricsEnvelopeSchema,
  )
}
