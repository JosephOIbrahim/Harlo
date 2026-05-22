"""macos/launcher.py — single entry point for the Harlo.app bundle.

py2app builds a bundle whose executable is this file. The launchd
plists invoke this same executable with mode flags:

    Harlo.app/Contents/MacOS/Harlo --daemon   ← com.harlo.daemon.plist
    Harlo.app/Contents/MacOS/Harlo --agents   ← com.harlo.agents.plist
    Harlo.app/Contents/MacOS/Harlo --mcp      ← MCP server over stdio
    Harlo.app/Contents/MacOS/Harlo            ← interactive CLI

The dispatcher peels off the first matching mode arg and hands the
rest to the right submodule. First-run setup (incl. the launchd
install offer on macOS) runs only on the interactive CLI path —
calling the daemon doesn't re-trigger setup.
"""

from __future__ import annotations

import sys
from typing import Sequence


_MODE_FLAGS = {"--daemon", "--agents", "--mcp"}


def _detect_mode(argv: Sequence[str]) -> tuple[str | None, list[str]]:
    """Return (mode_flag, residual_argv).

    Recognised mode flags are matched anywhere in argv (they may
    follow other launchd-supplied args). Only the FIRST matching
    flag is consumed; everything else is passed through to the
    sub-entry untouched.
    """
    residual = list(argv)
    for flag in _MODE_FLAGS:
        if flag in residual:
            residual.remove(flag)
            return flag, residual
    return None, residual


def _run_daemon() -> int:
    from harlo.daemon.main import run_socket_activated

    run_socket_activated()
    return 0


def _run_agents(residual: list[str]) -> int:
    from agents.harness import main as agents_main

    args = list(residual)
    if "--socket-activated" not in args:
        args.append("--socket-activated")
    return agents_main(args)


def _run_mcp() -> int:
    from harlo.mcp_server import main as mcp_main

    mcp_main()
    return 0


def _run_cli(residual: list[str]) -> int:
    from harlo.session.first_run import prompt_install_launchd, run_first_run

    result = run_first_run()
    if result.fresh_install:
        prompt_install_launchd()

    from harlo.cli.main import main as cli_main

    # Click reads sys.argv directly. Trim our mode-arg residue so
    # Click sees only the user-facing CLI args.
    sys.argv = [sys.argv[0], *residual]
    cli_main()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Single entry point. Returns an exit code suitable for sys.exit."""
    raw = list(sys.argv[1:] if argv is None else argv)
    mode, residual = _detect_mode(raw)

    if mode == "--daemon":
        return _run_daemon()
    if mode == "--agents":
        return _run_agents(residual)
    if mode == "--mcp":
        return _run_mcp()

    return _run_cli(residual)


if __name__ == "__main__":
    sys.exit(main())
