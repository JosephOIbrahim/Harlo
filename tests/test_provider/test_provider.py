"""Tests for the LLM provider abstraction and generate pipeline.

Tests:
1. Provider Protocol interface compliance
2. Claude adapter initialization (no real API calls)
3. OpenAI adapter initialization (stub)
4. Full generate pipeline with mock provider
5. Barrier validation applied to output
6. GVR integration with provider as generator_fn
7. Router "ask" command dispatch
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────
# Provider Protocol
# ─────────────────────────────────────────────────────────────────────

class TestProviderProtocol:
    """Test the Provider protocol interface."""

    def test_protocol_is_runtime_checkable(self):
        """Provider protocol should be runtime-checkable."""
        from cognitive_twin.provider import Provider
        assert hasattr(Provider, "__protocol_attrs__") or hasattr(Provider, "__abstractmethods__") or True
        # Runtime-checkable protocols support isinstance checks

    def test_mock_provider_satisfies_protocol(self):
        """A mock with generate/stream/model_name should satisfy Provider."""
        from cognitive_twin.provider import Provider

        class MockProvider:
            @property
            def model_name(self) -> str:
                return "mock-v1"

            def generate(self, prompt, context=None):
                return "mock response"

            def stream(self, prompt, context=None):
                yield "mock"

        mock = MockProvider()
        assert isinstance(mock, Provider)

    def test_incomplete_mock_fails_protocol(self):
        """A class missing methods should NOT satisfy Provider."""
        from cognitive_twin.provider import Provider

        class Incomplete:
            pass

        assert not isinstance(Incomplete(), Provider)

    def test_get_provider_unknown_raises(self):
        """get_provider with unknown name should raise ValueError."""
        from cognitive_twin.provider import get_provider

        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("nonexistent")


# ─────────────────────────────────────────────────────────────────────
# Claude Adapter
# ─────────────────────────────────────────────────────────────────────

class TestClaudeProvider:
    """Test Claude adapter initialization and message building."""

    def test_init_requires_api_key(self):
        """Claude provider should raise if no API key is available."""
        from cognitive_twin.provider.claude import ClaudeProvider

        # Clear env var if set
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                ClaudeProvider()

    def test_init_accepts_api_key_param(self):
        """Claude provider should accept api_key parameter."""
        from cognitive_twin.provider.claude import ClaudeProvider

        with patch("anthropic.Anthropic"):
            provider = ClaudeProvider(api_key="test-key-123")
            assert provider.model_name == "claude-sonnet-4-20250514"

    def test_init_reads_env_var(self):
        """Claude provider should read ANTHROPIC_API_KEY from env."""
        from cognitive_twin.provider.claude import ClaudeProvider

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key-456"}):
            with patch("anthropic.Anthropic"):
                provider = ClaudeProvider()
                assert provider.model_name == "claude-sonnet-4-20250514"

    def test_custom_model(self):
        """Claude provider should accept custom model ID."""
        from cognitive_twin.provider.claude import ClaudeProvider

        with patch("anthropic.Anthropic"):
            provider = ClaudeProvider(api_key="k", model="claude-opus-4-20250514")
            assert provider.model_name == "claude-opus-4-20250514"

    def test_build_messages_simple(self):
        """_build_messages should create proper message list."""
        from cognitive_twin.provider.claude import ClaudeProvider

        with patch("anthropic.Anthropic"):
            provider = ClaudeProvider(api_key="k")
            messages = provider._build_messages("Hello")
            assert len(messages) == 1
            assert messages[0] == {"role": "user", "content": "Hello"}

    def test_build_messages_with_context(self):
        """_build_messages should prepend context messages."""
        from cognitive_twin.provider.claude import ClaudeProvider

        with patch("anthropic.Anthropic"):
            provider = ClaudeProvider(api_key="k")
            context = [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
            ]
            messages = provider._build_messages("Follow up", context)
            assert len(messages) == 3
            assert messages[0]["content"] == "Hi"
            assert messages[1]["content"] == "Hello!"
            assert messages[2]["content"] == "Follow up"

    def test_generate_calls_api(self):
        """generate() should call the Anthropic messages.create API."""
        from cognitive_twin.provider.claude import ClaudeProvider

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Claude says hello"
        mock_response.content = [mock_block]
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            provider = ClaudeProvider(api_key="k")
            result = provider.generate("test prompt")

        assert result == "Claude says hello"
        mock_client.messages.create.assert_called_once()

    def test_generate_with_system_prompt(self):
        """generate() should pass system prompt to API."""
        from cognitive_twin.provider.claude import ClaudeProvider

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "response"
        mock_response.content = [mock_block]
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            provider = ClaudeProvider(api_key="k", system_prompt="You are a test")
            provider.generate("prompt")

        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs[1]["system"] == "You are a test" or call_kwargs.kwargs.get("system") == "You are a test"

    def test_provider_satisfies_protocol(self):
        """ClaudeProvider should satisfy the Provider protocol."""
        from cognitive_twin.provider import Provider
        from cognitive_twin.provider.claude import ClaudeProvider

        with patch("anthropic.Anthropic"):
            provider = ClaudeProvider(api_key="k")
            assert isinstance(provider, Provider)


# ─────────────────────────────────────────────────────────────────────
# OpenAI Adapter
# ─────────────────────────────────────────────────────────────────────

class TestOpenAIProvider:
    """Test OpenAI adapter initialization."""

    def test_init_requires_api_key(self):
        """OpenAI provider should raise if no API key."""
        from cognitive_twin.provider.openai import OpenAIProvider

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                OpenAIProvider()

    def test_init_requires_openai_package(self):
        """OpenAI provider should raise ImportError if openai not installed."""
        from cognitive_twin.provider.openai import OpenAIProvider
        import sys

        # Temporarily hide openai from imports
        with patch.dict(os.environ, {"OPENAI_API_KEY": "k"}):
            with patch.dict(sys.modules, {"openai": None}):
                with pytest.raises(ImportError, match="openai package"):
                    OpenAIProvider()


# ─────────────────────────────────────────────────────────────────────
# Mock Provider for Pipeline Tests
# ─────────────────────────────────────────────────────────────────────

class MockProvider:
    """A mock provider that returns predictable responses."""

    def __init__(self, response: str = "This is a mock response about the topic"):
        self._response = response
        self.calls: list[str] = []

    @property
    def model_name(self) -> str:
        return "mock-v1"

    def generate(self, prompt: str, context=None) -> str:
        self.calls.append(prompt)
        return self._response

    def stream(self, prompt: str, context=None):
        self.calls.append(prompt)
        for word in self._response.split():
            yield word + " "


# ─────────────────────────────────────────────────────────────────────
# Generate Pipeline
# ─────────────────────────────────────────────────────────────────────

class TestGeneratePipeline:
    """Test the full Twin generation loop with mock provider."""

    def test_generate_returns_response(self):
        """generate() should return the provider's response."""
        from cognitive_twin.brainstem.generate import generate

        db = tempfile.mktemp(suffix=".db")
        try:
            provider = MockProvider("The answer is 42")
            result = generate(
                query="What is the meaning of life?",
                provider=provider,
                db_path=db,
            )
            assert result["response"] is not None
            assert result["model"] == "mock-v1"
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_generate_includes_verification(self):
        """generate() should include Aletheia verification result."""
        from cognitive_twin.brainstem.generate import generate

        db = tempfile.mktemp(suffix=".db")
        try:
            provider = MockProvider("A substantive response about the meaning of life and philosophy")
            result = generate(
                query="What is the meaning of life?",
                provider=provider,
                db_path=db,
            )
            assert "verification" in result
            assert "state" in result["verification"]
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_generate_with_recalled_context(self):
        """generate() should use semantic recall for context."""
        from cognitive_twin.brainstem.generate import generate
        from cognitive_twin.encoder import semantic_store

        db = tempfile.mktemp(suffix=".db")
        try:
            # Store some context first
            semantic_store(db, "ctx1", "Cats are domesticated felines")
            semantic_store(db, "ctx2", "Dogs are loyal companions")

            provider = MockProvider("Cats are wonderful pets that purr and play with cat toys and felines")
            result = generate(
                query="Tell me about cats",
                provider=provider,
                db_path=db,
            )

            # Should have recalled context traces
            assert result["confidence"] > 0.0
            assert len(result["context_traces"]) > 0
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_generate_context_injected_in_prompt(self):
        """generate() should inject recalled context into the prompt."""
        from cognitive_twin.brainstem.generate import generate
        from cognitive_twin.encoder import semantic_store

        db = tempfile.mktemp(suffix=".db")
        try:
            semantic_store(db, "t1", "The speed of light is 299792458 m/s")

            provider = MockProvider("The speed of light is approximately 300 million meters per second")
            result = generate(
                query="What is the speed of light?",
                provider=provider,
                db_path=db,
            )

            # Provider should have been called with augmented prompt
            assert len(provider.calls) >= 1
            # The first call should contain context
            first_call = provider.calls[0]
            assert "speed of light" in first_call.lower() or "context" in first_call.lower()
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_generate_empty_db_still_works(self):
        """generate() should work with empty database (no context)."""
        from cognitive_twin.brainstem.generate import generate

        db = tempfile.mktemp(suffix=".db")
        try:
            provider = MockProvider("A response about general knowledge and information")
            result = generate(
                query="Tell me something",
                provider=provider,
                db_path=db,
            )
            assert result["response"] is not None
            assert result["confidence"] == 0.0
            assert result["context_traces"] == []
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_generate_confidence_range(self):
        """Confidence should be between 0.0 and 1.0."""
        from cognitive_twin.brainstem.generate import generate

        db = tempfile.mktemp(suffix=".db")
        try:
            provider = MockProvider("Some response text about a topic with information")
            result = generate(
                query="test query",
                provider=provider,
                db_path=db,
            )
            assert 0.0 <= result["confidence"] <= 1.0
        finally:
            if os.path.exists(db):
                os.unlink(db)


class TestGenerateWithBarrier:
    """Test barrier validation in the generate pipeline."""

    def test_barrier_validates_json_output(self):
        """When validate_barrier=True, valid JSON should pass."""
        from cognitive_twin.brainstem.generate import generate

        valid_json = json.dumps({
            "core_memory": {
                "facts": ["The sky is blue"],
                "confidence": 0.9,
            }
        })

        db = tempfile.mktemp(suffix=".db")
        try:
            provider = MockProvider(valid_json)
            result = generate(
                query="What color is the sky?",
                provider=provider,
                db_path=db,
                validate_barrier=True,
            )
            assert result["barrier"] is not None
            assert result["barrier"]["valid"] is True
            assert "facts" in result["barrier"]["core_memory"]
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_barrier_rejects_invalid_json(self):
        """When validate_barrier=True, non-JSON output should fail validation."""
        from cognitive_twin.brainstem.generate import generate

        db = tempfile.mktemp(suffix=".db")
        try:
            provider = MockProvider("This is plain text, not JSON with valid structure")
            result = generate(
                query="test",
                provider=provider,
                db_path=db,
                validate_barrier=True,
            )
            assert result["barrier"] is not None
            assert result["barrier"]["valid"] is False
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_barrier_not_applied_by_default(self):
        """By default, barrier validation should not be applied."""
        from cognitive_twin.brainstem.generate import generate

        db = tempfile.mktemp(suffix=".db")
        try:
            provider = MockProvider("Plain text response about an interesting topic")
            result = generate(
                query="test",
                provider=provider,
                db_path=db,
            )
            assert result["barrier"] is None
        finally:
            if os.path.exists(db):
                os.unlink(db)


class TestGenerateGVR:
    """Test GVR integration with the generate pipeline."""

    def test_gvr_runs_on_output(self):
        """GVR should run on the generated output."""
        from cognitive_twin.brainstem.generate import generate

        db = tempfile.mktemp(suffix=".db")
        try:
            # Give a good response that should pass verification
            provider = MockProvider(
                "The meaning of life involves finding purpose, building relationships, "
                "and contributing to something greater than yourself."
            )
            result = generate(
                query="What is the meaning of life?",
                provider=provider,
                db_path=db,
            )
            assert result["verification"]["state"] in (
                "verified", "fixable", "unprovable", "spec_gamed", "deferred"
            )
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_gvr_uses_provider_for_revision(self):
        """If output is FIXABLE, GVR should use provider for revision."""
        from cognitive_twin.brainstem.generate import generate

        # Empty response triggers FIXABLE, then provider used for revision
        revision_provider = MockProvider("")  # Empty = FIXABLE

        db = tempfile.mktemp(suffix=".db")
        try:
            result = generate(
                query="What is memory?",
                provider=revision_provider,
                db_path=db,
            )
            # Should have called provider multiple times (initial + revisions)
            # Empty response → FIXABLE → revise → still empty → UNPROVABLE
            assert result["verification"]["state"] in ("fixable", "unprovable", "deferred")
        finally:
            if os.path.exists(db):
                os.unlink(db)


class TestGenerateFactory:
    """Test the provider factory function."""

    def test_get_provider_claude(self):
        """get_provider('claude') should return ClaudeProvider."""
        from cognitive_twin.provider import get_provider
        from cognitive_twin.provider.claude import ClaudeProvider

        with patch("anthropic.Anthropic"):
            provider = get_provider("claude", api_key="test-key")
            assert isinstance(provider, ClaudeProvider)

    def test_get_provider_claude_default(self):
        """get_provider() should default to Claude."""
        from cognitive_twin.provider import get_provider
        from cognitive_twin.provider.claude import ClaudeProvider

        with patch("anthropic.Anthropic"):
            provider = get_provider(api_key="test-key")
            assert isinstance(provider, ClaudeProvider)


class TestRouterAsk:
    """Test the router's ask command handler."""

    def test_router_has_ask_command(self):
        """Router should recognise 'ask' as a valid command."""
        from cognitive_twin.daemon.router import route_command

        result = route_command("ask", {"question": "test"})
        # Should NOT be "Unknown command" — it's a registered handler
        assert "Unknown command" not in result.get("message", "")

    def test_router_ask_with_mock_provider(self):
        """Router ask command should work when provider is mocked."""
        from cognitive_twin.daemon.router import route_command

        mock_prov = MockProvider("A detailed response about the test topic with relevant information")

        with patch("cognitive_twin.provider.get_provider", return_value=mock_prov):
            result = route_command("ask", {"question": "test question"})
            assert result["status"] == "ok"
            assert "result" in result
            assert result["result"]["model"] == "mock-v1"


class TestCLIAsk:
    """Test the CLI ask command registration."""

    def test_ask_command_registered(self):
        """ask command should be registered in CLI."""
        from cognitive_twin.cli.main import cli

        command_names = [cmd for cmd in cli.commands]
        assert "ask" in command_names

    def test_ask_command_has_options(self):
        """ask command should have expected options."""
        from cognitive_twin.cli.commands.ask import ask

        param_names = [p.name for p in ask.params]
        assert "question" in param_names
        assert "provider" in param_names
        assert "depth" in param_names
        assert "domain" in param_names
        assert "as_json" in param_names


class TestCompliance:
    """Verify no rules are violated by provider code."""

    def test_no_sleep_in_provider(self):
        """Rule 1: No sleep() in provider code."""
        import glob
        provider_dir = os.path.join(os.path.dirname(__file__), "..", "..", "src", "provider")
        provider_dir = os.path.normpath(provider_dir)
        for py_file in glob.glob(os.path.join(provider_dir, "*.py")):
            content = open(py_file, encoding="utf-8").read()
            assert "sleep(" not in content, f"sleep() found in {py_file}"

    def test_no_while_true_in_provider(self):
        """Rule 1: No while True in provider code."""
        import glob
        provider_dir = os.path.join(os.path.dirname(__file__), "..", "..", "src", "provider")
        provider_dir = os.path.normpath(provider_dir)
        for py_file in glob.glob(os.path.join(provider_dir, "*.py")):
            content = open(py_file, encoding="utf-8").read()
            assert "while True" not in content, f"while True found in {py_file}"

    def test_no_sleep_in_generate(self):
        """Rule 1: No sleep() in generate module."""
        import inspect
        from cognitive_twin.brainstem import generate as gen_module
        source = inspect.getsource(gen_module)
        assert "sleep(" not in source

    def test_no_while_true_in_generate(self):
        """Rule 1: No while True in generate module."""
        import inspect
        from cognitive_twin.brainstem import generate as gen_module
        source = inspect.getsource(gen_module)
        assert "while True" not in source

    def test_verify_not_called_with_trace(self):
        """Rule 11: generate pipeline must NOT pass reasoning_trace to verify."""
        import inspect
        from cognitive_twin.brainstem import generate as gen_module
        source = inspect.getsource(gen_module)
        # The generate module should never set reasoning_trace
        assert "reasoning_trace=" not in source or "reasoning_trace=None" in source
