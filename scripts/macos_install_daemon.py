#!/usr/bin/env python3
"""Install (or uninstall) Harlo's launchd units on macOS.

Three units may be installed:

  com.harlo.daemon       — socket-activated, 0W idle
  com.harlo.agents       — socket-activated, 0W idle
  com.harlo.healthbridge — opt-in KeepAlive (ADR-0001)

Usage:

  python scripts/macos_install_daemon.py install --daemon --agents
  python scripts/macos_install_daemon.py uninstall --healthbridge
  python scripts/macos_install_daemon.py status

The script is idempotent: install over an existing unit replaces it.
It never enables `com.harlo.healthbridge` automatically — only the
user's explicit "Connect HealthKit" action in Settings can.
"""

from __future__ import annotations

import argparse
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
PLIST_DIR = REPO_ROOT / "macos" / "launchd"

# Canonical install path the bundled plists reference. Override at
# install time via HARLO_APP_PATH (e.g. for dev runs, homebrew cask
# locations, or user-local /Applications variants).
DEFAULT_APP_PATH = Path("/Applications/Harlo.app")
DEFAULT_BRIDGE_PATH = Path("/Applications/HarloHealthBridge.app")


def _resolved_app_path() -> Path:
    override = os.environ.get("HARLO_APP_PATH")
    return Path(override).expanduser() if override else DEFAULT_APP_PATH


def _resolved_bridge_path() -> Path:
    override = os.environ.get("HARLO_BRIDGE_APP_PATH")
    return Path(override).expanduser() if override else DEFAULT_BRIDGE_PATH


def _executable_for(unit_key: str) -> Path:
    """Locate the executable inside the right bundle for this unit."""
    if unit_key == "healthbridge":
        return _resolved_bridge_path() / "Contents" / "MacOS" / "HarloHealthBridge"
    return _resolved_app_path() / "Contents" / "MacOS" / "Harlo"


def _retemplate_plist(src: Path, unit_key: str) -> dict:
    """Load the source plist and substitute ProgramArguments[0] with
    the actual bundle executable path on this host.

    Plists shipped in the repo reference /Applications/...; this
    function rewrites the path when the bundle is somewhere else
    (HARLO_APP_PATH / HARLO_BRIDGE_APP_PATH set, or dev install).
    """
    with src.open("rb") as fh:
        plist = plistlib.load(fh)
    args = list(plist.get("ProgramArguments") or [])
    if not args:
        raise ValueError(f"{src}: ProgramArguments is empty")
    args[0] = str(_executable_for(unit_key))
    plist["ProgramArguments"] = args
    return plist

UNITS = {
    "daemon": "com.harlo.daemon",
    "agents": "com.harlo.agents",
    "healthbridge": "com.harlo.healthbridge",
}


def _user_launch_agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def _is_macos() -> bool:
    return sys.platform == "darwin"


def _domain_target() -> str:
    uid = os.getuid()
    return f"gui/{uid}"


def _run(cmd: list[str]) -> int:
    print(f"+ {' '.join(cmd)}")
    return subprocess.call(cmd)


def _install_one(unit_key: str) -> None:
    label = UNITS[unit_key]
    src = PLIST_DIR / f"{label}.plist"
    if not src.exists():
        raise FileNotFoundError(f"missing plist: {src}")
    dst_dir = _user_launch_agents_dir()
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"{label}.plist"

    # Unload first if present (idempotent install).
    if dst.exists():
        _run(["launchctl", "bootout", f"{_domain_target()}/{label}"])

    # Re-template the bundle executable path before writing. The
    # repo's plist hardcodes /Applications/Harlo.app; if Harlo.app
    # lives elsewhere on this host (dev run, custom prefix), the
    # HARLO_APP_PATH env var supplies the actual location.
    templated = _retemplate_plist(src, unit_key)
    with dst.open("wb") as fh:
        plistlib.dump(templated, fh)

    if unit_key == "healthbridge":
        # Bootstrap but do not enable — the user toggles this from
        # Harlo's HealthKit pane.
        print(
            f"installed {label} (NOT bootstrapped — enable from "
            f"Harlo → Settings → HealthKit)"
        )
        return

    _run(["launchctl", "bootstrap", _domain_target(), str(dst)])
    _run(["launchctl", "enable", f"{_domain_target()}/{label}"])


def _uninstall_one(unit_key: str) -> None:
    label = UNITS[unit_key]
    dst = _user_launch_agents_dir() / f"{label}.plist"
    if dst.exists():
        _run(["launchctl", "bootout", f"{_domain_target()}/{label}"])
        dst.unlink()
        print(f"removed {dst}")
    else:
        print(f"{label}: not installed")


def _status(units: Iterable[str]) -> None:
    for unit_key in units:
        label = UNITS[unit_key]
        rc = _run(["launchctl", "print", f"{_domain_target()}/{label}"])
        print(f"{label}: launchctl print exit={rc}")


def main(argv: list[str] | None = None) -> int:
    if not _is_macos():
        print("This installer only runs on macOS.", file=sys.stderr)
        return 2

    parser = argparse.ArgumentParser(prog="macos_install_daemon")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def _add_unit_flags(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--daemon", action="store_true")
        sp.add_argument("--agents", action="store_true")
        sp.add_argument("--healthbridge", action="store_true")
        sp.add_argument(
            "--all",
            action="store_true",
            help="Apply to all units except healthbridge (which is opt-in).",
        )

    _add_unit_flags(sub.add_parser("install"))
    _add_unit_flags(sub.add_parser("uninstall"))
    _add_unit_flags(sub.add_parser("status"))

    args = parser.parse_args(argv)

    selected: list[str] = []
    if args.daemon:
        selected.append("daemon")
    if args.agents:
        selected.append("agents")
    if args.healthbridge:
        selected.append("healthbridge")
    if args.all and not selected:
        selected = ["daemon", "agents"]

    if not selected:
        parser.error("specify --daemon, --agents, --healthbridge, or --all")

    op = {
        "install": _install_one,
        "uninstall": _uninstall_one,
        "status": lambda u: _status([u]),
    }[args.cmd]

    for unit_key in selected:
        op(unit_key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
