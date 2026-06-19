"""SPEC §F2 anchor structural-immunity follow-up — are anchor sections
(CONSTITUTIONAL / SAFETY / CONSENT / KNOWLEDGE) STRUCTURALLY immune to
injection on the live stage? Not parametrically protected by convention,
but unreachable by composition mechanics — even by a delta that
explicitly authors an opinion on an anchor path.

Layer architecture::

    anchor_layer.usda   role="anchor"  -> /Brain/Anchors/{CONSTITUTIONAL,
                                            SAFETY, CONSENT, KNOWLEDGE}.value
    base_layer.usda     role="base"    -> /Brain/Cognitive/{...}.value defaults
    delta_<X>.usda      role="delta"   -> /Brain/Cognitive/* per profile X
    delta_adversarial   role="delta"   -> normal modulation PLUS an attack opinion
                                          on /Brain/Anchors/CONSTITUTIONAL.value
    composed_<X>.usda   subLayerPaths = [anchor, delta_X, base]
                          ^ anchor at position 0 → strongest in USD composition
                            delta beats base for non-anchor prims (delta position 1)
                            anchor beats delta for anchor prims (anchor position 0)

The structural mechanism: USD's subLayerPaths gives the FRONT layer the
strongest opinion. Putting anchor_layer at position 0 means any opinion in
anchor_layer wins against any opinion in subsequent sublayers — including
the adversarial delta's attempt to overwrite an anchor path.

The verifier (`wave1_harness.check_anchor_immunity`) asserts:
  - For ALL profiles (incl. adversarial): `hash_anchor_subtree(composed_X)`
    equals `clean_anchor_hash` (computed against composed_clean = anchor+base).
  - Non-anchor hashes DIFFER across modulating profiles (Default/Stress/Rest)
    — proof the deltas are non-vacuous.
  - The adversarial layer ACTUALLY authored its attack opinion (the load-
    bearing probe — without this, the test could "pass" by trivially
    skipping the adversarial scenario).
  - The composed_adversarial resolves the targeted anchor to its CLEAN value,
    NOT the adversarial value — the attack was made but had ZERO effect.
    THIS is what distinguishes structural immunity from parametric protection.

Per architect: faking immunity (post-resolution elevation, special-casing
the verifier) is the one unacceptable outcome. The harness's job is to
report pxr's actual resolution at every step.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from pxr import Sdf, Usd


# ─── Demo constants ────────────────────────────────────────────────────────

ANCHOR_NAMES = ["CONSTITUTIONAL", "SAFETY", "CONSENT", "KNOWLEDGE"]
ANCHOR_VALUES = {
    "CONSTITUTIONAL": "constitutional_baseline",
    "SAFETY": "safety_baseline",
    "CONSENT": "consent_baseline",
    "KNOWLEDGE": "knowledge_baseline",
}

ANCHOR_ROOT = "/Brain/Anchors"
NONANCHOR_ROOT = "/Brain/Cognitive"
ATTR_VALUE = "value"

# Modulating + adversarial profiles. Each maps a non-anchor path segment
# (under NONANCHOR_ROOT) to the value that profile authors there.
PROFILES = {
    "default": {"AttentionThreshold": 0.5, "Mode": "baseline_focus"},
    "stress":  {"AttentionThreshold": 0.8, "Mode": "elevated_alert"},
    "rest":    {"AttentionThreshold": 0.3, "Mode": "low_load"},
    # Adversarial: same non-anchor modulation as default (so the *only*
    # difference vs default is the attack itself) — this isolates the
    # adversarial signal cleanly.
    "adversarial": {"AttentionThreshold": 0.5, "Mode": "baseline_focus"},
}

ADVERSARIAL_ATTACK_TARGET = "/Brain/Anchors/CONSTITUTIONAL"
ADVERSARIAL_ATTACK_VALUE = "MALICIOUS_OVERRIDE"

LAYER_ROLE_KEY = "layer_role"
ROLE_ANCHOR = "anchor"
ROLE_BASE = "base"
ROLE_DELTA = "delta"


# ─── Core: hash resolved subtree state ─────────────────────────────────────


def _walk_subtree_resolved(stage: Usd.Stage, root_path: str) -> list[str]:
    """Return sorted ``"path = repr(value)"`` rows for every attribute under
    ``root_path`` on the composed stage. The values are pxr's RESOLVED
    values (`attr.Get()`), so the rows reflect the LIVE composition."""
    rows: list[str] = []
    root_prim = stage.GetPrimAtPath(root_path)
    if not root_prim.IsValid():
        return rows
    for prim in Usd.PrimRange(root_prim):
        for attr in prim.GetAttributes():
            val = attr.Get()
            rows.append(f"{attr.GetPath()} = {val!r}")
    rows.sort()
    return rows


def hash_subtree(stage: Usd.Stage, root_path: str) -> str:
    """SHA256 of the canonical resolved-state of a prim subtree."""
    canonical = "\n".join(_walk_subtree_resolved(stage, root_path))
    return hashlib.sha256(canonical.encode()).hexdigest()


def hash_anchor_subtree(stage: Usd.Stage) -> str:
    """SHA256 of the resolved state of /Brain/Anchors/ on this stage."""
    return hash_subtree(stage, ANCHOR_ROOT)


def hash_nonanchor_subtree(stage: Usd.Stage) -> str:
    """SHA256 of the resolved state of /Brain/Cognitive/ on this stage."""
    return hash_subtree(stage, NONANCHOR_ROOT)


# ─── Authoring helpers ─────────────────────────────────────────────────────


def _author_anchor_layer(path: Path) -> None:
    """Create the anchor layer with all 4 anchor prims at their baseline values."""
    if path.exists():
        path.unlink()
    layer = Sdf.Layer.CreateNew(str(path))
    layer.customLayerData = {LAYER_ROLE_KEY: ROLE_ANCHOR}
    stage = Usd.Stage.Open(layer)
    stage.DefinePrim("/Brain", "Scope")
    stage.DefinePrim(ANCHOR_ROOT, "Scope")
    for name in ANCHOR_NAMES:
        prim = stage.DefinePrim(f"{ANCHOR_ROOT}/{name}", "Scope")
        prim.CreateAttribute(
            ATTR_VALUE, Sdf.ValueTypeNames.String
        ).Set(ANCHOR_VALUES[name])
    layer.Save()


def _author_base_layer(path: Path) -> None:
    """Create the base layer with non-anchor clean defaults."""
    if path.exists():
        path.unlink()
    layer = Sdf.Layer.CreateNew(str(path))
    layer.customLayerData = {LAYER_ROLE_KEY: ROLE_BASE}
    stage = Usd.Stage.Open(layer)
    stage.DefinePrim("/Brain", "Scope")
    stage.DefinePrim(NONANCHOR_ROOT, "Scope")
    at = stage.DefinePrim(f"{NONANCHOR_ROOT}/AttentionThreshold", "Scope")
    at.CreateAttribute(ATTR_VALUE, Sdf.ValueTypeNames.Double).Set(0.5)
    md = stage.DefinePrim(f"{NONANCHOR_ROOT}/Mode", "Scope")
    md.CreateAttribute(ATTR_VALUE, Sdf.ValueTypeNames.String).Set("baseline_focus")
    layer.Save()


def _author_delta_layer(
    path: Path,
    profile_name: str,
    opinions: dict,
    attacks_anchor: bool,
) -> None:
    """Author a delta layer with non-anchor modulation. If ``attacks_anchor``,
    ALSO author an opinion on ADVERSARIAL_ATTACK_TARGET — the load-bearing
    probe that pxr's composition must structurally reject."""
    if path.exists():
        path.unlink()
    layer = Sdf.Layer.CreateNew(str(path))
    layer.customLayerData = {LAYER_ROLE_KEY: ROLE_DELTA, "profile": profile_name}
    stage = Usd.Stage.Open(layer)
    stage.DefinePrim("/Brain", "Scope")
    stage.DefinePrim(NONANCHOR_ROOT, "Scope")
    for path_seg, value in opinions.items():
        prim = stage.DefinePrim(f"{NONANCHOR_ROOT}/{path_seg}", "Scope")
        type_name = (Sdf.ValueTypeNames.Double if isinstance(value, float)
                     else Sdf.ValueTypeNames.String)
        prim.CreateAttribute(ATTR_VALUE, type_name).Set(value)
    if attacks_anchor:
        # Define the path hierarchy so the attack opinion is authored on a
        # real prim spec — pxr's composition then has both anchor_layer's
        # opinion (position 0) and this delta's opinion (position 1) to
        # resolve. Structural immunity: position 0 wins.
        stage.DefinePrim("/Brain", "Scope")
        stage.DefinePrim(ANCHOR_ROOT, "Scope")
        adv_prim = stage.DefinePrim(ADVERSARIAL_ATTACK_TARGET, "Scope")
        adv_prim.CreateAttribute(
            ATTR_VALUE, Sdf.ValueTypeNames.String
        ).Set(ADVERSARIAL_ATTACK_VALUE)
    layer.Save()


def _author_composed_root(path: Path, sublayers_strongest_first: list) -> None:
    """Create a root layer with subLayerPaths in strongest-first order
    (USD: the layer at the front of subLayerPaths is the strongest)."""
    if path.exists():
        path.unlink()
    root = Sdf.Layer.CreateNew(str(path))
    for sub in sublayers_strongest_first:
        root.subLayerPaths.append(str(sub))
    root.Save()


# ─── Top-level: author the scene + compute reference clean_anchor_hash ─────


def author_anchor_immunity_demo(base_dir) -> dict:
    """Author the Cycle 4 anchor-immunity scene under ``base_dir/anchor_demo/``.

    Returns a dict with: paths (anchor/base/deltas/composed_clean/
    composed_profiles), anchor_root, nonanchor_root, anchor_names,
    anchor_clean_values, clean_anchor_hash (reference computed on the
    clean composed stage, same hashing path the verifier uses),
    adversarial_attack_target / attr / value, profiles list.
    """
    base = Path(base_dir) / "anchor_demo"
    base.mkdir(parents=True, exist_ok=True)

    anchor_path = base / "anchor_layer.usda"
    base_path = base / "base_layer.usda"

    _author_anchor_layer(anchor_path)
    _author_base_layer(base_path)

    delta_paths: dict[str, str] = {}
    composed_paths: dict[str, str] = {}
    for profile_name, opinions in PROFILES.items():
        delta_path = base / f"delta_{profile_name}.usda"
        attacks = (profile_name == "adversarial")
        _author_delta_layer(delta_path, profile_name, opinions, attacks_anchor=attacks)
        delta_paths[profile_name] = str(delta_path)

        composed_path = base / f"composed_{profile_name}.usda"
        _author_composed_root(composed_path, [anchor_path, delta_path, base_path])
        composed_paths[profile_name] = str(composed_path)

    # Clean composed (no delta) — reference for clean_anchor_hash
    composed_clean_path = base / "composed_clean.usda"
    _author_composed_root(composed_clean_path, [anchor_path, base_path])
    clean_stage = Usd.Stage.Open(str(composed_clean_path))
    clean_anchor_hash = hash_anchor_subtree(clean_stage)

    return {
        "paths": {
            "anchor_layer": str(anchor_path),
            "base_layer": str(base_path),
            "composed_clean": str(composed_clean_path),
            "deltas": delta_paths,
            "composed_profiles": composed_paths,
        },
        "anchor_root": ANCHOR_ROOT,
        "nonanchor_root": NONANCHOR_ROOT,
        "anchor_names": ANCHOR_NAMES,
        "anchor_clean_values": dict(ANCHOR_VALUES),
        "clean_anchor_hash": clean_anchor_hash,
        "adversarial_attack_target": ADVERSARIAL_ATTACK_TARGET,
        "adversarial_attack_attr": ATTR_VALUE,
        "adversarial_attack_value": ADVERSARIAL_ATTACK_VALUE,
        "profiles": list(PROFILES.keys()),
    }
