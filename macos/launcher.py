"""Thin launcher used as py2app's `APP` entry point.

When users double-click `Harlo.app`, this is what runs. It:

  1. Runs first-run setup (data dir creation, legacy migration, and
     — new in Phase 5A — offering to install the launchd units).
  2. Hands control to the existing CLI / MCP entry point.

Kept deliberately tiny so py2app's wrapper has nothing to trip over.
"""

from __future__ import annotations

import sys


def main() -> int:
    from harlo.session.first_run import run_first_run, prompt_install_launchd

    result = run_first_run()
    if result.fresh_install:
        prompt_install_launchd()

    # Fall through to the regular Harlo CLI. The app's Info.plist
    # marks LSUIElement=true, so there's no dock icon; this process
    # exits as soon as the CLI/MCP entry returns. The launchd
    # daemon (installed during first-run) handles steady-state work.
    from harlo.cli.main import main as cli_main
    cli_main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
