from __future__ import annotations

from .database import Database

# Historical public name retained as an exact alias to the one persistence owner.
Store = Database

__all__ = ["Store"]
