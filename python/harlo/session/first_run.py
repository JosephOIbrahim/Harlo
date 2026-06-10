"""First-run setup for the Harlo daemon.

Marker-file gated: runs once per data directory. Handles:

1. Creating the new platform-aware DATA_DIR.
2. One-shot migration of legacy state from PROJECT_ROOT/data — for
   dogfood users whose data lived in the source tree before the
   macOS bundle moved DATA_DIR to ~/Library/Application Support/Harlo.
3. Stamping a marker so future launches skip the migration.
4. (Phase 5A) Offering to install the socket-activated launchd
   units on macOS so the daemon and MOE harness become available
   without a separate `make install` step. The prompt is shown
   exactly once; the user can decline.

Honors Rule 1: no polling, no while-True. Called exactly once on
daemon startup (or first MCP call) from the boot path.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
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
            try:
                if item.is_dir():
                    # Recursive merge — overwrite any engine-bootstrap
                    # stubs the daemon may have authored before first-run
                    # ran (e.g., the empty `schedule.usda` skeleton from
                    # schedule_migrate.migrate_inline()). We are gated by
                    # .first_run_complete; if we're here, target subdirs
                    # hold only auto-generated stubs, not user data.
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    # Top-level files (twin.db, observations.db, …) are
                    # user data — never clobber.
                    if target.exists():
                        _LOGGER.info("first-run: skip %s (target exists)", item.name)
                        continue
                    shutil.copy2(item, target)
                migrated.append(item.name)
            except OSError as exc:
                _LOGGER.warning("first-run: failed to migrate %s: %s", item.name, exc)

    _MARKER.write_text("ok\n", encoding="utf-8")
    fresh = migrated_from is None
    return FirstRunResult(
        fresh_install=fresh,
        migrated_from=migrated_from,
        migrated_paths=tuple(migrated),
    )


_LAUNCHD_MARKER = DATA_DIR / ".launchd_offered"


def _find_install_script() -> Path | None:
    """Find scripts/macos_install_daemon.py either in dev tree or
    inside a py2app bundle's Resources/scripts/."""
    candidates = [
        PROJECT_ROOT / "scripts" / "macos_install_daemon.py",
    ]
    # py2app puts data_files into Contents/Resources/<subdir>/
    bundle_resources = Path(sys.executable).resolve().parent.parent / "Resources"
    if bundle_resources.exists():
        candidates.append(bundle_resources / "scripts" / "macos_install_daemon.py")
    for c in candidates:
        if c.exists():
            return c
    return None


def prompt_install_launchd(
    *,
    auto_accept: bool | None = None,
    out=sys.stdout,
) -> bool:
    """Offer to install the launchd daemon + agents units.

    Idempotent: the offer is made once per DATA_DIR (a separate
    marker from the first-run completion marker, so re-running
    first-run after a manual uninstall still re-prompts).

    Args:
        auto_accept: If True, install without prompting (used by
            installers). If False, just stamp the marker and skip.
            If None (default), prompt interactively when stdin is a
            tty, otherwise no-op.
        out: stream to write user-facing prompts to.

    Returns:
        True if the install was actually performed, False otherwise.
    """
    if sys.platform != "darwin":
        return False
    if _LAUNCHD_MARKER.exists():
        return False

    if auto_accept is None and not sys.stdin.isatty():
        # Non-interactive (Finder launch, piped, MCP child): do NOT
        # stamp ANY marker — a silent launch must never permanently
        # suppress the onboarding offer (CTO review D55). This check
        # runs before the script lookup so the missing-script stamp
        # below can only happen in an interactive context.
        return False

    script = _find_install_script()
    if script is None:
        _LOGGER.warning("first-run: macos_install_daemon.py not found; skipping")
        _LAUNCHD_MARKER.write_text("missing-script\n", encoding="utf-8")
        return False

    if auto_accept is None:
        out.write(
            "\nHarlo can install two background services so the CLI and "
            "agent harness wake on-demand:\n"
            "  • com.harlo.daemon   — handles `harlo` CLI calls (0W idle)\n"
            "  • com.harlo.agents   — runs MOE agent tasks (0W idle)\n"
            "\nNeither is KeepAlive. Either can be removed later with:\n"
            "  python scripts/macos_install_daemon.py uninstall --daemon --agents\n"
            "\nInstall now? [Y/n] "
        )
        out.flush()
        try:
            response = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            response = "n"
        accept = response in {"", "y", "yes"}
    else:
        accept = bool(auto_accept)

    if not accept:
        _LAUNCHD_MARKER.write_text("declined\n", encoding="utf-8")
        return False

    cmd = [sys.executable, str(script), "install", "--all"]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        _LOGGER.error("first-run: launchd install failed: %s", exc)
        _LAUNCHD_MARKER.write_text(f"failed: {exc.returncode}\n", encoding="utf-8")
        return False

    _LAUNCHD_MARKER.write_text("installed\n", encoding="utf-8")
    return True


__all__ = [
    "FirstRunResult",
    "already_completed",
    "prompt_install_launchd",
    "run_first_run",
]
