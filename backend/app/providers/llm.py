"""The language models behind the coach: GroqLLM (real) and MockLLM (offline), same method.

Both return OUR small LLMReply object, never Groq's own object: the agent loop doesn't
know or care which one answered (same idea as MockProvider / HfProvider in TP1).
"""

import logging
import re
import time
from dataclasses import dataclass, field

import groq

from app import config

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    id: str  # each tool result must be sent back with the id of ITS call
    name: str
    arguments: str  # a JSON *string*, exactly as the model wrote it (may be invalid!)


@dataclass
class LLMReply:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    # True when the model wrote a broken tool call (e.g. "compare Attempts") that Groq refused.
    # That's the model's typo, not an outage: the loop tells the model and lets it try again.
    invalid_tool_call: bool = False


class LLMUnavailable(Exception):
    """The model can't be reached (quota, network...). The route turns it into a 503."""


def remove_thinking(text: str) -> str:
    """Some models (qwen) write their reasoning between <think> tags: the player
    must only see the answer."""
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()


class GroqLLM:
    name = "groq"

    def __init__(self, api_key: str, model: str):
        self.client = groq.Groq(api_key=api_key)
        self.model = model

    def call_api(self, messages, tools):
        """One request to Groq, retried on 429 "too many requests". Never leaks Groq's text."""
        for attempt in range(config.LLM_RETRIES + 1):
            try:
                return self.client.chat.completions.create(
                    model=self.model, messages=messages, tools=tools,
                    tool_choice="auto", temperature=config.LLM_TEMPERATURE)
            except groq.RateLimitError:
                logger.warning("Groq rate limit (attempt %d)", attempt + 1)
                time.sleep(config.LLM_RETRY_WAIT_SECONDS * (attempt + 1))
            except groq.BadRequestError as error:
                # Groq checks tool names itself and answers 400 "tool_use_failed" when the
                # model invents one. Found in the benchmark: qwen wrote "compare Attempts".
                if "tool_use_failed" in str(getattr(error, "body", "")):
                    logger.warning("the model wrote an invalid tool call")
                    return None
                logger.error("Groq call failed: %s", type(error).__name__)
                raise LLMUnavailable() from error
            except groq.GroqError as error:
                # Bad key, network down, model not available...: details go to the log only.
                logger.error("Groq call failed: %s", type(error).__name__)
                raise LLMUnavailable() from error
        raise LLMUnavailable()

    def chat(self, messages: list[dict], tools: list[dict]) -> LLMReply:
        response = self.call_api(messages, tools)
        if response is None:
            return LLMReply(invalid_tool_call=True)
        message = response.choices[0].message
        calls = []
        for call in message.tool_calls or []:
            calls.append(ToolCall(id=call.id, name=call.function.name,
                                  arguments=call.function.arguments))
        return LLMReply(text=remove_thinking(message.content), tool_calls=calls)


def get_llm(model: str | None = None):
    """Returns (llm, degraded). "real" mode without a key falls back to the mock,
    and says so (degraded=True), so a demo never hides that it isn't the real model."""
    # Imported here, not at the top: mock_llm.py imports this file, and two files that
    # import each other at the top crash Python ("circular import").
    from app.providers.mock_llm import MockLLM

    if config.INFERENCE_MODE == "real":
        if config.GROQ_API_KEY:
            return GroqLLM(config.GROQ_API_KEY, model or config.LLM_MODEL), False
        logger.warning("INFERENCE_MODE=real but GROQ_API_KEY is empty: using the mock")
        return MockLLM(), True
    return MockLLM(), False
