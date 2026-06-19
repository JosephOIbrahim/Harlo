"""LIVRPS thesis test: SPEC §F1 — does pxr's native composition resolve
cognitive priority L > V > S on the live `real_usd` stage?

Authors three sibling test prims under `/Brain/CompositionDemo/` on a fresh
USD stage, each with a different combination of native composition arcs:

    L_wins  : LOCAL  + VARIANT + SPECIALIZE   -> expect pxr to resolve to LOCAL
    V_wins  : VARIANT + SPECIALIZE            -> expect VARIANT
    S_wins  : SPECIALIZE                      -> expect SPECIALIZE

The verifier (`wave1_harness.check_native_composition`) opens this stage in a
cold `pxr.Usd.Stage.Open` from its own process and reads `attr.Get()`. That
call exercises pxr's REAL composition engine — no Python IntEnum proxy. If
pxr's resolution does not match LIVRPS strength order at any tier, SPEC §F1
("LIVRPS strength order can't resolve cognitive priority without fighting USD
semantics") has fired honestly.

Per architect: §F1 firing is a SUCCESS (loop exit), not a code defect. This
module MUST NOT bolt on post-resolution overrides to force the verifier
green. Faking the thesis is the one unacceptable outcome.

Cognitive mapping (architect's framing):
    LOCAL       = today's-override (strongest)
    VARIANT     = context-mode (middle)
    SPECIALIZE  = constitutional base (weakest)
"""

from __future__ import annotations

from pathlib import Path

from pxr import Sdf, Usd


ATTR_NAME = "current_mode"

VALUE_LOCAL = "override_today"
VALUE_VARIANT = "morning_mode"
VALUE_SPECIALIZE = "constitutional_base"

ROOT_PATH = "/Brain/CompositionDemo"
BASE_PATH = f"{ROOT_PATH}/_constitutional_base"
L_WINS_PATH = f"{ROOT_PATH}/L_wins"
V_WINS_PATH = f"{ROOT_PATH}/V_wins"
S_WINS_PATH = f"{ROOT_PATH}/S_wins"

VARIANT_SET_NAME = "context_mode"
VARIANT_NAME = "morning"


def _add_specialize(prim: Usd.Prim, base_path: str) -> None:
    """Add a Specializes composition arc from prim to base_path."""
    prim.GetSpecializes().AddSpecialize(Sdf.Path(base_path))


def _add_variant_opinion(prim: Usd.Prim, value: str) -> None:
    """Add a context_mode variant set on prim, select `morning`, author the
    attribute inside the variant edit context (so the opinion is contributed
    via the VARIANT arc, not as a local opinion on the prim itself).
    """
    vset = prim.GetVariantSets().AddVariantSet(VARIANT_SET_NAME)
    vset.AddVariant(VARIANT_NAME)
    vset.SetVariantSelection(VARIANT_NAME)
    with vset.GetVariantEditContext():
        prim.CreateAttribute(ATTR_NAME, Sdf.ValueTypeNames.String).Set(value)


def _add_local_opinion(prim: Usd.Prim, value: str) -> None:
    """Author a LOCAL opinion on the prim in the current (root layer) edit
    target — the strongest LIVRPS arc.
    """
    prim.CreateAttribute(ATTR_NAME, Sdf.ValueTypeNames.String).Set(value)


def author_native_composition_demo(stage_path: str) -> dict:
    """Author the §F1 thesis-test scene to a fresh USD .usda at stage_path.

    Returns a dict describing each scenario so the verifier can cross-check
    its assertions against what was authored (no telepathy).

    Args:
        stage_path: Absolute path to the .usda file to (re)create.

    Returns:
        ``{path, attribute, scenarios: [{path, arcs, expected_winner,
        expected_value}, ...]}``.
    """
    path = Path(stage_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Fresh stage each call — RED-then-GREEN reproducibility, no stale state.
    if path.exists():
        path.unlink()

    stage = Usd.Stage.CreateNew(str(path))
    stage.DefinePrim("/Brain", "Scope")
    stage.DefinePrim(ROOT_PATH, "Scope")

    # Constitutional base — the SPECIALIZE source. Carries the attribute at
    # the weakest tier; any prim that AddSpecialize's this path inherits it.
    base = stage.DefinePrim(BASE_PATH, "Scope")
    base.CreateAttribute(ATTR_NAME, Sdf.ValueTypeNames.String).Set(VALUE_SPECIALIZE)

    # ─── L_wins: LOCAL + VARIANT + SPECIALIZE ──────────────────────────────
    # Authoring order: composition arcs first (Specializes, then Variant
    # selection + variant-context opinion), local opinion last so it lives
    # on the root layer outside any variant edit context.
    l_wins = stage.DefinePrim(L_WINS_PATH, "Scope")
    _add_specialize(l_wins, BASE_PATH)
    _add_variant_opinion(l_wins, VALUE_VARIANT)
    _add_local_opinion(l_wins, VALUE_LOCAL)

    # ─── V_wins: VARIANT + SPECIALIZE (no LOCAL) ───────────────────────────
    v_wins = stage.DefinePrim(V_WINS_PATH, "Scope")
    _add_specialize(v_wins, BASE_PATH)
    _add_variant_opinion(v_wins, VALUE_VARIANT)

    # ─── S_wins: SPECIALIZE only ───────────────────────────────────────────
    s_wins = stage.DefinePrim(S_WINS_PATH, "Scope")
    _add_specialize(s_wins, BASE_PATH)

    stage.GetRootLayer().Save()

    return {
        "path": str(path),
        "attribute": ATTR_NAME,
        "scenarios": [
            {
                "path": L_WINS_PATH,
                "arcs": ["LOCAL", "VARIANT", "SPECIALIZE"],
                "expected_winner": "LOCAL",
                "expected_value": VALUE_LOCAL,
            },
            {
                "path": V_WINS_PATH,
                "arcs": ["VARIANT", "SPECIALIZE"],
                "expected_winner": "VARIANT",
                "expected_value": VALUE_VARIANT,
            },
            {
                "path": S_WINS_PATH,
                "arcs": ["SPECIALIZE"],
                "expected_winner": "SPECIALIZE",
                "expected_value": VALUE_SPECIALIZE,
            },
        ],
    }
