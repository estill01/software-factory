from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LifecycleOwner:
    """One primary owner plus the coordinators allowed into its transaction."""

    concern: str
    primary_module: str
    authoritative_tables: tuple[str, ...]
    transaction_participants: tuple[str, ...] = ()

    @property
    def writer_modules(self) -> tuple[str, ...]:
        return (self.primary_module, *self.transaction_participants)


LIFECYCLE_OWNERS = (
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
    LifecycleOwner(
        "program",
        "program",
        ("programs", "program_revisions"),
    ),
    LifecycleOwner(
        "work",
        "work_items",
        ("work_items", "work_dependencies"),
        ("controller", "execution", "qa"),
    ),
    LifecycleOwner(
        "execution",
        "execution",
        ("executions", "leases", "provider_callbacks"),
        ("controller", "qa", "reflection", "supervision"),
    ),
    LifecycleOwner(
        "quality_assurance",
        "qa",
        ("qa_requirements", "qa_results"),
    ),
    LifecycleOwner(
        "acceptance_evidence",
        "acceptance",
        ("acceptance_runs", "acceptance_case_results"),
    ),
    LifecycleOwner(
        "acceptance_governance",
        "governance",
        (
            "acceptance_contracts_v2",
            "probe_results_v2",
            "independent_review_executions_v2",
            "acceptance_decisions_v2",
        ),
    ),
    LifecycleOwner(
        "supervision",
        "supervision",
        ("supervision_assignments", "supervision_checks", "incidents"),
    ),
    LifecycleOwner(
        "delivery",
        "reporting",
        (
            "schedules_v2",
            "reports_v2",
            "notifications_v2",
            "notification_attempts_v2",
            "operator_action_tokens_v2",
            "operator_decisions_v2",
        ),
        ("governance",),
    ),
    LifecycleOwner(
        "release_recovery",
        "operations",
        ("immutable_releases_v2", "factory_recovery_cases_v2"),
        ("release",),
    ),
)


def owner_for_table(table: str) -> LifecycleOwner:
    matches = [owner for owner in LIFECYCLE_OWNERS if table in owner.authoritative_tables]
    if len(matches) != 1:
        raise KeyError(f"expected one lifecycle owner for {table}, found {len(matches)}")
    return matches[0]
