"""Subprocess-isolated SchemaRegistry gate test.

Per Constitution Commandment 4: validation runs in a fresh subprocess
to catch plugin-load failures that would silently succeed in the
parent's polluted process state.

Per Phase 1 design §8.1 + Phase 2 implementation plan §5.2.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


HARLO_TYPENAMES = [
    # Abstract bases
    "HarloPrim",
    "HarloContainer",
    # Concrete containers
    "BrainStage",
    "AssociationPrim",
    "CompositionPrim",
    "ElenchusPrim",
    "InquiryContainerPrim",
    "MotorContainerPrim",
    "SkillsContainerPrim",
    "CognitiveProfilePrim",
    # Concrete typed leaves
    "TracePrim",
    "CompositionLayerPrim",
    "GateStatusPrim",
    "MerkleRootPrim",
    "SessionPrim",
    "InquiryPrim",
    "MotorPrim",
    "SkillPrim",
    "MultipliersPrim",
    "IntakeHistoryPrim",
    # Applied API schema (D10)
    "Provenance",
]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_DIR = _REPO_ROOT / "schema"


def _import_pxr_or_skip():
    try:
        import pxr  # noqa: F401
    except ImportError:
        pytest.skip("pxr not installed (substrate extra absent)")


def test_schema_registry_loads_all_harlo_types_in_subprocess():
    """All 21 typeNames register and resolve in a fresh subprocess.

    Negative checks:
    - Moneta's MonetaMemory is NOT visible (would indicate cross-plugin
      contamination).
    - USD built-in `Xform` is still resolvable (no registry corruption).
    """
    _import_pxr_or_skip()

    code = f"""
import sys, os
from pxr import Plug, Usd

reg = Plug.Registry()
reg.RegisterPlugins({str(_SCHEMA_DIR)!r})

schema_reg = Usd.SchemaRegistry()

expected = {HARLO_TYPENAMES!r}
missing = []
for typename in expected:
    if not schema_reg.GetTypeFromName(typename):
        missing.append(typename)

if missing:
    print('MISSING:', missing)
    sys.exit(1)

# Negative: no Moneta typeName collision in our registry view
if schema_reg.GetTypeFromName('MonetaMemory'):
    print('UNEXPECTED MonetaMemory in registry')
    sys.exit(2)

# USD built-in still resolvable (registry not corrupted)
if not schema_reg.GetTypeFromName('Xform'):
    print('USD built-in Xform not resolvable - registry corrupted')
    sys.exit(3)

print('OK')
sys.exit(0)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"Schema registry subprocess failed:\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "OK" in result.stdout


def test_no_runtime_tier_pxr_import():
    """Importing harlo.usd_lite (parent) must NOT pull in pxr.

    Constitution Law 3 / 4: pxr stays optional and never on the
    runtime read path. Persistence layer is the only pxr-importing
    submodule.
    """
    code = """
import sys
import harlo.usd_lite  # noqa: F401
assert 'pxr' not in sys.modules, 'pxr was imported transitively from harlo.usd_lite'
print('OK')
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Runtime-tier pxr-import test failed:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "OK" in result.stdout
