"""Domain errors raised by the Software Factory runtime."""


class StoreError(RuntimeError):
    """Base error for persistence and runtime invariant failures."""


class StaleState(StoreError):
    """The caller's expected aggregate version no longer matches."""


class AuthorityDenied(StoreError):
    """The requested effect is outside current authority."""


class InvalidTransition(StoreError):
    """A requested state transition violates the domain state machine."""


class EvidenceInvalid(StoreError):
    """Evidence is missing, stale, failed, or bound to the wrong subject/revision."""


class LeaseConflict(StoreError):
    """A requested resource lease conflicts with an existing active lease."""


class StaleLease(StoreError):
    """A worker result was produced under an expired or superseded lease generation."""


class RoleConflict(StoreError):
    """Required independent roles are not distinct."""


class ProviderError(StoreError):
    """An external execution provider failed to dispatch, poll, or cancel work."""
