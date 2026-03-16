"""Gate 5c: Training data pipeline — JSONL + features + O(1) log rotation.

Tests:
- Every verification → valid JSONL row
- No reasoning traces (Rule 11)
- retrieval_path correctly reflects SYSTEM_1 vs SYSTEM_2
- cognitive_profile_hash present and deterministic
- cognitive_profile_features present/empty appropriately (Patch 5)
- Log rotation at max_rows (Patch 8)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cognitive_twin.hebbian.training_data import (
    _MAX_ROWS,
    _MAX_ROTATED_FILES,
    _profile_features,
    _profile_hash,
    get_row_count,
    record_verification,
)
from cognitive_twin.usd_lite.prims import CognitiveProfilePrim, MultipliersPrim


class TestRecordVerification:
    """Every verification → valid JSONL row."""

    def test_basic_record(self, tmp_path: Path) -> None:
        row = record_verification(
            intent_hash="intent_abc",
            output_hash="output_def",
            verification_state="TRUSTED",
            cycle_count=2,
            data_dir=tmp_path,
        )
        assert row["intent_hash"] == "intent_abc"
        assert row["verification_state"] == "TRUSTED"
        assert row["cycle_count"] == 2

    def test_writes_to_jsonl(self, tmp_path: Path) -> None:
        record_verification(
            intent_hash="h1", output_hash="h2",
            verification_state="TRUSTED", cycle_count=1,
            data_dir=tmp_path,
        )
        filepath = tmp_path / "aletheia_training.jsonl"
        assert filepath.exists()
        lines = filepath.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["intent_hash"] == "h1"

    def test_appends_rows(self, tmp_path: Path) -> None:
        for i in range(5):
            record_verification(
                intent_hash=f"h{i}", output_hash=f"o{i}",
                verification_state="TRUSTED", cycle_count=1,
                data_dir=tmp_path,
            )
        assert get_row_count(tmp_path) == 5

    def test_retrieval_path_system_1(self, tmp_path: Path) -> None:
        row = record_verification(
            intent_hash="h", output_hash="o",
            verification_state="TRUSTED", cycle_count=1,
            retrieval_path="SYSTEM_1",
            data_dir=tmp_path,
        )
        assert row["retrieval_path"] == "SYSTEM_1"

    def test_retrieval_path_system_2(self, tmp_path: Path) -> None:
        row = record_verification(
            intent_hash="h", output_hash="o",
            verification_state="TRUSTED", cycle_count=1,
            retrieval_path="SYSTEM_2",
            data_dir=tmp_path,
        )
        assert row["retrieval_path"] == "SYSTEM_2"

    def test_no_reasoning_trace_field(self, tmp_path: Path) -> None:
        """Rule 11: No reasoning traces in dataset."""
        row = record_verification(
            intent_hash="h", output_hash="o",
            verification_state="TRUSTED", cycle_count=1,
            data_dir=tmp_path,
        )
        assert "reasoning_trace" not in row
        assert "trace" not in row or row.get("trace") is None


class TestProfileHash:
    """cognitive_profile_hash is deterministic."""

    def test_deterministic(self) -> None:
        profile = CognitiveProfilePrim(
            multipliers=MultipliersPrim(surprise_threshold=2.3),
        )
        h1 = _profile_hash(profile)
        h2 = _profile_hash(profile)
        assert h1 == h2
        assert len(h1) == 64

    def test_none_profile_deterministic(self) -> None:
        h1 = _profile_hash(None)
        h2 = _profile_hash(None)
        assert h1 == h2

    def test_different_profiles_different_hash(self) -> None:
        p1 = CognitiveProfilePrim(multipliers=MultipliersPrim(surprise_threshold=2.0))
        p2 = CognitiveProfilePrim(multipliers=MultipliersPrim(surprise_threshold=2.5))
        assert _profile_hash(p1) != _profile_hash(p2)


class TestProfileFeatures:
    """Patch 5: cognitive_profile_features present and typed correctly."""

    def test_with_profile(self) -> None:
        profile = CognitiveProfilePrim(
            multipliers=MultipliersPrim(
                surprise_threshold=2.3,
                reconstruction_threshold=0.25,
                hebbian_alpha=0.015,
                allostatic_threshold=0.8,
                detail_orientation=0.4,
            ),
        )
        features = _profile_features(profile)
        assert features["surprise_threshold"] == 2.3
        assert features["reconstruction_threshold"] == 0.25
        assert features["hebbian_alpha"] == 0.015
        assert features["allostatic_threshold"] == 0.8
        assert features["detail_orientation"] == 0.4

    def test_without_profile_empty_dict(self) -> None:
        """No profile → empty dict {}, never null, never missing key."""
        features = _profile_features(None)
        assert features == {}
        assert isinstance(features, dict)

    def test_features_in_recorded_row(self, tmp_path: Path) -> None:
        profile = CognitiveProfilePrim(
            multipliers=MultipliersPrim(surprise_threshold=2.5),
        )
        row = record_verification(
            intent_hash="h", output_hash="o",
            verification_state="TRUSTED", cycle_count=1,
            profile=profile,
            data_dir=tmp_path,
        )
        assert "cognitive_profile_features" in row
        assert row["cognitive_profile_features"]["surprise_threshold"] == 2.5

    def test_features_empty_when_no_profile(self, tmp_path: Path) -> None:
        row = record_verification(
            intent_hash="h", output_hash="o",
            verification_state="TRUSTED", cycle_count=1,
            profile=None,
            data_dir=tmp_path,
        )
        assert row["cognitive_profile_features"] == {}


class TestLogRotation:
    """Patch 8: O(1) amortized log rotation at max_rows."""

    def test_rotation_at_max_rows(self, tmp_path: Path) -> None:
        """File rotates when reaching max_rows."""
        # Write max_rows entries
        filepath = tmp_path / "aletheia_training.jsonl"
        with open(filepath, "w", encoding="utf-8") as f:
            for i in range(_MAX_ROWS):
                f.write(json.dumps({"row": i}) + "\n")

        # This write should trigger rotation
        record_verification(
            intent_hash="trigger", output_hash="rotation",
            verification_state="TRUSTED", cycle_count=1,
            data_dir=tmp_path,
        )

        # Original file should be small (just the new row)
        assert get_row_count(tmp_path) == 1

        # Rotated file should exist
        rotated = list(tmp_path.glob("aletheia_training.*.jsonl"))
        assert len(rotated) >= 1

    def test_max_rotated_files(self, tmp_path: Path) -> None:
        """At most MAX_ROTATED_FILES old files retained."""
        filepath = tmp_path / "aletheia_training.jsonl"

        # Create more than max rotated files
        for j in range(_MAX_ROTATED_FILES + 2):
            with open(filepath, "w", encoding="utf-8") as f:
                for i in range(_MAX_ROWS):
                    f.write(json.dumps({"batch": j, "row": i}) + "\n")

            record_verification(
                intent_hash=f"h{j}", output_hash=f"o{j}",
                verification_state="TRUSTED", cycle_count=1,
                data_dir=tmp_path,
            )

        rotated = list(tmp_path.glob("aletheia_training.*.jsonl"))
        assert len(rotated) <= _MAX_ROTATED_FILES

    def test_no_full_rewrite(self, tmp_path: Path) -> None:
        """Rotation uses rename, not full rewrite. O(1) amortized."""
        filepath = tmp_path / "aletheia_training.jsonl"
        with open(filepath, "w", encoding="utf-8") as f:
            for i in range(100):
                f.write(json.dumps({"row": i}) + "\n")

        # Below max_rows — no rotation
        record_verification(
            intent_hash="h", output_hash="o",
            verification_state="TRUSTED", cycle_count=1,
            data_dir=tmp_path,
        )
        assert get_row_count(tmp_path) == 101
        rotated = list(tmp_path.glob("aletheia_training.*.jsonl"))
        assert len(rotated) == 0  # No rotation yet
