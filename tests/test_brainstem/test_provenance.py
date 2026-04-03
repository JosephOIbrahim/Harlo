"""Gate 3d: Structured provenance on all composition layers.

Every /Composition/Layer gets a fully populated Provenance dataclass.
Legacy layers get SYSTEM_INFERRED. Different sessions → different event_hashes.
"""

from __future__ import annotations

from datetime import datetime, timezone

from harlo.brainstem.provenance import (
    make_event_hash,
    migrate_legacy_provenance,
    stamp_provenance,
)
from harlo.usd_lite.arc_types import ArcType
from harlo.usd_lite.prims import (
    CompositionLayerPrim,
    Provenance,
    SourceType,
)

NOW = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
EARLIER = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _make_layer(**overrides) -> CompositionLayerPrim:
    defaults = dict(
        layer_id="l1",
        arc_type=ArcType.LOCAL,
        opinion={"key": "value"},
        timestamp=NOW,
    )
    defaults.update(overrides)
    return CompositionLayerPrim(**defaults)


class TestStampProvenance:
    """stamp_provenance attaches structured provenance."""

    def test_stamps_user_direct(self) -> None:
        layer = _make_layer()
        stamped = stamp_provenance(layer, SourceType.USER_DIRECT, "sess_1")
        assert stamped.provenance is not None
        assert stamped.provenance.source_type == SourceType.USER_DIRECT
        assert stamped.provenance.session_id == "sess_1"
        assert len(stamped.provenance.event_hash) == 64  # SHA256 hex

    def test_stamps_system_inferred(self) -> None:
        layer = _make_layer()
        stamped = stamp_provenance(layer, SourceType.SYSTEM_INFERRED, "sess_2")
        assert stamped.provenance.source_type == SourceType.SYSTEM_INFERRED

    def test_stamps_hebbian_derived(self) -> None:
        layer = _make_layer()
        stamped = stamp_provenance(layer, SourceType.HEBBIAN_DERIVED, "sess_3")
        assert stamped.provenance.source_type == SourceType.HEBBIAN_DERIVED

    def test_stamps_intake_calibrated(self) -> None:
        layer = _make_layer()
        stamped = stamp_provenance(layer, SourceType.INTAKE_CALIBRATED, "sess_4")
        assert stamped.provenance.source_type == SourceType.INTAKE_CALIBRATED

    def test_preserves_layer_fields(self) -> None:
        layer = _make_layer(permanent=True, opinion={"a": 1, "b": 2})
        stamped = stamp_provenance(layer, SourceType.USER_DIRECT, "s")
        assert stamped.permanent is True
        assert stamped.opinion == {"a": 1, "b": 2}
        assert stamped.arc_type == ArcType.LOCAL
        assert stamped.layer_id == "l1"
        assert stamped.timestamp == NOW

    def test_deterministic_event_hash(self) -> None:
        """Same inputs → same event hash."""
        layer = _make_layer()
        s1 = stamp_provenance(layer, SourceType.USER_DIRECT, "s1", "event_data")
        s2 = stamp_provenance(layer, SourceType.USER_DIRECT, "s1", "event_data")
        assert s1.provenance.event_hash == s2.provenance.event_hash

    def test_different_sessions_different_hashes(self) -> None:
        """Different sessions → different event hashes (via session_id in stamp, not hash)."""
        layer = _make_layer()
        s1 = stamp_provenance(layer, SourceType.USER_DIRECT, "sess_a")
        s2 = stamp_provenance(layer, SourceType.USER_DIRECT, "sess_b")
        assert s1.provenance.session_id != s2.provenance.session_id

    def test_different_event_data_different_hashes(self) -> None:
        layer = _make_layer()
        s1 = stamp_provenance(layer, SourceType.USER_DIRECT, "s", "data_1")
        s2 = stamp_provenance(layer, SourceType.USER_DIRECT, "s", "data_2")
        assert s1.provenance.event_hash != s2.provenance.event_hash

    def test_different_layer_ids_different_hashes(self) -> None:
        l1 = _make_layer(layer_id="layer_a")
        l2 = _make_layer(layer_id="layer_b")
        s1 = stamp_provenance(l1, SourceType.USER_DIRECT, "s")
        s2 = stamp_provenance(l2, SourceType.USER_DIRECT, "s")
        assert s1.provenance.event_hash != s2.provenance.event_hash

    def test_origin_timestamp_matches_layer(self) -> None:
        layer = _make_layer(timestamp=EARLIER)
        stamped = stamp_provenance(layer, SourceType.USER_DIRECT, "s")
        assert stamped.provenance.origin_timestamp == EARLIER


class TestMigrateLegacyProvenance:
    """Legacy layers get SYSTEM_INFERRED provenance."""

    def test_migrates_layer_without_provenance(self) -> None:
        layer = _make_layer()
        assert layer.provenance is None
        migrated = migrate_legacy_provenance(layer, session_id="legacy_sess")
        assert migrated.provenance is not None
        assert migrated.provenance.source_type == SourceType.SYSTEM_INFERRED
        assert migrated.provenance.session_id == "legacy_sess"

    def test_preserves_existing_provenance(self) -> None:
        """Layers that already have provenance are not re-stamped."""
        prov = Provenance(
            source_type=SourceType.USER_DIRECT,
            origin_timestamp=NOW,
            event_hash="existing_hash",
            session_id="original",
        )
        layer = _make_layer(provenance=prov)
        migrated = migrate_legacy_provenance(layer, session_id="should_not_appear")
        assert migrated.provenance.session_id == "original"
        assert migrated.provenance.event_hash == "existing_hash"

    def test_default_session_id(self) -> None:
        layer = _make_layer()
        migrated = migrate_legacy_provenance(layer)
        assert migrated.provenance.session_id == "legacy"

    def test_preserves_all_fields(self) -> None:
        layer = _make_layer(permanent=True, arc_type=ArcType.VARIANT)
        migrated = migrate_legacy_provenance(layer)
        assert migrated.permanent is True
        assert migrated.arc_type == ArcType.VARIANT


class TestMakeEventHash:
    """Deterministic event hash computation."""

    def test_deterministic(self) -> None:
        h1 = make_event_hash("l1", NOW, "data")
        h2 = make_event_hash("l1", NOW, "data")
        assert h1 == h2
        assert len(h1) == 64

    def test_different_inputs_different_hash(self) -> None:
        h1 = make_event_hash("l1", NOW, "data")
        h2 = make_event_hash("l2", NOW, "data")
        assert h1 != h2

    def test_empty_event_data(self) -> None:
        h = make_event_hash("l1", NOW)
        assert len(h) == 64


class TestProvenanceSourceTypes:
    """All 5 source types are valid and distinct."""

    def test_all_source_types_exist(self) -> None:
        assert len(SourceType) == 5

    def test_source_type_values(self) -> None:
        expected = {
            "user_direct", "external_reference", "system_inferred",
            "hebbian_derived", "intake_calibrated",
        }
        actual = {st.value for st in SourceType}
        assert actual == expected
