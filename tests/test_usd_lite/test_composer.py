"""LIVRPS composition engine tests — precedence, permanence, tie-breaking."""

from __future__ import annotations

from datetime import datetime, timezone

from harlo.usd_lite.arc_types import ArcType
from harlo.usd_lite.composer import compose
from harlo.usd_lite.prims import CompositionLayerPrim


T1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 2, 1, tzinfo=timezone.utc)
T3 = datetime(2026, 3, 1, tzinfo=timezone.utc)


def _layer(
    layer_id: str,
    arc: ArcType,
    opinion: dict,
    ts: datetime = T1,
    permanent: bool = False,
) -> CompositionLayerPrim:
    return CompositionLayerPrim(
        layer_id=layer_id,
        arc_type=arc,
        opinion=opinion,
        timestamp=ts,
        permanent=permanent,
    )


class TestBasicLIVRPS:
    """Normal LIVRPS resolution without permanence."""

    def test_single_layer(self) -> None:
        result = compose([_layer("l1", ArcType.LOCAL, {"a": 1})])
        assert result.outcome == {"a": 1}
        assert result.winning_layers == {"a": "l1"}

    def test_empty_layers(self) -> None:
        result = compose([])
        assert result.outcome == {}
        assert result.winning_layers == {}

    def test_stronger_arc_wins(self) -> None:
        layers = [
            _layer("weak", ArcType.SUBLAYER, {"a": "weak"}),
            _layer("strong", ArcType.LOCAL, {"a": "strong"}),
        ]
        result = compose(layers)
        assert result.outcome["a"] == "strong"
        assert result.winning_layers["a"] == "strong"

    def test_same_arc_later_timestamp_wins(self) -> None:
        layers = [
            _layer("old", ArcType.VARIANT, {"a": "old"}, ts=T1),
            _layer("new", ArcType.VARIANT, {"a": "new"}, ts=T2),
        ]
        result = compose(layers)
        assert result.outcome["a"] == "new"

    def test_stronger_arc_beats_later_timestamp(self) -> None:
        layers = [
            _layer("strong_old", ArcType.LOCAL, {"a": "strong"}, ts=T1),
            _layer("weak_new", ArcType.SUBLAYER, {"a": "weak"}, ts=T3),
        ]
        result = compose(layers)
        assert result.outcome["a"] == "strong"

    def test_independent_attributes(self) -> None:
        layers = [
            _layer("l1", ArcType.LOCAL, {"a": 1}),
            _layer("l2", ArcType.SUBLAYER, {"b": 2}),
        ]
        result = compose(layers)
        assert result.outcome == {"a": 1, "b": 2}

    def test_multiple_attributes_mixed(self) -> None:
        layers = [
            _layer("l1", ArcType.SUBLAYER, {"a": "sub", "b": "sub"}, ts=T1),
            _layer("l2", ArcType.LOCAL, {"a": "local"}, ts=T2),
        ]
        result = compose(layers)
        assert result.outcome["a"] == "local"
        assert result.outcome["b"] == "sub"


class TestPermanentPrims:
    """Permanent prims override normal LIVRPS rules."""

    def test_permanent_beats_non_permanent_local(self) -> None:
        layers = [
            _layer("local", ArcType.LOCAL, {"a": "local"}, ts=T2),
            _layer("perm", ArcType.SUBLAYER, {"a": "permanent"}, ts=T1, permanent=True),
        ]
        result = compose(layers)
        assert result.outcome["a"] == "permanent"

    def test_non_permanent_cannot_override_permanent(self) -> None:
        layers = [
            _layer("perm", ArcType.SUBLAYER, {"a": "permanent"}, ts=T1, permanent=True),
            _layer("local", ArcType.LOCAL, {"a": "local"}, ts=T3),
        ]
        result = compose(layers)
        assert result.outcome["a"] == "permanent"

    def test_among_permanents_later_wins(self) -> None:
        layers = [
            _layer("old_perm", ArcType.LOCAL, {"a": "old"}, ts=T1, permanent=True),
            _layer("new_perm", ArcType.SUBLAYER, {"a": "new"}, ts=T2, permanent=True),
        ]
        result = compose(layers)
        assert result.outcome["a"] == "new"

    def test_permanent_first_layer_stays(self) -> None:
        layers = [
            _layer("perm", ArcType.REFERENCE, {"a": "perm"}, ts=T1, permanent=True),
            _layer("later", ArcType.LOCAL, {"a": "later"}, ts=T3),
        ]
        result = compose(layers)
        assert result.outcome["a"] == "perm"

    def test_permanent_only_affects_its_attributes(self) -> None:
        layers = [
            _layer("perm", ArcType.SUBLAYER, {"a": "perm"}, permanent=True),
            _layer("normal", ArcType.LOCAL, {"b": "normal"}),
        ]
        result = compose(layers)
        assert result.outcome == {"a": "perm", "b": "normal"}


class TestAuditTrace:
    """Composition produces an audit trace of all decisions."""

    def test_set_action(self) -> None:
        result = compose([_layer("l1", ArcType.LOCAL, {"a": 1})])
        assert len(result.trace) == 1
        assert result.trace[0]["action"] == "set"
        assert result.trace[0]["layer_id"] == "l1"

    def test_override_action(self) -> None:
        layers = [
            _layer("weak", ArcType.SUBLAYER, {"a": "weak"}),
            _layer("strong", ArcType.LOCAL, {"a": "strong"}),
        ]
        result = compose(layers)
        actions = [t["action"] for t in result.trace]
        assert "set" in actions
        assert "override" in actions

    def test_kept_action(self) -> None:
        layers = [
            _layer("strong", ArcType.LOCAL, {"a": "strong"}),
            _layer("weak", ArcType.SUBLAYER, {"a": "weak"}),
        ]
        result = compose(layers)
        actions = [t["action"] for t in result.trace]
        assert "kept" in actions

    def test_permanent_override_reason(self) -> None:
        layers = [
            _layer("normal", ArcType.LOCAL, {"a": "normal"}),
            _layer("perm", ArcType.SUBLAYER, {"a": "perm"}, permanent=True),
        ]
        result = compose(layers)
        override_entry = [t for t in result.trace if t["action"] == "override"][0]
        assert override_entry["reason"] == "permanent_override"

    def test_trace_records_all_decisions(self) -> None:
        layers = [
            _layer("l1", ArcType.LOCAL, {"a": 1, "b": 2}),
            _layer("l2", ArcType.SUBLAYER, {"a": 10, "c": 3}),
        ]
        result = compose(layers)
        # a: set by l1, then l2 kept (l1 stronger)
        # b: set by l1
        # c: set by l2
        assert len(result.trace) == 4
