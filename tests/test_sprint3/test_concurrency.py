"""Tests for Sprint 3 Phase 4: Sublayer-per-delegate concurrency."""

import pytest

from src.mock_usd_stage import MockUsdStage


class TestSublayerConcurrency:
    def test_create_sublayer(self):
        stage = MockUsdStage()
        stage.create_delegate_sublayer("claude")
        stage.create_delegate_sublayer("claude_code")
        composed = stage.compose()
        assert composed == {}  # empty sublayers

    def test_write_to_sublayer(self):
        stage = MockUsdStage()
        stage.create_delegate_sublayer("claude")
        stage.author_to_sublayer("claude", "/state", 0, {"momentum": 3})
        val = stage.read_from_sublayer("claude", "/state", 0)
        assert val == {"momentum": 3}

    def test_sublayers_isolated(self):
        """Delegate A cannot read delegate B's uncommitted writes."""
        stage = MockUsdStage()
        stage.create_delegate_sublayer("claude")
        stage.create_delegate_sublayer("claude_code")
        stage.author_to_sublayer("claude", "/state", 0, {"momentum": 3})
        stage.author_to_sublayer("claude_code", "/state", 0, {"momentum": 2})
        # Each sees only its own
        assert stage.read_from_sublayer("claude", "/state", 0) == {"momentum": 3}
        assert stage.read_from_sublayer("claude_code", "/state", 0) == {"momentum": 2}

    def test_compose_merges_sublayers(self):
        stage = MockUsdStage()
        stage.author("/base", 0, "base_value")
        stage.create_delegate_sublayer("claude_code")
        stage.create_delegate_sublayer("claude")
        stage.author_to_sublayer("claude_code", "/delegate_a", 0, "code_val")
        stage.author_to_sublayer("claude", "/delegate_b", 0, "claude_val")
        composed = stage.compose()
        assert composed[("/base", 0)] == "base_value"
        assert composed[("/delegate_a", 0)] == "code_val"
        assert composed[("/delegate_b", 0)] == "claude_val"

    def test_interactive_wins_on_conflict(self):
        """Claude (interactive) is strongest, overwrites Claude Code (batch)."""
        stage = MockUsdStage()
        stage.create_delegate_sublayer("claude_code")
        stage.create_delegate_sublayer("claude")
        # Default priority: registration order, last = strongest
        stage.author_to_sublayer("claude_code", "/state", 0, "batch_value")
        stage.author_to_sublayer("claude", "/state", 0, "interactive_value")
        composed = stage.compose()
        assert composed[("/state", 0)] == "interactive_value"

    def test_custom_priority_order(self):
        stage = MockUsdStage()
        stage.create_delegate_sublayer("claude")
        stage.create_delegate_sublayer("claude_code")
        # Reverse: make claude_code strongest
        stage.set_sublayer_priority(["claude", "claude_code"])
        stage.author_to_sublayer("claude", "/state", 0, "claude_val")
        stage.author_to_sublayer("claude_code", "/state", 0, "code_val")
        composed = stage.compose()
        assert composed[("/state", 0)] == "code_val"

    def test_base_overridden_by_sublayer(self):
        stage = MockUsdStage()
        stage.author("/state", 0, "base")
        stage.create_delegate_sublayer("claude")
        stage.author_to_sublayer("claude", "/state", 0, "override")
        composed = stage.compose()
        assert composed[("/state", 0)] == "override"

    def test_no_cross_contamination(self):
        stage = MockUsdStage()
        stage.create_delegate_sublayer("a")
        stage.create_delegate_sublayer("b")
        stage.author_to_sublayer("a", "/only_a", 0, "a_value")
        assert stage.read_from_sublayer("b", "/only_a", 0) is None

    def test_compose_empty_sublayers(self):
        stage = MockUsdStage()
        stage.author("/base", 0, "val")
        composed = stage.compose()
        assert composed == {("/base", 0): "val"}

    def test_clear_clears_sublayers(self):
        stage = MockUsdStage()
        stage.create_delegate_sublayer("claude")
        stage.author_to_sublayer("claude", "/state", 0, "val")
        stage.clear()
        assert stage.read_from_sublayer("claude", "/state", 0) is None

    def test_deep_copy_isolation_in_sublayer(self):
        stage = MockUsdStage()
        stage.create_delegate_sublayer("claude")
        data = {"key": "original"}
        stage.author_to_sublayer("claude", "/state", 0, data)
        data["key"] = "mutated"
        val = stage.read_from_sublayer("claude", "/state", 0)
        assert val["key"] == "original"
