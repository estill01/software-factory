from __future__ import annotations

from .errors import RSITransitionError


class ReviewPolicy:
    """Role-separation rules shared by improvement decisions."""

    @staticmethod
    def require_independent_actor(
        *, author_id: str | None, reviewer_id: str | None, subject: str
    ) -> None:
        if author_id is not None and reviewer_id == author_id:
            raise RSITransitionError(f"{subject} cannot independently review it")
