"""Tests for Sprint 3 Phase 1: HdCognitiveDelegate base + registry."""

import pytest

from src.delegate_base import (
    DelegateCapabilities,
    DelegateResult,
    HdCognitiveDelegate,
    TaskContext,
)
from src.delegate_registry import DelegateRegistry


# -------------------------------------------------------------------
# Concrete test delegate
# -------------------------------------------------------------------

class _TestDelegate(HdCognitiveDelegate):
    def __init__(self, delegate_id: str, tasks: list[str],
                 latency: str = "interactive", context: int = 200_000):
        self._id = delegate_id
        self._tasks = tasks
        self._latency = latency
        self._context = context
        self._synced = False

    def get_delegate_id(self) -> str:
        return self._id

    def get_capabilities(self) -> DelegateCapabilities:
        return DelegateCapabilities(
            delegate_id=self._id,
            supported_tasks=self._tasks,
            latency_class=self._latency,
            context_window=self._context,
        )

    def sync(self, stage_view, computed_values, context):
        self._synced = True

    def execute(self, task):
        return DelegateResult(response=f"executed:{task}", tokens_used=100)

    def commit_resources(self, result):
        return {"committed": True}


# -------------------------------------------------------------------
# ABC tests
# -------------------------------------------------------------------

class TestHdCognitiveDelegate:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            HdCognitiveDelegate()

    def test_concrete_delegate_works(self):
        d = _TestDelegate("test", ["reasoning"])
        assert d.get_delegate_id() == "test"
        assert d.get_status() == "active"

    def test_delegate_capabilities(self):
        d = _TestDelegate("test", ["reasoning", "coaching"], context=150_000)
        caps = d.get_capabilities()
        assert caps.delegate_id == "test"
        assert "reasoning" in caps.supported_tasks
        assert caps.effective_context == 150_000

    def test_effective_context_with_compression(self):
        caps = DelegateCapabilities(
            delegate_id="x", supported_tasks=[], latency_class="batch",
            context_window=200_000, compression_factor=4.0,
        )
        assert caps.effective_context == 800_000

    def test_sync_execute_commit(self):
        d = _TestDelegate("test", ["reasoning"])
        ctx = TaskContext(task_type="reasoning", signal_class="twin_coach")
        d.sync({}, {}, ctx)
        result = d.execute("test task")
        assert result.response == "executed:test task"
        committed = d.commit_resources(result)
        assert committed["committed"] is True

    def test_delegate_result_defaults(self):
        r = DelegateResult(response="ok")
        assert r.proposed_mutations == {}
        assert r.observation_data == {}
        assert r.tokens_used == 0


# -------------------------------------------------------------------
# Registry tests
# -------------------------------------------------------------------

class TestDelegateRegistry:
    def test_register_and_list(self):
        reg = DelegateRegistry()
        d = _TestDelegate("alpha", ["reasoning"])
        reg.register(d)
        caps = reg.list_delegates()
        assert len(caps) == 1
        assert caps[0].delegate_id == "alpha"

    def test_unregister(self):
        reg = DelegateRegistry()
        reg.register(_TestDelegate("alpha", ["reasoning"]))
        reg.unregister("alpha")
        assert len(reg.list_delegates()) == 0

    def test_select_empty_raises(self):
        reg = DelegateRegistry()
        with pytest.raises(ValueError):
            reg.select({})

    def test_select_by_coding(self):
        reg = DelegateRegistry()
        reg.register(_TestDelegate("claude", ["reasoning", "coaching"]))
        reg.register(_TestDelegate("code", ["code_generation", "debugging"]))
        result = reg.select({"requires_coding": True})
        assert result.get_delegate_id() == "code"

    def test_select_by_task(self):
        reg = DelegateRegistry()
        reg.register(_TestDelegate("claude", ["reasoning", "coaching"]))
        reg.register(_TestDelegate("code", ["code_generation"]))
        result = reg.select({"supported_tasks": ["coaching"]})
        assert result.get_delegate_id() == "claude"

    def test_select_by_latency(self):
        reg = DelegateRegistry()
        reg.register(_TestDelegate("fast", ["reasoning"], latency="realtime"))
        reg.register(_TestDelegate("slow", ["reasoning"], latency="batch"))
        result = reg.select({"latency_max": "interactive"})
        assert result.get_delegate_id() == "fast"

    def test_select_by_context_budget(self):
        reg = DelegateRegistry()
        reg.register(_TestDelegate("small", ["reasoning"], context=5_000))
        reg.register(_TestDelegate("big", ["reasoning"], context=200_000))
        result = reg.select({"context_budget": "heavy"})
        assert result.get_delegate_id() == "big"

    def test_select_fallback(self):
        """When no filters match exactly, falls back to first."""
        reg = DelegateRegistry()
        reg.register(_TestDelegate("only", ["niche_task"]))
        result = reg.select({"supported_tasks": ["nonexistent"]})
        assert result.get_delegate_id() == "only"

    def test_tiebreak_prefers_lower_latency(self):
        reg = DelegateRegistry()
        reg.register(_TestDelegate("a", ["reasoning"], latency="batch"))
        reg.register(_TestDelegate("b", ["reasoning"], latency="interactive"))
        result = reg.select({"supported_tasks": ["reasoning"]})
        assert result.get_delegate_id() == "b"

    def test_get_by_id(self):
        reg = DelegateRegistry()
        d = _TestDelegate("alpha", ["reasoning"])
        reg.register(d)
        assert reg.get("alpha") is d
        assert reg.get("nonexistent") is None
