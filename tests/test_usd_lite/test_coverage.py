"""Coverage completion tests for usd_lite module.

Targets uncovered branches: BrainStage.to_dict/from_dict, container prim
dict round-trips, serializer edge cases, and default fallback paths.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cognitive_twin.usd_lite.arc_types import ArcType
from cognitive_twin.usd_lite.prims import (
    ElenchusPrim,
    AssociationPrim,
    CognitiveProfilePrim,
    CompositionLayerPrim,
    CompositionPrim,
    GateStatusPrim,
    InquiryContainerPrim,
    InquiryPrim,
    IntakeHistoryPrim,
    MerkleRootPrim,
    MotorContainerPrim,
    MotorGateStatus,
    MotorPrim,
    MultipliersPrim,
    Provenance,
    RetrievalPath,
    SessionPrim,
    SkillPrim,
    SkillsContainerPrim,
    SourceType,
    TracePrim,
    VerificationState,
)
from cognitive_twin.usd_lite.serializer import parse, serialize
from cognitive_twin.usd_lite.stage import BrainStage


NOW = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)


class TestBrainStageDictRoundTrip:
    """BrainStage.to_dict / from_dict coverage."""

    def test_empty_stage_dict_roundtrip(self) -> None:
        stage = BrainStage()
        d = stage.to_dict()
        restored = BrainStage.from_dict(d)
        assert restored == stage

    def test_full_stage_dict_roundtrip(self) -> None:
        stage = BrainStage(
            session=SessionPrim(current_session_id="s1", exchange_count=5),
            inquiry=InquiryContainerPrim(active=[
                InquiryPrim(hypothesis="h1", confidence=0.5),
            ]),
            motor=MotorContainerPrim(pending=[
                MotorPrim(action="a1", gate_status=MotorGateStatus.INHIBITED),
            ]),
            skills=SkillsContainerPrim(domains={
                "d1": SkillPrim(domain="d1", trace_count=1, first_seen=NOW, last_seen=NOW),
            }),
        )
        d = stage.to_dict()
        restored = BrainStage.from_dict(d)
        assert restored == stage

    def test_stage_no_session_dict(self) -> None:
        stage = BrainStage()
        d = stage.to_dict()
        assert d["session"] is None
        restored = BrainStage.from_dict(d)
        assert restored.session is None


class TestContainerPrimDictRoundTrips:
    """Direct to_dict/from_dict on container prims — coverage for uncovered lines."""

    def test_composition_prim_dict(self) -> None:
        layer = CompositionLayerPrim(
            layer_id="l1", arc_type=ArcType.LOCAL, opinion={"k": "v"}, timestamp=NOW,
        )
        cp = CompositionPrim(layers={"l1": layer})
        restored = CompositionPrim.from_dict(cp.to_dict())
        assert "l1" in restored.layers
        assert restored.layers["l1"].arc_type == ArcType.LOCAL

    def test_inquiry_container_dict(self) -> None:
        ic = InquiryContainerPrim(active=[
            InquiryPrim(hypothesis="test", confidence=0.7),
        ])
        restored = InquiryContainerPrim.from_dict(ic.to_dict())
        assert len(restored.active) == 1
        assert restored.active[0].hypothesis == "test"

    def test_motor_container_dict(self) -> None:
        mc = MotorContainerPrim(pending=[
            MotorPrim(action="act", gate_status=MotorGateStatus.APPROVED),
        ])
        restored = MotorContainerPrim.from_dict(mc.to_dict())
        assert len(restored.pending) == 1
        assert restored.pending[0].gate_status == MotorGateStatus.APPROVED

    def test_skills_container_dict(self) -> None:
        sc = SkillsContainerPrim(domains={
            "rust": SkillPrim(domain="rust", trace_count=10, first_seen=NOW, last_seen=NOW),
        })
        restored = SkillsContainerPrim.from_dict(sc.to_dict())
        assert "rust" in restored.domains


class TestSerializerEdgeCases:
    """Edge cases for serializer coverage."""

    def test_integer_float_format(self) -> None:
        """Float that looks like an integer (e.g. 2.0) gets decimal point."""
        stage = BrainStage(session=SessionPrim(
            current_session_id="s1",
            exchange_count=0,
            surprise_rolling_mean=0.0,
        ))
        text = serialize(stage)
        assert "0.0" in text

    def test_trace_without_co_activations(self) -> None:
        """Traces with empty co_activations/competitions omit those fields."""
        trace = TracePrim(
            trace_id="t1",
            sdr=[0] * 2048,
            content_hash="hash",
            strength=1.0,
            last_accessed=NOW,
        )
        stage = BrainStage(association=AssociationPrim(traces={"t1": trace}))
        text = serialize(stage)
        # co_activations should not appear since it's empty
        assert "co_activations" not in text
        # But it round-trips correctly (defaults to empty)
        restored = parse(text)
        assert restored.association.traces["t1"].co_activations == {}

    def test_intake_history_empty_roundtrip_via_usda(self) -> None:
        """IntakeHistory with no fields omits them from .usda."""
        stage = BrainStage(cognitive_profile=CognitiveProfilePrim(
            intake_history=IntakeHistoryPrim(),
        ))
        text = serialize(stage)
        # last_intake should not appear
        assert "last_intake" not in text
        restored = parse(text)
        assert restored.cognitive_profile.intake_history.last_intake is None
        assert restored.cognitive_profile.intake_history.intake_version is None

    def test_malformed_open_brace(self) -> None:
        """Parser raises on missing open brace."""
        with pytest.raises(ValueError, match="Expected"):
            parse('#usda 1.0\ndef BrainStage "Brain"\nNOT_A_BRACE\n')

    def test_unexpected_eof(self) -> None:
        """Parser raises on unexpected end of input."""
        with pytest.raises(ValueError):
            parse('#usda 1.0\ndef BrainStage "Brain"\n{\n')

    def test_skill_with_empty_growth_arc_text(self) -> None:
        """Skill with empty growth arc serializes as []."""
        stage = BrainStage(skills=SkillsContainerPrim(domains={
            "test": SkillPrim(
                domain="test", trace_count=0, first_seen=NOW, last_seen=NOW,
                growth_arc=[],
            ),
        }))
        text = serialize(stage)
        assert "[]" in text
        restored = parse(text)
        assert restored.skills.domains["test"].growth_arc == []

    def test_usda_with_blank_lines_and_comments(self) -> None:
        """Parser skips blank lines between blocks."""
        stage = BrainStage()
        text = serialize(stage)
        # Insert blank lines
        lines = text.split("\n")
        padded = "\n\n".join(lines)
        restored = parse(padded)
        assert restored == stage

    def test_usda_with_unknown_lines(self) -> None:
        """Parser skips unrecognized lines."""
        stage = BrainStage()
        text = serialize(stage)
        # Insert an unknown line inside the Brain block
        lines = text.split("\n")
        # Insert after the opening brace
        for i, line in enumerate(lines):
            if line.strip() == "{" and i > 0:
                lines.insert(i + 1, "    # This is a comment-like unknown line")
                break
        modified = "\n".join(lines)
        restored = parse(modified)
        assert restored == stage

    def test_partial_usda_missing_attrs(self) -> None:
        """Parse a .usda with missing attributes to hit default branches."""
        # Minimal trace with only required fields — missing optional int/float/hex/bool
        usda = '''#usda 1.0
def BrainStage "Brain"
{
    def AssociationPrim "Association"
    {
        def TracePrim "t_partial"
        {
            hex sdr = "''' + "0" * 512 + '''"
            string content_hash = "hash"
            float strength = 0.5
            token last_accessed = "2026-03-15T12:00:00+00:00"
        }
    }
    def CompositionPrim "Composition"
    {
    }
    def ElenchusPrim "Elenchus"
    {
    }
    def InquiryContainerPrim "Inquiry"
    {
    }
    def MotorContainerPrim "Motor"
    {
    }
    def SkillsContainerPrim "Skills"
    {
        def SkillPrim "minimal_skill"
        {
            token first_seen = "2026-01-01T00:00:00+00:00"
            token last_seen = "2026-03-15T12:00:00+00:00"
        }
    }
    def CognitiveProfilePrim "CognitiveProfile"
    {
        def MultipliersPrim "Multipliers"
        {
        }
        def IntakeHistoryPrim "IntakeHistory"
        {
        }
    }
}
'''
        restored = parse(usda)
        # Trace defaults
        t = restored.association.traces["t_partial"]
        assert t.co_activations == {}
        assert t.competitions == {}
        assert t.hebbian_strengthen_mask == [0] * 2048
        assert t.hebbian_weaken_mask == [0] * 2048
        # Skill defaults
        s = restored.skills.domains["minimal_skill"]
        assert s.trace_count == 0  # default int
        assert s.growth_arc == []  # default float array
        assert s.hebbian_density == 0.0  # default float
        # Multipliers defaults
        m = restored.cognitive_profile.multipliers
        assert m.surprise_threshold == 2.0
        assert m.reconstruction_threshold == 0.3
        # Profile defaults
        assert restored.cognitive_profile.intake_history.last_intake is None

    def test_fmt_float_integer_value(self) -> None:
        """A float that repr()s without decimal point gets '.0' appended."""
        from cognitive_twin.usd_lite.serializer import _fmt_float
        # Python's repr(2.0) is '2.0' so this already has a decimal.
        # But repr of a very large/small float might not — hard to trigger.
        # Instead, just verify the function works correctly.
        assert "." in _fmt_float(2.0)
        assert "." in _fmt_float(0.0)
        assert "." in _fmt_float(1e10)
        assert _fmt_float(float("inf")) == "inf"
        assert _fmt_float(float("nan")).lower() == "nan"

    def test_parse_quoted_unquoted(self) -> None:
        """_parse_quoted returns unquoted input as-is."""
        from cognitive_twin.usd_lite.serializer import _parse_quoted
        assert _parse_quoted("bare_value") == "bare_value"
        assert _parse_quoted('"quoted"') == "quoted"

    def test_minimal_stage_with_only_association(self) -> None:
        """Parse a stage that only has association — missing optional attrs trigger defaults."""
        trace = TracePrim(
            trace_id="t_min",
            sdr=[0] * 2048,
            content_hash="min_hash",
            strength=0.5,
            last_accessed=NOW,
        )
        stage = BrainStage(association=AssociationPrim(traces={"t_min": trace}))
        text = serialize(stage)
        restored = parse(text)
        # The trace should have default empty dicts/masks
        t = restored.association.traces["t_min"]
        assert t.co_activations == {}
        assert t.hebbian_strengthen_mask == [0] * 2048
