"""P4a — `scripts/check_signing_readiness.sh` keeps the baseline green.

This is a regression guard. The branch is supposed to be sign-ready
(Phase 5A foundation shipped). If a future commit drops a documented
secret, breaks a plist, or renames a bundle identifier, the readiness
script catches it before the macOS-15 CI runner burns minutes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "check_signing_readiness.sh"


@pytest.mark.skipif(
    shutil.which("bash") is None, reason="bash unavailable in this environment"
)
def test_readiness_script_exists_and_is_executable() -> None:
    assert _SCRIPT.exists(), f"script missing: {_SCRIPT}"
    # Executable bit is the CI contract — Makefile invocations rely on it.
    assert os.access(_SCRIPT, os.X_OK), "script lacks +x"


@pytest.mark.skipif(
    shutil.which("bash") is None, reason="bash unavailable"
)
def test_readiness_script_passes_on_clean_branch() -> None:
    """Run the script and expect a green exit. If this fails, print
    the script output so the regression is visible at a glance."""
    proc = subprocess.run(
        ["bash", str(_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
        timeout=30,
    )
    if proc.returncode != 0:
        pytest.fail(
            "check_signing_readiness.sh failed:\n"
            f"--- stdout ---\n{proc.stdout}\n"
            f"--- stderr ---\n{proc.stderr}"
        )


@pytest.mark.skipif(
    shutil.which("bash") is None, reason="bash unavailable"
)
def test_readiness_script_fails_when_info_plist_is_broken(tmp_path) -> None:
    """Smoke check that the script ACTUALLY fails on regressions — not
    a no-op that always exits 0. Symlink a sandbox tree pointing at a
    broken Info.plist and confirm the script exits nonzero.

    The script discovers paths relative to its own location, so we
    layer a temporary repo root with a deliberately broken plist."""
    sandbox = tmp_path / "fake_repo"
    sandbox.mkdir()
    (sandbox / "scripts").mkdir()
    (sandbox / "scripts" / "check_signing_readiness.sh").symlink_to(_SCRIPT)
    (sandbox / "macos" / "Harlo.app" / "Contents").mkdir(parents=True)
    (sandbox / "macos" / "Harlo.app" / "Contents" / "Info.plist").write_text(
        "this is not a plist"
    )
    proc = subprocess.run(
        ["bash", "scripts/check_signing_readiness.sh"],
        capture_output=True,
        text=True,
        cwd=sandbox,
        timeout=30,
    )
    assert proc.returncode != 0, (
        "script should have failed on a broken Info.plist but exited 0:\n"
        f"{proc.stdout}"
    )
