from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AuthorityClass = Literal["operational", "semantic", "evidence", "support"]


@dataclass(frozen=True)
class LifecycleOwner:
    """One primary owner plus the coordinators allowed into its transaction."""

    concern: str
    primary_module: str
    authoritative_tables: tuple[str, ...]
    transaction_participants: tuple[str, ...] = ()
    authority_class: AuthorityClass = "operational"

    @property
    def writer_modules(self) -> tuple[str, ...]:
        return (self.primary_module, *self.transaction_participants)


# This is deliberately exhaustive over tables written by runtime Python. A table
# may appear exactly once. A participant is a bounded transaction participant,
# not a second lifecycle authority.
LIFECYCLE_OWNERS = (
    LifecycleOwner(
        "schema_lineage",
        "database",
        ("schema_migrations", "meta"),
        authority_class="support",
    ),
    LifecycleOwner("event_ledger", "audit", ("events",), authority_class="evidence"),
    LifecycleOwner(
        "command_ledger",
        "audit",
        ("commands",),
        ("doctor",),
        authority_class="evidence",
    ),
    LifecycleOwner(
        "evidence_ledger",
        "audit",
        ("evidence_records",),
        ("qa",),
        authority_class="evidence",
    ),
    LifecycleOwner(
        "mission_authority",
        "mission",
        ("projects", "repositories", "missions", "authority_records"),
        ("continuation", "audit"),
    ),
    LifecycleOwner(
        "capability_obligation",
        "capability",
        ("capabilities", "obligations", "obligation_dependencies"),
        ("continuation", "controller", "qa"),
    ),
    LifecycleOwner("program", "program", ("programs", "program_revisions")),
    LifecycleOwner("engine_submission", "engine", ("engine_submissions_v2",)),
    LifecycleOwner(
        "work",
        "work_items",
        ("work_items", "work_dependencies"),
        ("controller", "execution", "qa"),
    ),
    LifecycleOwner(
        "agent_session_assignment",
        "agents",
        ("agent_sessions", "work_assignments"),
        ("controller", "execution"),
    ),
    LifecycleOwner(
        "workspace",
        "workspaces",
        ("workspaces",),
        ("agents", "controller", "execution"),
    ),
    LifecycleOwner(
        "execution",
        "execution",
        ("executions", "leases", "provider_callbacks"),
        ("controller", "qa", "reflection", "supervision"),
    ),
    LifecycleOwner("quality_assurance", "qa", ("qa_requirements", "qa_results")),
    LifecycleOwner("artifacts", "artifacts", ("artifacts",), authority_class="evidence"),
    LifecycleOwner(
        "acceptance_evidence",
        "acceptance",
        ("acceptance_runs", "acceptance_case_results"),
        authority_class="evidence",
    ),
    LifecycleOwner(
        "acceptance_governance",
        "governance",
        (
            "acceptance_contracts_v2",
            "acceptance_probe_results_v2",
            "independent_review_executions_v2",
            "acceptance_decisions_v2",
            "external_effect_intents_v2",
            "notification_report_links_v2",
            "role_grants_v2",
        ),
    ),
    LifecycleOwner(
        "acceptance_lifecycle",
        "acceptance_lifecycle",
        ("acceptance_stage_records_v2", "outcome_reconciliations_v2"),
    ),
    LifecycleOwner(
        "supervision",
        "supervision",
        ("supervision_assignments", "supervision_checks", "incidents"),
    ),
    LifecycleOwner(
        "delivery_and_operator_action",
        "reporting",
        (
            "schedules_v2",
            "notifications_v2",
            "notification_attempts_v2",
            "operator_action_tokens_v2",
            "operator_decisions_v2",
        ),
    ),
    LifecycleOwner(
        "report",
        "reporting",
        ("reports_v2",),
        ("governance",),
        authority_class="evidence",
    ),
    LifecycleOwner(
        "adaptive_outcome",
        "adaptive",
        ("adaptive_actions", "strategy_outcomes"),
        authority_class="semantic",
    ),
    LifecycleOwner(
        "librsi_semantic_cache",
        "integrations.librsi.service",
        (
            "librsi_records",
            "librsi_record_bindings",
            "librsi_cutover_receipts_v2",
        ),
        authority_class="semantic",
    ),
    LifecycleOwner(
        "learning",
        "learning",
        (
            "active_signal_bundles",
            "experiment_runs_v2",
            "experiments_v2",
            "hypotheses_v2",
            "hypothesis_evidence_v2",
            "learned_signal_candidates",
            "observed_stream_events",
            "reflections_v2",
            "signal_effectiveness_reviews",
            "signal_evaluations_v2",
            "signal_occurrences",
        ),
        ("migration",),
        authority_class="semantic",
    ),
    LifecycleOwner(
        "evolution",
        "evolution",
        (
            "active_selector_policies_v2",
            "evolution_checkpoints_v2",
            "program_change_candidates_v2",
            "program_portfolios_v2",
            "selection_outcomes_v2",
            "selection_records_v2",
            "selection_reviews_v2",
            "selector_policy_candidates_v2",
            "selector_policy_evaluations_v2",
        ),
        authority_class="semantic",
    ),
    LifecycleOwner(
        "problem_solving",
        "problem_solving",
        (
            "next_action_decisions_v2",
            "problem_cycle_verifications_v2",
            "problem_experiment_designs_v2",
            "problem_solving_cycles_v2",
            "strategy_attempts_v2",
            "strategy_candidates_v2",
        ),
        authority_class="semantic",
    ),
    LifecycleOwner(
        "migration_cutover",
        "migration",
        (
            "cutover_effects_v2",
            "cutover_path_effects_v2",
            "migration_items_v2",
            "migration_runs_v2",
            "parity_cases_v2",
        ),
    ),
    LifecycleOwner(
        "release",
        "operations",
        (
            "immutable_releases_v2",
            "release_reviews_v2",
            "release_verifications_v2",
        ),
        ("release",),
    ),
    LifecycleOwner(
        "recovery",
        "operations",
        (
            "factory_recovery_cases_v2",
            "recovery_resume_tokens_v2",
            "release_agent_refreshes_v2",
        ),
        ("recovery",),
    ),
    LifecycleOwner(
        "preservation_cleanup",
        "operations",
        (
            "cleanup_effects_v2",
            "cleanup_items_v2",
            "preservation_bundles_v2",
            "repository_inventories_v2",
        ),
        ("reconciliation",),
    ),
    LifecycleOwner(
        "reconciliation",
        "reconciliation",
        ("integration_candidates_v2", "restart_workspaces_v2"),
    ),
)


def owner_for_table(table: str) -> LifecycleOwner:
    matches = [owner for owner in LIFECYCLE_OWNERS if table in owner.authoritative_tables]
    if len(matches) != 1:
        raise KeyError(f"expected one lifecycle owner for {table}, found {len(matches)}")
    return matches[0]
