"""SPEC §F2 thesis test — does reconstruct_clean() as "flatten-to-base"
recover the clean baseline BIT-IDENTICALLY from a composed (clean + delta)
stage?

The cognitive mapping (architect's framing):
    CLEAN baseline = immutable pre-injection signal
    DELTA overlay  = injection residual (alpha * delta)
    composed view  = clean + delta applied (the modulated state)
    reconstruct_clean(stage) = structurally isolate the base from the delta,
                               returning the canonical clean representation

This module:
  - Authors 4 .usda files: a clean baseline (tagged `layer_role="base"`),
    a delta overlay (tagged `layer_role="delta"`), a composed root with
    `subLayerPaths=[delta, clean]` (delta strongest, composed view = delta-
    modulated), and a clean-only composed root for the reference clean_hash.
  - Provides `reconstruct_clean(composed_stage_path)` — filters sublayers by
    customLayerData tag, builds a transient anon root with only the base
    sublayers, returns `Stage.Flatten().ExportToString()` — the canonical
    serialization.

The verifier (`wave1_harness.check_structural_lossless`) compares the
SHA256 of `reconstruct_clean(composed_with_delta)` against the reference
clean_hash (computed by `reconstruct_clean(composed_clean_only)` — same
serialization path on both sides → apples vs apples for bit-identity).

Per architect: §F2 firing is SUCCESS (loop exit), not failure. DO NOT
massage the comparison (loosen the hash, fall back to float-tol, post-
patch the recovered layer). Faking the lossless guarantee is the one
unacceptable outcome.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from pxr import Sdf, Usd


# ─── Demo constants ────────────────────────────────────────────────────────

CLEAN_BASELINE_NAME = "clean_baseline.usda"
DELTA_OVERLAY_NAME = "delta_overlay.usda"
COMPOSED_WITH_DELTA_NAME = "composed_with_delta.usda"
COMPOSED_CLEAN_ONLY_NAME = "composed_clean_only.usda"

SIGNAL_PRIM_PATH = "/Brain/LosslessDemo/Signal"
SIGNAL_ATTR_NAME = "value"

# Numeric signal so the test surfaces float bit-identity issues honestly
# (a string would mask such failures). The values map to:
#   clean   = pre-injection baseline
#   delta   = injection residual (alpha * delta = 0.2 here)
#   modulated = clean + delta
CLEAN_VALUE = 0.5
DELTA_MODULATED_VALUE = 0.7

LAYER_ROLE_KEY = "layer_role"
ROLE_BASE = "base"
ROLE_DELTA = "delta"


# ─── Core: reconstruct_clean() ─────────────────────────────────────────────


def reconstruct_clean(composed_stage_path: str) -> str:
    """Structurally recover the clean baseline from a composed stage.

    Opens the composed stage, inspects each sublayer's
    `customLayerData[LAYER_ROLE_KEY]`, includes only those tagged
    ``"base"``, and returns ``Stage.Flatten().ExportToString()`` on a
    transient anonymous root that holds only those base sublayers.

    The returned string is the canonical USD ASCII serialization of the
    flattened clean state — suitable for SHA256-based bit-identity tests.

    Raises:
        RuntimeError: if the stage can't be opened or no base sublayers
            are found.
    """
    composed = Usd.Stage.Open(composed_stage_path)
    if composed is None:
        raise RuntimeError(f"Stage.Open returned None for {composed_stage_path}")

    root = composed.GetRootLayer()
    base_paths: list[str] = []
    for sub_path in root.subLayerPaths:
        sub = Sdf.Layer.FindOrOpen(sub_path)
        if sub is None:
            continue
        meta = dict(sub.customLayerData) if sub.customLayerData else {}
        role = meta.get(LAYER_ROLE_KEY, "")
        if role == ROLE_BASE:
            base_paths.append(sub_path)

    if not base_paths:
        raise RuntimeError(
            f"reconstruct_clean: no sublayers tagged "
            f"customLayerData[{LAYER_ROLE_KEY!r}]=={ROLE_BASE!r} in "
            f"{composed_stage_path}"
        )

    anon_root = Sdf.Layer.CreateAnonymous(".usda")
    for p in base_paths:
        anon_root.subLayerPaths.append(p)
    stage = Usd.Stage.Open(anon_root)
    return stage.Flatten().ExportToString()


# ─── Authoring helpers ─────────────────────────────────────────────────────


def _author_signal_layer(path: Path, layer_role: str, signal_value: float) -> None:
    """Create a sublayer at `path` with the signal attribute authored on
    `/Brain/LosslessDemo/Signal` and `customLayerData[layer_role]` set."""
    if path.exists():
        path.unlink()
    layer = Sdf.Layer.CreateNew(str(path))
    # Tag the layer's role before authoring prims (metadata set on the layer,
    # not on any prim — survives ExportToString flattening as layer metadata).
    layer.customLayerData = {LAYER_ROLE_KEY: layer_role}

    stage = Usd.Stage.Open(layer)
    stage.DefinePrim("/Brain", "Scope")
    stage.DefinePrim("/Brain/LosslessDemo", "Scope")
    sig = stage.DefinePrim(SIGNAL_PRIM_PATH, "Scope")
    sig.CreateAttribute(
        SIGNAL_ATTR_NAME, Sdf.ValueTypeNames.Double
    ).Set(float(signal_value))
    layer.Save()


def _author_composed_root(path: Path, sublayers_strongest_first: list[Path]) -> None:
    """Create a root layer at `path` with subLayerPaths in strongest-first
    order (USD convention: the layer at the FRONT of subLayerPaths is the
    strongest)."""
    if path.exists():
        path.unlink()
    root = Sdf.Layer.CreateNew(str(path))
    for sub in sublayers_strongest_first:
        root.subLayerPaths.append(str(sub))
    root.Save()


# ─── Top-level: author + reference hash ────────────────────────────────────


def author_lossless_demo(base_dir) -> dict:
    """Author the §F2 thesis-test scene under ``base_dir/lossless_demo/``.

    Creates 4 .usda files (fresh each call) and computes the reference
    ``clean_hash`` via the same ``reconstruct_clean`` path the verifier
    will use — guaranteeing apples-vs-apples for SHA256 bit-identity.

    Returns a dict with: paths, clean_value, delta_modulated_value,
    delta_magnitude, composed_view_value (proof the composed stage with
    delta deviates from clean), clean_hash, signal_attr, signal_prim.
    """
    base = Path(base_dir) / "lossless_demo"
    base.mkdir(parents=True, exist_ok=True)

    clean_path = base / CLEAN_BASELINE_NAME
    delta_path = base / DELTA_OVERLAY_NAME
    composed_delta_path = base / COMPOSED_WITH_DELTA_NAME
    composed_clean_path = base / COMPOSED_CLEAN_ONLY_NAME

    # Author the two leaf layers.
    _author_signal_layer(clean_path, ROLE_BASE, CLEAN_VALUE)
    _author_signal_layer(delta_path, ROLE_DELTA, DELTA_MODULATED_VALUE)

    # composed_with_delta: delta strongest, clean weakest. Composed view
    # resolves to DELTA_MODULATED_VALUE.
    _author_composed_root(composed_delta_path, [delta_path, clean_path])

    # composed_clean_only: just the clean sublayer. Used for the reference
    # clean_hash via the SAME reconstruct_clean path the verifier uses.
    _author_composed_root(composed_clean_path, [clean_path])

    # Reference clean_hash — feed clean-only through reconstruct_clean so
    # both sides of the comparison traverse the identical serialization.
    clean_canonical = reconstruct_clean(str(composed_clean_path))
    clean_hash = hashlib.sha256(clean_canonical.encode()).hexdigest()

    # Proof the delta is non-empty: read the composed-with-delta view.
    composed_stage = Usd.Stage.Open(str(composed_delta_path))
    composed_view = (composed_stage.GetPrimAtPath(SIGNAL_PRIM_PATH)
                     .GetAttribute(SIGNAL_ATTR_NAME).Get())

    return {
        "paths": {
            "clean_baseline": str(clean_path),
            "delta_overlay": str(delta_path),
            "composed_with_delta": str(composed_delta_path),
            "composed_clean_only": str(composed_clean_path),
        },
        "signal_prim": SIGNAL_PRIM_PATH,
        "signal_attr": SIGNAL_ATTR_NAME,
        "clean_value": CLEAN_VALUE,
        "delta_modulated_value": DELTA_MODULATED_VALUE,
        "delta_magnitude": abs(DELTA_MODULATED_VALUE - CLEAN_VALUE),
        "composed_view_value": composed_view,  # should equal DELTA_MODULATED_VALUE
        "clean_hash": clean_hash,
    }
