"""Tests for Sprint 3 Phase 2: HdClaude + HdClaudeCode delegates."""

import pytest

from src.delegate_base import DelegateResult, TaskContext
from src.delegate_claude import HdClaude
from src.delegate_claude_code import HdClaudeCode
from src.delegate_registry import DelegateRegistry


class TestHdClaude:
    def test_implements_interface(self):
        d = HdClaude()
        assert d.get_delegate_id() == "claude"
        assert d.get_status() == "active"

    def test_capabilities(self):
        caps = HdClaude().get_capabilities()
        assert "reasoning" in caps.supported_tasks
        assert "coaching" in caps.supported_tasks
        assert caps.latency_class == "interactive"
        assert caps.context_window == 200_000

    def test_sync_execute_returns_result(self):
        d = HdClaude()
        ctx = TaskContext(task_type="reasoning", signal_class="twin_coach", exchange_index=5)
        d.sync({}, {"momentum": 3, "burnout": 0, "energy": 3, "burst": 0}, ctx)
        result = d.execute("test task")
        assert isinstance(result, DelegateResult)
        assert "COGNITIVE STATE" in result.response
        assert "ROLLING" in result.response
        assert result.tokens_used > 0

    def test_coach_block_contains_state(self):
        d = HdClaude()
        ctx = TaskContext(task_type="coaching", signal_class="twin_coach", exchange_index=10)
        d.sync({}, {"momentum": 2, "burnout": 1, "energy": 2, "burst": 0,
                     "allostasis": {"load": 0.45}}, ctx)
        result = d.execute("coach")
        assert "BUILDING" in result.response
        assert "YELLOW" in result.response
        assert "0.450" in result.response

    def test_commit_resources(self):
        d = HdClaude()
        ctx = TaskContext(task_type="reasoning", signal_class="twin_coach")
        d.sync({}, {}, ctx)
        result = d.execute("task")
        mutations = d.commit_resources(result)
        assert "/delegate/claude/exchange_count" in mutations

    def test_observation_data(self):
        d = HdClaude()
        ctx = TaskContext(task_type="reasoning", signal_class="twin_coach")
        d.sync({}, {}, ctx)
        result = d.execute("task")
        assert result.observation_data["delegate_id"] == "claude"


class TestHdClaudeCode:
    def test_implements_interface(self):
        d = HdClaudeCode()
        assert d.get_delegate_id() == "claude_code"

    def test_capabilities(self):
        caps = HdClaudeCode().get_capabilities()
        assert "code_generation" in caps.supported_tasks
        assert "implementation" in caps.supported_tasks
        assert caps.latency_class == "batch"

    def test_sync_execute(self):
        d = HdClaudeCode()
        ctx = TaskContext(task_type="implementation", signal_class="twin_store",
                         requires_coding=True, exchange_index=3)
        d.sync({}, {"momentum": 2, "energy": 3}, ctx)
        result = d.execute("implement feature")
        assert "IMPLEMENTATION CONTEXT" in result.response
        assert result.tokens_used > 0

    def test_commit_resources(self):
        d = HdClaudeCode()
        ctx = TaskContext(task_type="implementation", signal_class="twin_store")
        d.sync({}, {}, ctx)
        result = d.execute("task")
        mutations = d.commit_resources(result)
        assert "/delegate/claude_code/exchange_count" in mutations


class TestRegistrySelection:
    def test_claude_selected_for_reasoning(self):
        reg = DelegateRegistry()
        reg.register(HdClaude())
        reg.register(HdClaudeCode())
        result = reg.select({"supported_tasks": ["reasoning"]})
        assert result.get_delegate_id() == "claude"

    def test_claude_code_selected_for_coding(self):
        reg = DelegateRegistry()
        reg.register(HdClaude())
        reg.register(HdClaudeCode())
        result = reg.select({"requires_coding": True})
        assert result.get_delegate_id() == "claude_code"

    def test_claude_selected_for_coaching(self):
        reg = DelegateRegistry()
        reg.register(HdClaude())
        reg.register(HdClaudeCode())
        result = reg.select({"supported_tasks": ["coaching"]})
        assert result.get_delegate_id() == "claude"

    def test_interactive_preferred_over_batch(self):
        reg = DelegateRegistry()
        reg.register(HdClaude())
        reg.register(HdClaudeCode())
        result = reg.select({"latency_max": "interactive"})
        assert result.get_delegate_id() == "claude"
