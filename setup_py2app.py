"""py2app build spec for Harlo.app (Phase 5A).

Run via `python setup_py2app.py py2app` (driven by the Makefile).
This script does NOT sign — `scripts/macos_sign_and_notarize.sh`
runs codesign afterwards, so we control entitlements + deep-signing
precisely.

Constraints honored:
  - Universal binary (arm64 + x86_64).
  - Plist comes from the on-disk `macos/Harlo.app/Contents/Info.plist`
    so its content (bundle ID, HealthKit usage strings) is the
    single source of truth.
  - Rust .so (`harlo.hippocampus`) is included automatically because
    it sits next to the rest of the `harlo` package.
"""

from __future__ import annotations

import plistlib
from pathlib import Path

from setuptools import setup

REPO_ROOT = Path(__file__).resolve().parent
INFO_PLIST_PATH = REPO_ROOT / "macos" / "Harlo.app" / "Contents" / "Info.plist"

with INFO_PLIST_PATH.open("rb") as fh:
    INFO_PLIST = plistlib.load(fh)

APP = ["macos/launcher.py"]  # tiny shim — see file
DATA_FILES = [
    ("config", [
        str(REPO_ROOT / "config" / "barrier_schema.json"),
        str(REPO_ROOT / "config" / "biometric_sample_schema.json"),
        str(REPO_ROOT / "config" / "intake_form_schema.json"),
        str(REPO_ROOT / "config" / "default_profile.yaml"),
        str(REPO_ROOT / "config" / "verification_depth.yaml"),
    ]),
    ("launchd", [
        str(REPO_ROOT / "macos" / "launchd" / "com.harlo.daemon.plist"),
        str(REPO_ROOT / "macos" / "launchd" / "com.harlo.agents.plist"),
    ]),
    ("scripts", [
        str(REPO_ROOT / "scripts" / "macos_install_daemon.py"),
    ]),
]

OPTIONS = {
    "argv_emulation": False,
    "plist": INFO_PLIST,
    "iconfile": None,  # design/assets/icon.icns once Claude Design delivers
    "packages": [
        "harlo",
        "jsonschema",
        "click",
        "pydantic",
        "yaml",
    ],
    "includes": [
        "harlo.hippocampus",
        "harlo.daemon.config",
        "harlo.cli.main",
        "harlo.mcp_server",
        "harlo.session.first_run",
    ],
    "excludes": [
        # py2app pulls in many things by default; keep the bundle lean.
        "tkinter",
        "matplotlib",
        "PyQt5",
        "PyQt6",
        "wx",
        "test",
        "unittest",
        "pytest",
    ],
    "arch": "universal2",
    "strip": False,
    "optimize": 0,
    # We sign in a separate step. py2app's signer is too coarse
    # for our entitlements requirements.
    "codesign_identity": None,
}

setup(
    name="Harlo",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
