"""F2 — Mixed-stage TracePrim test.

Per Phase 6 design §2 + session override mandatory Crucible work.

Verifies that the C3 reader fallback path (legacy TracePrim without
`trace_id` attribute) correctly produces dict-key-consistent output
when mixed with new-format TracePrims (with `trace_id` attribute)
in the same stage.

Bypasses the writer to author both prim shapes directly via pxr.
The writer always sets `trace_id` (D17), so a "legacy" stage shape
must be authored with raw USD APIs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest


def _import_pxr_or_skip():
    try:
        import pxr  # noqa: F401
    except ImportError:
        pytest.skip("pxr not installed (substrate extra absent)")


def _import_persistence_or_skip():
    try:
        from harlo.usd_lite.persistence import read  # noqa: F401
    except ImportError as exc:
        pytest.skip(f"persistence layer unavailable: {exc}")


def test_mixed_legacy_and_new_traceprims_in_same_stage(tmp_path):
    """A stage containing both legacy (no trace_id attr) and new-format
    (with trace_id attr) TracePrims reads back with consistent dict
    keys per D17."""
    _import_pxr_or_skip()
    _import_persistence_or_skip()

    from pxr import Plug, Sdf, Usd
    # Importing the persistence package side-effects Plug.Registry
    import harlo.usd_lite.persistence as _persistence  # noqa: F401
    # The persistence layer registers the schema lazily on first
    # write/read; force registration here so DefinePrim resolves
    # the typeNames.
    schema_dir = (Path(__file__).resolve().parents[2] / "schema").resolve()
    Plug.Registry().RegisterPlugins(str(schema_dir))

    target_path = tmp_path / "mixed.usda"
    stage = Usd.Stage.CreateNew(str(target_path))

    # Authoring scaffold
    stage.DefinePrim("/Brain", "BrainStage")
    stage.DefinePrim("/Brain/Association", "AssociationPrim")
    # Traces grouping is a Scope (untyped grouping container; the
    # writer also creates this implicitly when DefinePrim recurses)
    stage.DefinePrim("/Brain/Association/Traces", "Scope")

    # ---- Legacy TracePrim (no trace_id attribute) ----
    legacy = stage.DefinePrim(
        "/Brain/Association/Traces/legacy_trace_alpha",
        "TracePrim",
    )
    legacy.CreateAttribute("content_hash", Sdf.ValueTypeNames.String).Set("legacy_hash_value")
    legacy.CreateAttribute("strength", Sdf.ValueTypeNames.Double).Set(0.5)
    legacy.CreateAttribute("last_accessed", Sdf.ValueTypeNames.Double).Set(
        datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
    )
    legacy.CreateAttribute("sdr_hex", Sdf.ValueTypeNames.String).Set("0" * 512)
    legacy.CreateAttribute("hebbian_strengthen_mask_hex", Sdf.ValueTypeNames.String).Set("0" * 512)
    legacy.CreateAttribute("hebbian_weaken_mask_hex", Sdf.ValueTypeNames.String).Set("0" * 512)
    # DELIBERATELY OMITTED: no .Set() of trace_id.
    # Note: the trace_id attribute is schema-defined on TracePrim, so
    # GetAttribute("trace_id").IsValid() returns True even without an
    # authored value. The meaningful invariant is "no authored value":
    assert not legacy.GetAttribute("trace_id").HasAuthoredValue(), (
        "test setup invariant: legacy prim should not have an authored trace_id"
    )

    # ---- New-format TracePrim (with trace_id attribute) ----
    new = stage.DefinePrim(
        "/Brain/Association/Traces/t_99deadbeef",
        "TracePrim",
    )
    new.CreateAttribute("trace_id", Sdf.ValueTypeNames.String).Set("99deadbeef")
    new.CreateAttribute("content_hash", Sdf.ValueTypeNames.String).Set("new_hash_value")
    new.CreateAttribute("strength", Sdf.ValueTypeNames.Double).Set(0.9)
    new.CreateAttribute("last_accessed", Sdf.ValueTypeNames.Double).Set(
        datetime(2026, 4, 28, tzinfo=timezone.utc).timestamp()
    )
    new.CreateAttribute("sdr_hex", Sdf.ValueTypeNames.String).Set("0" * 512)
    new.CreateAttribute("hebbian_strengthen_mask_hex", Sdf.ValueTypeNames.String).Set("0" * 512)
    new.CreateAttribute("hebbian_weaken_mask_hex", Sdf.ValueTypeNames.String).Set("0" * 512)

    stage.GetRootLayer().Save()

    # ---- Read back via persistence layer ----
    from harlo.usd_lite.persistence import read
    bs = read(str(target_path))

    traces = bs.association.traces
    assert len(traces) == 2, f"expected 2 traces, got {len(traces)}: {list(traces)}"

    # Legacy: dict key = prim name (fallback path)
    assert "legacy_trace_alpha" in traces, (
        f"legacy fallback failed; keys = {sorted(traces)}"
    )
    legacy_trace = traces["legacy_trace_alpha"]
    assert legacy_trace.trace_id == "legacy_trace_alpha", (
        "fallback path must set trace_id field to the prim name"
    )
    assert legacy_trace.content_hash == "legacy_hash_value"
    assert legacy_trace.strength == pytest.approx(0.5)

    # New: dict key = canonical trace_id (attribute path)
    assert "99deadbeef" in traces, (
        f"new-format attribute path failed; keys = {sorted(traces)}"
    )
    new_trace = traces["99deadbeef"]
    assert new_trace.trace_id == "99deadbeef", (
        "new-format must use trace_id attribute, not sanitized prim name"
    )
    assert new_trace.content_hash == "new_hash_value"
    assert new_trace.strength == pytest.approx(0.9)

    # Adversarial: the sanitized prim name `t_99deadbeef` must NOT
    # appear as a dict key (would indicate the reader leaked the
    # presentation form into the canonical layer)
    assert "t_99deadbeef" not in traces, (
        "reader leaked sanitized prim name as dict key"
    )


def test_legacy_only_stage_falls_back_for_all_traces(tmp_path):
    """A stage with no trace_id attributes anywhere uses prim-name
    fallback for every TracePrim. Pre-C3 stages must remain readable."""
    _import_pxr_or_skip()
    _import_persistence_or_skip()

    from pxr import Plug, Sdf, Usd
    import harlo.usd_lite.persistence as _persistence  # noqa: F401
    schema_dir = (Path(__file__).resolve().parents[2] / "schema").resolve()
    Plug.Registry().RegisterPlugins(str(schema_dir))

    target_path = tmp_path / "legacy_only.usda"
    stage = Usd.Stage.CreateNew(str(target_path))
    stage.DefinePrim("/Brain", "BrainStage")
    stage.DefinePrim("/Brain/Association", "AssociationPrim")
    stage.DefinePrim("/Brain/Association/Traces", "Scope")

    for name in ("alpha_trace", "beta_trace", "gamma_trace"):
        prim = stage.DefinePrim(f"/Brain/Association/Traces/{name}", "TracePrim")
        prim.CreateAttribute("content_hash", Sdf.ValueTypeNames.String).Set(f"{name}_hash")
        prim.CreateAttribute("strength", Sdf.ValueTypeNames.Double).Set(0.0)
        prim.CreateAttribute("last_accessed", Sdf.ValueTypeNames.Double).Set(0.0)
        prim.CreateAttribute("sdr_hex", Sdf.ValueTypeNames.String).Set("0" * 512)
        prim.CreateAttribute("hebbian_strengthen_mask_hex", Sdf.ValueTypeNames.String).Set("0" * 512)
        prim.CreateAttribute("hebbian_weaken_mask_hex", Sdf.ValueTypeNames.String).Set("0" * 512)

    stage.GetRootLayer().Save()

    from harlo.usd_lite.persistence import read
    bs = read(str(target_path))
    assert set(bs.association.traces) == {"alpha_trace", "beta_trace", "gamma_trace"}
    for k, v in bs.association.traces.items():
        assert v.trace_id == k, f"fallback consistency: dict key {k} != trace.trace_id {v.trace_id}"
