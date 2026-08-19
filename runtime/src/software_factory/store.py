from __future__ import annotations

from .audit import AuditMixin
from .database import DatabaseStore


class Store(AuditMixin, DatabaseStore):
    """Transactional SQL state and hash-chained audit owner."""
