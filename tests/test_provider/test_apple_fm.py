"""Apple Foundation Models provider + on-device sincerity-gate swap.

The apple-fm-sdk is not installed in CI, so these tests cover the
graceful-missing-SDK path and the duck-typed LLM-judge swap in the
sincerity gate (using a fake provider — no SDK required).
"""

from __future__ import annotations

import pytest

from harlo.inquiry.sincerity_gate import SincerityClass, classify
from harlo.provider.apple_fm import AppleFoundationModelsProvider, is_available


def test_is_available_never_raises():
    assert is_available() in (True, False)


def test_provider_raises_clear_error_without_sdk():
    if is_available():
        pytest.skip("apple-fm-sdk is installed; skipping the missing-SDK path")
    with pytest.raises(RuntimeError, match="apple-fm-sdk"):
        AppleFoundationModelsProvider()


class _FakeProvider:
    def __init__(self, payload: str):
        self._payload = payload

    def generate(self, prompt: str, context=None) -> str:
        return self._payload


def test_sincerity_uses_llm_provider_when_supplied():
    fake = _FakeProvider('{"classification": "sarcastic", "confidence": 0.91}')
    res = classify("oh sure, that's just brilliant", llm_provider=fake)
    assert res.classification == SincerityClass.SARCASTIC
    assert res.confidence == pytest.approx(0.91)
    assert "llm_judge" in res.signals_matched


def test_sincerity_llm_output_wrapped_in_prose_is_parsed():
    fake = _FakeProvider(
        'Here is my judgement: {"classification":"uncertain","confidence":0.7} — done'
    )
    res = classify("hmm, hard to say", llm_provider=fake)
    assert res.classification == SincerityClass.UNCERTAIN


def test_sincerity_falls_back_to_heuristic_on_bad_llm_output():
    fake = _FakeProvider("not json at all, sorry")
    res = classify("yeah right", llm_provider=fake)  # heuristic catches 'right'
    assert res.classification == SincerityClass.SARCASTIC


def test_sincerity_default_heuristic_unchanged_without_provider():
    res = classify("maybe, i'm not sure")
    assert res.classification == SincerityClass.UNCERTAIN
