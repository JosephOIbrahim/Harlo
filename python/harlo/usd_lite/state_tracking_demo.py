"""SPEC P5 — customData Unchanged / Edited / New state tracking on a
multi-layer composed stage. Per-prim tag derived from prim-stack analysis,
written into a dedicated tags layer, read back from the composed view.

Layer architecture::

    p5_base.usda     role="base"     -> /Brain/P5/A.value (only here)
                                         /Brain/P5/B.value (also overridden in overlay)
    p5_overlay.usda  role="overlay"  -> /Brain/P5/B.value (overrides base)
                                         /Brain/P5/C.value (only here — new)
    p5_tags.usda     role="tags"     -> customData["state"] per /Brain/P5/* prim,
                                         derived from prim-stack analysis
    composed_p5.usda subLayerPaths = [tags, overlay, base]

Per-prim composition status:
    Unchanged  = spec only in base  (no overlay override, no overlay-only existence)
    Edited     = spec in base AND overlay
    New        = spec only in overlay  (no base existence)

The verifier (`wave1_harness.check_customdata_state_tracking`) reads each
prim's `customData["state"]` from the composed stage and asserts it matches
both (a) the expected state per construction AND (b) `compute_actual_state(prim)`
recomputed independently from the prim stack.

Not falsification-bearing — this is build-and-verify (does customData
state-tracking work as a USD mechanism, written by analysis and read by
the verifier).
"""

from __future__ import annotations

from pathlib import Path

from pxr import Sdf, Usd


# ─── Constants ─────────────────────────────────────────────────────────────

P5_ROOT = "/Brain/P5"
ATTR_VALUE = "value"

PRIM_A_PATH = f"{P5_ROOT}/A"  # Unchanged — only in base
PRIM_B_PATH = f"{P5_ROOT}/B"  # Edited — base + overlay
PRIM_C_PATH = f"{P5_ROOT}/C"  # New — only in overlay

VALUE_A_BASE = 1.0
VALUE_B_BASE = 10.0
VALUE_B_OVERLAY = 20.0
VALUE_C_OVERLAY = 30.0

STATE_KEY = "state"
STATE_UNCHANGED = "Unchanged"
STATE_EDITED = "Edited"
STATE_NEW = "New"

LAYER_ROLE_KEY = "layer_role"
ROLE_BASE = "base"
ROLE_OVERLAY = "overlay"
ROLE_TAGS = "tags"


# ─── Core: derive state from prim stack ────────────────────────────────────


def compute_actual_state(prim: Usd.Prim) -> str:
    """Inspect the prim's PrimStack and return its composition state.

    Walks the PrimSpec list, examining each spec's owning layer's
    `customLayerData["layer_role"]`. Only base / overlay roles are counted;
    the tags layer is filtered out (its presence shouldn't influence the
    state classification).

    Returns one of: ``STATE_UNCHANGED``, ``STATE_EDITED``, ``STATE_NEW``,
    or ``"Unknown"`` if neither base nor overlay role is found.
    """
    in_base = False
    in_overlay = False
    for spec in prim.GetPrimStack():
        layer = spec.layer
        meta = dict(layer.customLayerData) if layer.customLayerData else {}
        role = meta.get(LAYER_ROLE_KEY, "")
        if role == ROLE_BASE:
            in_base = True
        elif role == ROLE_OVERLAY:
            in_overlay = True
    if in_base and in_overlay:
        return STATE_EDITED
    if in_overlay and not in_base:
        return STATE_NEW
    if in_base and not in_overlay:
        return STATE_UNCHANGED
    return "Unknown"


# ─── Authoring helpers ─────────────────────────────────────────────────────


def _author_base_layer(path: Path) -> None:
    if path.exists():
        path.unlink()
    layer = Sdf.Layer.CreateNew(str(path))
    layer.customLayerData = {LAYER_ROLE_KEY: ROLE_BASE}
    stage = Usd.Stage.Open(layer)
    stage.DefinePrim("/Brain", "Scope")
    stage.DefinePrim(P5_ROOT, "Scope")
    a = stage.DefinePrim(PRIM_A_PATH, "Scope")
    a.CreateAttribute(ATTR_VALUE, Sdf.ValueTypeNames.Double).Set(VALUE_A_BASE)
    b = stage.DefinePrim(PRIM_B_PATH, "Scope")
    b.CreateAttribute(ATTR_VALUE, Sdf.ValueTypeNames.Double).Set(VALUE_B_BASE)
    layer.Save()


def _author_overlay_layer(path: Path) -> None:
    if path.exists():
        path.unlink()
    layer = Sdf.Layer.CreateNew(str(path))
    layer.customLayerData = {LAYER_ROLE_KEY: ROLE_OVERLAY}
    stage = Usd.Stage.Open(layer)
    stage.DefinePrim("/Brain", "Scope")
    stage.DefinePrim(P5_ROOT, "Scope")
    b = stage.DefinePrim(PRIM_B_PATH, "Scope")
    b.CreateAttribute(ATTR_VALUE, Sdf.ValueTypeNames.Double).Set(VALUE_B_OVERLAY)
    c = stage.DefinePrim(PRIM_C_PATH, "Scope")
    c.CreateAttribute(ATTR_VALUE, Sdf.ValueTypeNames.Double).Set(VALUE_C_OVERLAY)
    layer.Save()


def _author_composed_root(path: Path, sublayers_strongest_first: list) -> None:
    if path.exists():
        path.unlink()
    root = Sdf.Layer.CreateNew(str(path))
    for sub in sublayers_strongest_first:
        root.subLayerPaths.append(str(sub))
    root.Save()


def _author_tags_layer(
    path: Path,
    base_path: Path,
    overlay_path: Path,
    prim_paths: list[str],
) -> None:
    """Open a transient analysis stage (subLayerPaths=[overlay, base]) so the
    prim stack reflects the data layers only (no tag noise). For each prim
    path, compute its state via `compute_actual_state`. Write each tag into
    a new tags layer as `customData[STATE_KEY]` on the prim spec.

    The tags layer is then included in the composed stage's subLayerPaths
    so the verifier reads the tag through normal pxr composition.
    """
    if path.exists():
        path.unlink()
    tags_layer = Sdf.Layer.CreateNew(str(path))
    tags_layer.customLayerData = {LAYER_ROLE_KEY: ROLE_TAGS}

    # Analysis stage — base + overlay only, so prim stack reflects data layers.
    analysis_root = Sdf.Layer.CreateAnonymous(".usda")
    analysis_root.subLayerPaths.append(str(overlay_path))
    analysis_root.subLayerPaths.append(str(base_path))
    analysis_stage = Usd.Stage.Open(analysis_root)

    # Author tags onto the tags layer. Switch the edit target to tags_layer
    # so DefinePrim + SetCustomDataByKey write specs into THAT layer.
    tag_stage = Usd.Stage.Open(tags_layer)
    tag_stage.DefinePrim("/Brain", "Scope")
    tag_stage.DefinePrim(P5_ROOT, "Scope")
    for prim_path in prim_paths:
        analysis_prim = analysis_stage.GetPrimAtPath(prim_path)
        if not analysis_prim.IsValid():
            continue
        state = compute_actual_state(analysis_prim)
        tag_prim = tag_stage.DefinePrim(prim_path, "Scope")
        tag_prim.SetCustomDataByKey(STATE_KEY, state)
    tags_layer.Save()


# ─── Top-level orchestrator ────────────────────────────────────────────────


def author_p5_state_demo(base_dir) -> dict:
    """Author the P5 state-tracking scene under ``base_dir/p5_state_demo/``.

    Creates base + overlay + tags layers, plus a composed root with
    `subLayerPaths=[tags, overlay, base]`. Returns metadata for the verifier:
    paths, expected_states (per prim by construction), state_key.
    """
    base = Path(base_dir) / "p5_state_demo"
    base.mkdir(parents=True, exist_ok=True)

    base_path = base / "p5_base.usda"
    overlay_path = base / "p5_overlay.usda"
    tags_path = base / "p5_tags.usda"
    composed_path = base / "composed_p5.usda"

    _author_base_layer(base_path)
    _author_overlay_layer(overlay_path)
    _author_tags_layer(tags_path, base_path, overlay_path,
                       [PRIM_A_PATH, PRIM_B_PATH, PRIM_C_PATH])
    _author_composed_root(composed_path, [tags_path, overlay_path, base_path])

    return {
        "paths": {
            "p5_base": str(base_path),
            "p5_overlay": str(overlay_path),
            "p5_tags": str(tags_path),
            "composed_p5": str(composed_path),
        },
        "p5_root": P5_ROOT,
        "state_key": STATE_KEY,
        "expected_states": {
            PRIM_A_PATH: STATE_UNCHANGED,
            PRIM_B_PATH: STATE_EDITED,
            PRIM_C_PATH: STATE_NEW,
        },
        "expected_values": {
            PRIM_A_PATH: VALUE_A_BASE,
            PRIM_B_PATH: VALUE_B_OVERLAY,  # overlay wins
            PRIM_C_PATH: VALUE_C_OVERLAY,
        },
    }
