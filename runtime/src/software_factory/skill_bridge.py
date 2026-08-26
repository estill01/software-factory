"""Compatibility import for the retired projection-only skill bridge.

The installed ``sf-skill`` command targets :mod:`software_factory.native_skills`
directly.  This module remains only so older imports reach the same native
dispatcher instead of retaining a second, non-operative command path.
"""

from .native_skills import SKILLS, build_parser, invoke, main

__all__ = ["SKILLS", "build_parser", "invoke", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
