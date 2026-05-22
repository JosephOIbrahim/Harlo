"""First-run setup for the Harlo daemon.

Marker-file gated: runs once per data directory. Handles:

1. Creating the new platform-aware DATA_DIR.
2. One-shot migration of legacy state from PROJECT_ROOT/data — for
   dogfood users whose data lived in the source tree before the
   macOS bundle moved DATA_DIR to ~/Library/Application Support/Harlo.
3. Stamping a marker so future launches skip the migration.

Honors Rule 1: no polling, no while-True. Called exactly once on
daemon startup (or first MCP call) from the boot path.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import NamedTuple

from harlo.daemon.config import (
    AGENTS_DIR,
    DATA_DIR,
    DEFERRED_DIR,
    PROJECT_ROOT,
    STAGES_DIR,
    ensure_data_dirs,
)

_LOGGER = logging.getLogger(__name__)
_MARKER = DATA_DIR / ".first_run_complete"
_LEGACY_DATA = PROJECT_ROOT / "data"


class FirstRunResult(NamedTuple):
    fresh_install: bool
    migrated_from: Path | None
    migrated_paths: tuple[str, ...]


def already_completed() -> bool:
    return _MARKER.exists()


def run_first_run() -> FirstRunResult:
    """Idempotent setup. Returns description of what happened.

    Safe to call on every boot — short-circuits when the marker exists.
    """
    if already_completed():
        return FirstRunResult(fresh_install=False, migrated_from=None, migrated_paths=())

    ensure_data_dirs()

    migrated: list[str] = []
    migrated_from: Path | None = None

    if _LEGACY_DATA.exists() and _LEGACY_DATA.resolve() != DATA_DIR.resolve():
        migrated_from = _LEGACY_DATA
        for item in _LEGACY_DATA.iterdir():
            target = DATA_DIR / item.name
            if target.exists():
                _LOGGER.info("first-run: skip %s (target exists)", item.name)
                continue
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
            migrated.append(item.name)

    _MARKER.write_text("ok\n", encoding="utf-8")
    fresh = migrated_from is None
    return FirstRunResult(
        fresh_install=fresh,
        migrated_from=migrated_from,
        migrated_paths=tuple(migrated),
    )


__all__ = ["FirstRunResult", "already_completed", "run_first_run"]
