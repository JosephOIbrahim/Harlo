"""Tests for Sprint 4 Phase 3: Live .usda files and sublayer composition.

Verifies:
- Real .usda files on disk contain authored cognitive state
- Delegate sublayers are real .usda files
- Sublayer composition resolves correctly
- export_flat produces single resolved .usda
- .usda content is human-readable
"""

import os
import pytest

pxr = pytest.importorskip("pxr", reason="USD pxr bindings not available for this Python version")

from src.cognitive_stage import CognitiveStage
from src.cognitive_engine import CognitiveEngine
from src.mock_cogexec import evaluate_dag
from src.schemas import (
    CognitiveObservation,
    DynamicsBlock,
    Momentum,
    StateBlock,
)


class TestLiveUSDA:
    def test_usda_file_on_disk(self, tmp_path):
        """Root .usda exists with prim hierarchy."""
        stage = CognitiveStage(stage_dir=str(tmp_path))
        root_file = tmp_path / "harlo.usda"
        assert root_file.exists()
        content = root_file.read_text()
        assert "#usda" in content

    def test_authored_state_in_usda(self, tmp_path):
        """Authored state visible in .usda text."""
        stage = CognitiveStage(stage_dir=str(tmp_path))
        obs = CognitiveObservation(
            exchange_index=0,
            state=StateBlock(momentum=Momentum.ROLLING),
        )
        stage.author("/state", 0, obs)
        stage.save()

        text = stage.get_usda_text()
        assert "ROLLING" in text or "momentum" in text.lower() or "state" in text

    def test_delegate_sublayer_usda_on_disk(self, tmp_path):
        """Delegate sublayer creates real .usda file."""
        stage = CognitiveStage(stage_dir=str(tmp_path))
        stage.create_delegate_sublayer("claude")
        stage.author_to_sublayer("claude", "/delegates/claude", 0, {"status": "active"})
        stage.save()

        claude_file = tmp_path / "delegates" / "claude.usda"
        assert claude_file.exists()
        content = claude_file.read_text()
        assert len(content) > 0

    def test_both_delegate_sublayers(self, tmp_path):
        """Both claude and claude_code create separate .usda files."""
        stage = CognitiveStage(stage_dir=str(tmp_path))
        stage.create_delegate_sublayer("claude")
        stage.create_delegate_sublayer("claude_code")
        stage.author_to_sublayer("claude", "/delegates/claude", 0, {"from": "claude"})
        stage.author_to_sublayer("claude_code", "/delegates/claude_code", 0, {"from": "code"})
        stage.save()

        assert (tmp_path / "delegates" / "claude.usda").exists()
        assert (tmp_path / "delegates" / "claude_code.usda").exists()

    def test_sublayer_composition_resolves(self, tmp_path):
        """Composed stage merges base + sublayers correctly."""
        stage = CognitiveStage(stage_dir=str(tmp_path))
        stage.author("/state", 0, {"base": True})
        stage.create_delegate_sublayer("claude")
        stage.author_to_sublayer("claude", "/delegates/claude", 0, {"delegate": True})
        composed = stage.compose()
        assert len(composed) >= 2

    def test_export_flat_produces_single_file(self, tmp_path):
        """export_flat creates one resolved .usda."""
        stage = CognitiveStage(stage_dir=str(tmp_path))
        stage.author("/state", 0, CognitiveObservation())
        stage.create_delegate_sublayer("claude")
        stage.author_to_sublayer("claude", "/delegates/claude", 0, {"ok": True})
        stage.save()

        flat_path = str(tmp_path / "flat_export.usda")
        stage.export_flat(flat_path)
        assert os.path.exists(flat_path)
        content = open(flat_path).read()
        assert "#usda" in content

    def test_dag_on_real_usd_stage(self, tmp_path):
        """Full DAG evaluation works on real USD stage."""
        stage = CognitiveStage(stage_dir=str(tmp_path))
        obs = CognitiveObservation(
            exchange_index=0,
            dynamics=DynamicsBlock(
                tasks_completed=5,
                exchange_velocity=0.6,
                topic_coherence=0.8,
            ),
        )
        result = evaluate_dag(stage, obs, 0)
        assert result is not None
        assert result.state.momentum in list(Momentum)

    def test_multi_exchange_on_real_usd(self, tmp_path):
        """10-exchange trajectory on real USD stage."""
        stage = CognitiveStage(stage_dir=str(tmp_path))
        for i in range(10):
            obs = CognitiveObservation(
                exchange_index=i,
                dynamics=DynamicsBlock(
                    tasks_completed=min(i, 5),
                    exchange_velocity=min(i * 0.1, 1.0),
                    topic_coherence=0.8,
                    session_exchange_count=i,
                ),
            )
            result = evaluate_dag(stage, obs, i)
        assert stage.max_exchange_index() == 9
        stage.save()

    def test_persist_and_reopen(self, tmp_path):
        """State persists across stage instances."""
        stage1 = CognitiveStage(stage_dir=str(tmp_path))
        obs = CognitiveObservation(
            exchange_index=42,
            state=StateBlock(momentum=Momentum.PEAK),
        )
        stage1.author("/state", 42, obs)
        stage1.save()
        del stage1

        stage2 = CognitiveStage(stage_dir=str(tmp_path))
        result = stage2.read("/state", 42)
        assert result is not None
        assert result.state.momentum == Momentum.PEAK

    def test_engine_with_real_usd(self, tmp_path):
        """CognitiveEngine works with CognitiveStage backend."""
        from src.cognitive_engine import CognitiveEngine
        from src.cognitive_stage import CognitiveStage

        # Monkey-patch stage into engine
        engine = CognitiveEngine()
        engine.stage = CognitiveStage(stage_dir=str(tmp_path), in_memory=True)
        engine.stage.create_delegate_sublayer("claude")
        engine.stage.create_delegate_sublayer("claude_code")

        result = engine.process_exchange("twin_coach", {"message": "test"})
        assert result["cognitive_context"] != ""
        assert result["delegate_id"] == "claude"
        engine.close()
