"""Tests for Sprint 4 Phase 1: CognitiveStage — real pxr.Usd.Stage.

Verifies:
- Creates .usda on disk, reopens correctly
- Prim hierarchy exists
- author() + read() round-trip at same exchange_index
- read_previous(0) returns defaults, NEVER None
- Time samples work correctly
- Delegate sublayers create real .usda files
- author_to_sublayer() and read_from_sublayer()
- save() persists state
- Thresholds readable
- compose() merges base + sublayers
- Interface compatibility with MockUsdStage
"""

import os
import pytest

from src.cognitive_stage import CognitiveStage
from src.schemas import (
    CognitiveObservation,
    DynamicsBlock,
    Momentum,
    Burnout,
    Energy,
    StateBlock,
)


@pytest.fixture
def stage(tmp_path):
    """Create a CognitiveStage in a temp directory."""
    return CognitiveStage(stage_dir=str(tmp_path))


@pytest.fixture
def mem_stage():
    """Create an in-memory CognitiveStage."""
    return CognitiveStage(in_memory=True)


# -------------------------------------------------------------------
# File creation and hierarchy
# -------------------------------------------------------------------

class TestStageCreation:
    def test_creates_usda_on_disk(self, tmp_path):
        stage = CognitiveStage(stage_dir=str(tmp_path))
        usda_path = tmp_path / "cognitive_twin.usda"
        assert usda_path.exists()

    def test_reopens_existing_stage(self, tmp_path):
        s1 = CognitiveStage(stage_dir=str(tmp_path))
        obs = CognitiveObservation(exchange_index=1)
        s1.author("/state", 1, obs)
        s1.save()

        s2 = CognitiveStage(stage_dir=str(tmp_path))
        result = s2.read("/state", 1)
        assert result is not None
        assert result.exchange_index == 1

    def test_prim_hierarchy(self, mem_stage):
        from pxr import Usd
        usd_stage = mem_stage.usd_stage
        for path in ["/state", "/routing", "/delegates", "/prediction", "/memory"]:
            prim = usd_stage.GetPrimAtPath(path)
            assert prim.IsValid(), f"Missing prim: {path}"

    def test_in_memory_mode(self):
        stage = CognitiveStage(in_memory=True)
        obs = CognitiveObservation()
        stage.author("/state", 0, obs)
        result = stage.read("/state", 0)
        assert result is not None


# -------------------------------------------------------------------
# Core API: author, read, read_previous
# -------------------------------------------------------------------

class TestCoreAPI:
    def test_author_and_read_round_trip(self, mem_stage):
        obs = CognitiveObservation(
            exchange_index=5,
            state=StateBlock(momentum=Momentum.ROLLING),
        )
        mem_stage.author("/state", 5, obs)
        result = mem_stage.read("/state", 5)
        assert result is not None
        assert result.exchange_index == 5
        assert result.state.momentum == Momentum.ROLLING

    def test_read_missing_returns_none(self, mem_stage):
        assert mem_stage.read("/state", 99) is None

    def test_read_previous_at_zero_returns_baseline(self, mem_stage):
        """Commandment 6: NEVER None at index 0."""
        result = mem_stage.read_previous("/state", 0)
        assert result is not None
        assert result.state.momentum == Momentum.COLD_START
        assert result.state.burnout == Burnout.GREEN
        assert result.state.energy == Energy.MEDIUM

    def test_read_previous_never_returns_none(self, mem_stage):
        result = mem_stage.read_previous("/state", 10)
        assert result is not None

    def test_read_previous_reads_t_minus_1(self, mem_stage):
        obs3 = CognitiveObservation(
            exchange_index=3,
            state=StateBlock(momentum=Momentum.BUILDING),
        )
        mem_stage.author("/state", 3, obs3)
        result = mem_stage.read_previous("/state", 4)
        assert result.state.momentum == Momentum.BUILDING

    def test_time_samples_independent(self, mem_stage):
        """Different exchange indices store different values."""
        obs_a = CognitiveObservation(exchange_index=0, state=StateBlock(energy=Energy.HIGH))
        obs_b = CognitiveObservation(exchange_index=1, state=StateBlock(energy=Energy.LOW))
        mem_stage.author("/state", 0, obs_a)
        mem_stage.author("/state", 1, obs_b)
        assert mem_stage.read("/state", 0).state.energy == Energy.HIGH
        assert mem_stage.read("/state", 1).state.energy == Energy.LOW

    def test_dict_value_round_trip(self, mem_stage):
        """Non-observation values also work."""
        data = {"momentum": 3, "burnout": 0}
        mem_stage.author("/prediction/forecast", 5, data)
        result = mem_stage.read("/prediction/forecast", 5)
        assert result["momentum"] == 3


# -------------------------------------------------------------------
# Thresholds
# -------------------------------------------------------------------

class TestThresholds:
    def test_default_thresholds(self, mem_stage):
        assert mem_stage.get_threshold("building_task_threshold") == 3
        assert mem_stage.get_threshold("rolling_coherence_threshold") == 0.7

    def test_custom_thresholds(self):
        stage = CognitiveStage(
            in_memory=True,
            thresholds={"building_task_threshold": 5},
        )
        assert stage.get_threshold("building_task_threshold") == 5


# -------------------------------------------------------------------
# Delegate sublayers
# -------------------------------------------------------------------

class TestDelegateSublayers:
    def test_create_sublayer_disk(self, tmp_path):
        stage = CognitiveStage(stage_dir=str(tmp_path))
        stage.create_delegate_sublayer("claude")
        layer_path = tmp_path / "delegates" / "claude.usda"
        assert layer_path.exists()

    def test_create_sublayer_in_memory(self, mem_stage):
        mem_stage.create_delegate_sublayer("claude")
        mem_stage.create_delegate_sublayer("claude_code")
        assert len(mem_stage._sublayer_stages) == 2

    def test_author_to_sublayer(self, mem_stage):
        mem_stage.create_delegate_sublayer("claude")
        mem_stage.author_to_sublayer("claude", "/delegates/claude", 1, {"status": "active"})
        result = mem_stage.read_from_sublayer("claude", "/delegates/claude", 1)
        assert result == {"status": "active"}

    def test_sublayers_isolated(self, mem_stage):
        mem_stage.create_delegate_sublayer("claude")
        mem_stage.create_delegate_sublayer("claude_code")
        mem_stage.author_to_sublayer("claude", "/state", 0, {"from": "claude"})
        mem_stage.author_to_sublayer("claude_code", "/state", 0, {"from": "code"})
        assert mem_stage.read_from_sublayer("claude", "/state", 0)["from"] == "claude"
        assert mem_stage.read_from_sublayer("claude_code", "/state", 0)["from"] == "code"

    def test_read_from_nonexistent_sublayer(self, mem_stage):
        assert mem_stage.read_from_sublayer("nonexistent", "/state", 0) is None

    def test_compose_merges_sublayers(self, mem_stage):
        mem_stage.author("/state", 0, {"base": True})
        mem_stage.create_delegate_sublayer("claude")
        mem_stage.author_to_sublayer("claude", "/delegates/claude", 0, {"delegate": True})
        composed = mem_stage.compose()
        assert len(composed) >= 2


# -------------------------------------------------------------------
# Utility methods
# -------------------------------------------------------------------

class TestUtility:
    def test_keys(self, mem_stage):
        mem_stage.author("/state", 0, CognitiveObservation())
        mem_stage.author("/state", 1, CognitiveObservation())
        keys = mem_stage.keys()
        assert len(keys) == 2

    def test_max_exchange_index(self, mem_stage):
        assert mem_stage.max_exchange_index() == -1
        mem_stage.author("/state", 0, CognitiveObservation())
        mem_stage.author("/state", 5, CognitiveObservation())
        assert mem_stage.max_exchange_index() == 5

    def test_clear(self, mem_stage):
        mem_stage.author("/state", 0, CognitiveObservation())
        mem_stage.clear()
        assert mem_stage.read("/state", 0) is None

    def test_get_usda_text(self, mem_stage):
        mem_stage.author("/state", 0, CognitiveObservation())
        text = mem_stage.get_usda_text()
        assert "#usda" in text

    def test_export_flat(self, tmp_path):
        stage = CognitiveStage(stage_dir=str(tmp_path))
        stage.author("/state", 0, CognitiveObservation())
        stage.save()
        out = str(tmp_path / "flat.usda")
        stage.export_flat(out)
        assert os.path.exists(out)
