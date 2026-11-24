"""Tests for providers/llm.py, without calling Groq: a fake client plays Groq's part."""

import groq
import httpx
import pytest

from app import config
from app.providers.llm import GroqLLM, LLMUnavailable, get_llm, remove_thinking


def test_mock_mode_gives_the_mock():
    llm, degraded = get_llm()
    assert llm.name == "mock" and degraded is False


def test_real_mode_without_key_falls_back_and_says_so(monkeypatch):
    monkeypatch.setattr(config, "INFERENCE_MODE", "real")
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    llm, degraded = get_llm()
    assert llm.name == "mock" and degraded is True


def test_thinking_is_removed():
    assert remove_thinking("<think>hmm, 62...</think>Your total is 62%.") == "Your total is 62%."


def rate_limit_error():
    request = httpx.Request("POST", "https://api.groq.com")
    response = httpx.Response(429, request=request)
    return groq.RateLimitError("secret details from Groq", response=response, body=None)


class AlwaysRateLimited:
    """Stands in for groq.Groq().chat.completions: every call is a 429."""

    def __init__(self):
        self.attempts = 0

    def create(self, **arguments):
        self.attempts += 1
        raise rate_limit_error()


class RefusesToolCall:
    """Stands in for Groq refusing a misspelled tool name (seen with qwen: "compare Attempts")."""

    def create(self, **arguments):
        request = httpx.Request("POST", "https://api.groq.com")
        body = {"error": {"code": "tool_use_failed", "message": "attempted to call tool 'x'"}}
        raise groq.BadRequestError("400", response=httpx.Response(400, request=request), body=body)


def test_invalid_tool_call_is_not_an_outage():
    llm = GroqLLM(api_key="fake-key-for-tests", model="any")
    llm.client.chat.completions = RefusesToolCall()
    reply = llm.chat([{"role": "user", "content": "hi"}], [])
    assert reply.invalid_tool_call is True


def test_rate_limit_is_retried_then_becomes_unavailable(monkeypatch):
    monkeypatch.setattr(config, "LLM_RETRY_WAIT_SECONDS", 0)
    llm = GroqLLM(api_key="fake-key-for-tests", model="any")
    fake = AlwaysRateLimited()
    llm.client.chat.completions = fake
    with pytest.raises(LLMUnavailable) as error:
        llm.chat([{"role": "user", "content": "hi"}], [])
    assert fake.attempts == config.LLM_RETRIES + 1
    assert "secret details" not in str(error.value)  # Groq's text is never passed on
