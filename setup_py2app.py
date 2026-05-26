"""py2app build spec for Harlo.app (Phase 5A).

Run via `python setup_py2app.py py2app` (driven by the Makefile).
This script does NOT sign — `scripts/macos_sign_and_notarize.sh`
runs codesign afterwards, so we control entitlements + deep-signing
precisely.

Constraints honored:
  - Architecture follows the running Python interpreter. Universal2
    requires a universal2 Python install on the build machine; CI
    runners get single-arch Python from actions/setup-python, so
    forcing `arch: universal2` there fails. Set
    HARLO_PY2APP_ARCH=universal2 on a local mac with the python.org
    universal2 installer to produce a fat binary.
  - Plist comes from the on-disk `macos/Harlo.app/Contents/Info.plist`
    so its content (bundle ID, HealthKit usage strings) is the
    single source of truth.
  - Rust .so (`harlo.hippocampus`) is included automatically because
    it sits next to the rest of the `harlo` package.
"""

from __future__ import annotations

import os
import plistlib
from pathlib import Path

from setuptools import setup
from py2app.build_app import py2app as _Py2AppCommand


class HarloPy2App(_Py2AppCommand):
    """py2app command override.

    py2app 0.28+ raises ``"install_requires is no longer supported"``
    when ``distribution.install_requires`` is truthy, but setuptools 61+
    populates that attribute automatically from ``pyproject.toml``'s
    ``[project].dependencies`` block — so the check fires on every modern
    project even if setup.py itself never mentions install_requires.

    We install runtime deps in a separate step before invoking py2app
    (see the macos-build.yml workflow and the Makefile target), so the
    in-bundle dep-fetch path is unused either way. Clear the attribute
    so the check passes cleanly.
    """

    def finalize_options(self):
        # Must clear *before* super().finalize_options(), which contains
        # the offending check (build_app.py:656 in py2app 0.28).
        self.distribution.install_requires = None
        super().finalize_options()

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
        # Lean v0.1.0 bundle: the runtime default is the lexical (Rust)
        # encoder (config.ENCODER_TYPE="lexical"). The semantic path
        # (harlo.encoder.semantic_encoder / onnx_encoder) is NOT reachable
        # from any launcher mode (daemon/agents/mcp/CLI) — verified by
        # importing every entry point with these blocked. Excluding the ML
        # stack drops ~hundreds of MB and removes protobuf's C-extension,
        # which py2app trapped (unsignable) inside python312.zip and broke
        # notarization. Re-add via a [semantic] build if that path ships.
        "transformers",
        "onnxruntime",
        "xgboost",
        "sentence_transformers",
        "torch",
        "sklearn",
        "scipy",
        "google",
        "google.protobuf",
    ],
    "strip": False,
    "optimize": 0,
    # Signing is handled by scripts/macos_sign_and_notarize.sh in a
    # separate step (py2app's signer is too coarse for our entitlements
    # requirements). Omitting codesign_identity entirely — older py2app
    # versions reject the option even when set to None.
}

# Architecture: opt-in to universal2 only when explicitly requested
# (requires a universal2 Python on disk). Default: match the running
# interpreter, which is what CI runners can actually produce.
_arch = os.environ.get("HARLO_PY2APP_ARCH")
if _arch:
    OPTIONS["arch"] = _arch

# `setup_requires=["py2app"]` is deprecated in setuptools >=70 and
# breaks under PEP 517 isolation. The workflow / Makefile installs
# py2app explicitly before invoking this file, so the kwarg is
# redundant — and removing it avoids the deprecation noise.
setup(
    name="Harlo",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    cmdclass={"py2app": HarloPy2App},
)
