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

import os
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


_BUNDLE_ID = "com.josephibrahim.harlo"


def _is_finder_launch(residual: list[str]) -> bool:
    """True ONLY for a LaunchServices (Finder double-click) launch.

    LaunchServices sets __CFBundleIdentifier to the launched bundle's
    id; terminal children inherit com.apple.Terminal instead, and
    pytest/scripts have neither. Matching OUR id exactly keeps piped
    scripted invocations and test harnesses on the CLI path.
    """
    return (
        sys.platform == "darwin"
        and not residual
        and not sys.stdin.isatty()
        and os.environ.get("__CFBundleIdentifier") == _BUNDLE_ID
    )


def _show_finder_dialog() -> None:
    """Give the double-click user actual feedback (CTO review D55).

    Native dialog via osascript — no UI framework in the bundle.
    Failure is swallowed: a broken dialog must never break the CLI.
    """
    import subprocess

    text = (
        "Harlo is running.\\n\\n"
        "Harlo works through Claude Desktop (as an MCP server) "
        "or from Terminal:\\n\\n"
        "  /Applications/Harlo.app/Contents/MacOS/Harlo --help\\n\\n"
        "To install the on-demand background services, run that "
        "command in Terminal and follow the setup prompt."
    )
    script = (
        f'display dialog "{text}" with title "Harlo" '
        'buttons {"OK"} default button "OK" giving up after 120'
    )
    try:
        subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True, timeout=130, check=False,
        )
    except Exception:
        pass


def _run_cli(residual: list[str]) -> int:
    from harlo.session.first_run import prompt_install_launchd, run_first_run

    result = run_first_run()

    # D55: a Finder double-click previously fell through to Click with
    # no TTY — zero visible feedback — while the launchd offer stamped
    # itself "no-tty" forever. Now: show a real dialog and return;
    # the onboarding offer stays available for an interactive launch.
    if _is_finder_launch(residual):
        _show_finder_dialog()
        return 0

    # D55 (review catch): prompt unconditionally on interactive launches,
    # not only when fresh_install — a silent Finder first launch consumes
    # the one-shot fresh_install flag via run_first_run(), which would
    # otherwise re-suppress the offer through a different marker. The
    # prompt is idempotent (gated internally by .launchd_offered).
    del result  # first-run result no longer gates the offer
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
