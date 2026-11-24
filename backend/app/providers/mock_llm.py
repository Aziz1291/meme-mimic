"""MockLLM: a scripted coach that works offline, with no key and no quota.

It picks a tool from keywords in the player's message, then turns the tool's result into
a sentence. Deterministic: the same message always gives the same answer.
Used in mock mode, in tests and in the demo without internet.
It is NOT smart: its benchmark score only proves the plumbing works, not the coaching.
"""

import json
import re

from app.providers.llm import LLMReply, ToolCall

OFF_TOPIC = ["weather", "homework", "poem", "recipe", "news", "football", "code", "math"]
OFF_TOPIC_REPLY = "I'm your Meme Mimic coach: I can only talk about your game and your scores."
PRIVACY_REPLY = "Sorry, I can only see your own game, not anyone else's."
SCORING_REPLY = ("Your score mixes 4 things: sound (the color of your voice), melody (how your "
                 "voice goes up and down), loud/quiet moments, and length.")
WEAK_POINT_WORDS = {
    "melody": ["melody", "pitch", "tune", "note"],
    "timbre": ["timbre", "sound", "voice", "tone"],
    "loudness": ["loud", "quiet", "volume", "energy"],
    "rhythm": ["rhythm", "speed", "fast", "slow", "length", "long", "short"],
}


def first_number(text: str) -> int | None:
    match = re.search(r"\d+", text)
    if match:
        return int(match.group())
    return None


def weak_point_in(text: str) -> str | None:
    for weak_point, words in WEAK_POINT_WORDS.items():
        if any(word in text for word in words):
            return weak_point
    return None


def tool_call(name: str, arguments: dict) -> LLMReply:
    return LLMReply(tool_calls=[ToolCall(id=f"mock_{name}", name=name,
                                         arguments=json.dumps(arguments))])


def choose(text: str) -> LLMReply:
    """Decides from the player's message: answer directly, or ask for one tool."""
    number = first_number(text)
    # Whole words: "hi" must not match inside "which" or "this".
    words = set(re.findall(r"[a-z]+", text))
    if words & set(OFF_TOPIC):
        return LLMReply(text=OFF_TOPIC_REPLY)
    if ("session" in text and number is not None) or "other player" in text or "someone else" in text:
        return LLMReply(text=PRIVACY_REPLY)
    if number is not None and ("retry" in text or "redo" in text):
        return tool_call("propose_retry", {"section_number": number})
    if "computed" in text or "how does the scor" in text or "how is the scor" in text:
        return LLMReply(text=SCORING_REPLY)
    if number is not None and ("improve" in text or "better" in text or "progress" in text):
        return tool_call("compare_attempts", {"section_number": number})
    if ("tip" in text or "advice" in text) and weak_point_in(text):
        return tool_call("get_tip", {"weak_point": weak_point_in(text)})
    if number is not None:
        return tool_call("get_section_scores", {"section_number": number})
    if any(word in text for word in ["worst", "best", "total", "score", "how did i do", "result"]):
        return tool_call("get_session_summary", {})
    if words & {"thanks", "thank", "thx"}:
        return LLMReply(text="You're welcome! Have fun with the next meme.")
    if words & {"hi", "hello", "hey"}:
        return LLMReply(text="Hi! Ask me about your scores, or for a tip.")
    return LLMReply(text="I can tell you your scores, compare your tries, or give you a tip.")


def describe(name: str, result: dict) -> str:
    """Turns one tool result into a sentence for the player."""
    if "error" in result:
        return "Sorry, I couldn't get that information."
    if name == "get_session_summary":
        return (f"Your total is {result['total_percent']}%. Your best piece was "
                f"{result['best']['section_number']} ({result['best']['percent']}%), your weakest "
                f"was piece {result['worst']['section_number']} ({result['worst']['percent']}%).")
    if name == "get_section_scores":
        parts = ", ".join(f"{key} {value}%" for key, value in result["sub_scores_percent"].items())
        return f"Piece {result['section_number']}: {result['percent']}% ({parts})."
    if name == "compare_attempts":
        return (f"Piece {result['section_number']}: first try {result['first_percent']}%, "
                f"latest {result['latest_percent']}% ({result['change_points']:+d} points).")
    if name == "get_tip":
        return result["tip"]
    if name == "propose_retry":
        return f"OK! Click the button to retry piece {result['section_number']}."
    return "Done."


class MockLLM:
    name = "mock"
    model = "mock-coach"

    def chat(self, messages: list[dict], tools: list[dict]) -> LLMReply:
        last = messages[-1]
        if last["role"] != "tool":
            return choose(last["content"].lower())
        # The tool results are back: find which tool each id belonged to, then answer.
        names_by_id = {}
        for message in messages:
            for call in message.get("tool_calls", []):
                names_by_id[call["id"]] = call["function"]["name"]
        sentences = []
        for message in messages:
            if message["role"] == "tool":
                sentences.append(describe(names_by_id[message["tool_call_id"]],
                                          json.loads(message["content"])))
        return LLMReply(text=sentences[-1])
