"""Convenience re-export of the settings singleton.

Kept as a separate module so imports read naturally as
`from app.core.settings import settings` while all definitions live in
`config.py`.
"""

from __future__ import annotations

from app.core.config import Settings, get_settings

# Eagerly-resolved singleton for modules that just want the values.
settings: Settings = get_settings()

__all__ = ["settings", "get_settings", "Settings"]
