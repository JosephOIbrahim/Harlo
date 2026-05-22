"""Locked-in regressions for the WS1 path-relocation completion +
the `harlo compose` IPC handler crash bug.

Two threads:

1. `MerkleStage.save()` previously wrote to a hardcoded `data/stages`,
   which leaked the user's CWD into a location the daemon config
   does not own. Today `save()` resolves through `daemon.config.STAGES_DIR`
   so HARLO_DATA_DIR honors macOS / dev / XDG defaults.

2. `_handle_compose` constructed `Layer(data=..., arc_type=...)` while
   `Layer` requires (arc_type, data, source, timestamp, layer_id).
   That made `harlo compose` raise TypeError at runtime. This test
   exercises the round-trip end to end through the IPC entry point.

3. `composition.audit.{log_resolution, read_audit, read_audit_for_stage}`
   used a hardcoded `data/audit.log`. Now resolved via daemon.config.

4. `brainstem.consolidation._REFLEX_DIR` used a hardcoded `data/reflexes`.
   Now imports from daemon.config; the old name is preserved so
   existing `monkeypatch.setattr(consolidation, "_REFLEX_DIR", …)`
   tests still work.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def isolated_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("HARLO_DATA_DIR", str(tmp_path / "data"))
    import harlo.daemon.config as cfg

    importlib.reload(cfg)
    # Reload modules that import from daemon.config at module load.
    import harlo.brainstem.consolidation as consolidation

    importlib.reload(consolidation)
    return tmp_path / "data"


def test_merkle_stage_save_honors_harlo_data_dir(isolated_data_dir):
    """Before the fix: MerkleStage.save() wrote to `data/stages` next
    to CWD. After: it writes under HARLO_DATA_DIR/stages."""
    import harlo.composition.stage as stage_mod
    from harlo.composition.layer import ArcType, Layer

    importlib.reload(stage_mod)

    stage = stage_mod.MerkleStage(stage_id="leak-test")
    stage.add_layer(
        Layer(
            arc_type=ArcType.LOCAL,
            data={"k": "v"},
            source="test",
            timestamp=0,
            layer_id="l1",
        )
    )
    written = stage.save()
    assert written.is_file()
    # The path must sit under the isolated DATA_DIR, NOT under
    # `data/stages` relative to CWD.
    assert str(isolated_data_dir) in str(written.parent), written


def test_merkle_stage_load_honors_harlo_data_dir(isolated_data_dir):
    import harlo.composition.stage as stage_mod
    from harlo.composition.layer import ArcType, Layer

    importlib.reload(stage_mod)

    s = stage_mod.MerkleStage(stage_id="load-test")
    s.add_layer(
        Layer(
            arc_type=ArcType.LOCAL,
            data={"k": "v"},
            source="t",
            timestamp=0,
            layer_id="l1",
        )
    )
    s.save()

    loaded = stage_mod.MerkleStage.load("load-test")
    assert loaded.stage_id == "load-test"
    assert len(loaded.get_layers()) == 1


def test_composition_audit_writes_to_data_dir_log(isolated_data_dir):
    from harlo.composition import audit as audit_mod
    from harlo.composition.resolver import Resolution

    importlib.reload(audit_mod)

    res = Resolution(
        merkle_root="abc123",
        outcome={"resolved": "ok"},
        trace=[],
        gvr_state={"state": "verified"},
    )
    entry_id = audit_mod.log_resolution(res, stage_id="audit-test")
    assert entry_id

    found = audit_mod.read_audit(entry_id)
    assert found is not None
    assert found["stage_id"] == "audit-test"

    # The log file should sit under the isolated DATA_DIR.
    assert str(isolated_data_dir) in str(audit_mod.AUDIT_LOG)
    assert audit_mod.AUDIT_LOG.is_file()


def test_brainstem_reflex_dir_honors_harlo_data_dir(isolated_data_dir):
    import harlo.brainstem.consolidation as consolidation

    importlib.reload(consolidation)
    # Default _REFLEX_DIR should resolve under the isolated data dir.
    assert str(isolated_data_dir) in str(consolidation._REFLEX_DIR)


def test_brainstem_reflex_dir_still_monkeypatchable(isolated_data_dir, tmp_path):
    """Existing tests use monkeypatch.setattr to redirect _REFLEX_DIR.
    The fix must not break that — preserve the module-level
    mutable attribute under its historical name."""
    import harlo.brainstem.consolidation as consolidation

    importlib.reload(consolidation)
    target = tmp_path / "override-reflexes"
    consolidation._REFLEX_DIR = target
    consolidation._ensure_reflex_dir()
    assert target.is_dir()


# -----------------------------------------------------------------
# _handle_compose round-trip
# -----------------------------------------------------------------


def test_handle_compose_round_trip(isolated_data_dir):
    """`harlo compose` previously crashed because Layer() was called
    without required source/timestamp/layer_id. This test exercises
    the full IPC entry point and asserts a clean response shape."""
    import harlo.daemon.router as router

    importlib.reload(router)

    resp = router.route_command(
        "compose",
        {
            "stage_id": "compose-roundtrip",
            "arc_type": "LOCAL",
            "layer_data": {"hello": "world"},
            "source": "regression-test",
        },
    )
    assert resp["status"] == "ok", resp
    result = resp["result"]
    assert result["layer_count"] == 1
    assert result["layer_id"]
    assert result["merkle_root"]

    # Second call adds another layer, no crash on `len(stage.layers)`.
    resp2 = router.route_command(
        "compose",
        {
            "stage_id": "compose-roundtrip",
            "arc_type": 2,  # numeric arc_type also accepted
            "layer_data": {"another": "layer"},
        },
    )
    assert resp2["status"] == "ok", resp2
    assert resp2["result"]["layer_count"] == 2


def test_handle_compose_rejects_unknown_arc_type(isolated_data_dir):
    import harlo.daemon.router as router

    importlib.reload(router)
    resp = router.route_command(
        "compose",
        {
            "stage_id": "bad-arc",
            "arc_type": "NOT_A_REAL_ARC",
            "layer_data": {},
        },
    )
    assert resp["status"] == "error"
    assert "arc_type" in resp["message"].lower()


def test_handle_compose_requires_stage_and_arc(isolated_data_dir):
    import harlo.daemon.router as router

    importlib.reload(router)
    r1 = router.route_command("compose", {"arc_type": "LOCAL"})
    r2 = router.route_command("compose", {"stage_id": "x"})
    assert r1["status"] == "error" and "stage_id" in r1["message"]
    assert r2["status"] == "error" and "arc_type" in r2["message"]
