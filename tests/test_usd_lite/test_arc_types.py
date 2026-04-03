"""ArcType enum — ordering and precedence tests."""

from __future__ import annotations

from harlo.usd_lite.arc_types import ArcType


class TestArcTypeOrdering:
    """Verify LIVRPS precedence: LOCAL is strongest, SUBLAYER weakest."""

    def test_local_is_strongest(self) -> None:
        assert ArcType.LOCAL < ArcType.INHERIT
        assert ArcType.LOCAL < ArcType.VARIANT
        assert ArcType.LOCAL < ArcType.REFERENCE
        assert ArcType.LOCAL < ArcType.PAYLOAD
        assert ArcType.LOCAL < ArcType.SUBLAYER

    def test_full_ordering(self) -> None:
        expected = [
            ArcType.LOCAL,
            ArcType.INHERIT,
            ArcType.VARIANT,
            ArcType.REFERENCE,
            ArcType.PAYLOAD,
            ArcType.SUBLAYER,
        ]
        assert sorted(ArcType) == expected

    def test_values(self) -> None:
        assert ArcType.LOCAL.value == 1
        assert ArcType.SUBLAYER.value == 6

    def test_name_roundtrip(self) -> None:
        for arc in ArcType:
            assert ArcType[arc.name] is arc

    def test_value_roundtrip(self) -> None:
        for arc in ArcType:
            assert ArcType(arc.value) is arc

    def test_six_members(self) -> None:
        assert len(ArcType) == 6
