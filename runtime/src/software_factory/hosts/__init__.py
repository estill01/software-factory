"""Thin hosts over the one authoritative Factory engine."""

from .embedded import EmbeddedFactoryHost
from .service import StandaloneFactoryService

__all__ = ["EmbeddedFactoryHost", "StandaloneFactoryService"]
