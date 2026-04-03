"""Tests for the Observer background process."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from harlo.hot_store import HotStore


@pytest.fixture
def db_path(tmp_path):
    """Temporary database path."""
    return str(tmp_path / "observer_test.db")


@pytest.fixture
def hot_store(db_path):
    """Create a HotStore with temp DB."""
    return HotStore(db_path)


@pytest.fixture
def fake_model(tmp_path):
    """Create a fake model file for path existence checks."""
    model = tmp_path / "fake.onnx"
    model.write_bytes(b"fake")
    return str(model)


class TestObserverInit:
    """Tests for Observer initialization."""

    def test_init_missing_model_raises(self, db_path):
        """FileNotFoundError if model doesn't exist."""
        from harlo.observer import Observer

        with pytest.raises(FileNotFoundError):
            Observer(db_path, "nonexistent.onnx")

    def test_init_with_mock_encoder(self, db_path, fake_model):
        """Observer initializes with mocked encoder."""
        from harlo.observer import Observer

        with patch("harlo.encoder.onnx_encoder.OnnxEncoder"):
            observer = Observer(db_path, fake_model)
            assert observer.pending_count() == 0


class TestPromotionCycle:
    """Tests for run_promotion_cycle."""

    def test_empty_returns_zero(self, db_path, fake_model):
        """No pending traces → 0 promoted."""
        from harlo.observer import Observer

        with patch("harlo.encoder.onnx_encoder.OnnxEncoder"):
            observer = Observer(db_path, fake_model)
            assert observer.run_promotion_cycle() == 0

    def test_promotes_pending_traces(self, db_path, hot_store, fake_model):
        """Pending traces get promoted."""
        from harlo.observer import Observer

        hot_store.store("test trace 1")
        hot_store.store("test trace 2")

        with patch("harlo.encoder.onnx_encoder.OnnxEncoder") as mock_cls:
            encoder = MagicMock()
            encoder.encode_batch.return_value = [bytes(256), bytes(256)]
            mock_cls.return_value = encoder

            observer = Observer(db_path, fake_model)
            observer._hot_store = hot_store
            observer._pipeline._hot_store = hot_store

            count = observer.run_promotion_cycle()

        assert count == 2
        assert observer.pending_count() == 0

    def test_pending_count_reflects_state(self, db_path, hot_store, fake_model):
        """pending_count decreases after promotion."""
        from harlo.observer import Observer

        hot_store.store("trace a")
        hot_store.store("trace b")
        hot_store.store("trace c")

        with patch("harlo.encoder.onnx_encoder.OnnxEncoder") as mock_cls:
            encoder = MagicMock()
            encoder.encode_batch.return_value = [bytes(256), bytes(256)]
            mock_cls.return_value = encoder

            observer = Observer(db_path, fake_model)
            observer._hot_store = hot_store
            observer._pipeline._hot_store = hot_store

            assert observer.pending_count() == 3
            observer.run_promotion_cycle(batch_size=2)
            assert observer.pending_count() == 1


class TestObserverNoLLM:
    """Verify Observer has no LLM client dependencies."""

    def test_no_anthropic_import(self):
        """Observer module does not import anthropic."""
        import harlo.observer as obs

        source = open(obs.__file__).read()
        assert "anthropic" not in source
        assert "get_provider" not in source

    def test_no_provider_import(self):
        """Observer module does not import provider."""
        import harlo.observer as obs

        source = open(obs.__file__).read()
        assert "provider" not in source
