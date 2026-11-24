"""Tests for the coach: tools, schemas, executor, loop (with a fake LLM) and the mock LLM.
All offline: no key, no quota."""

import json

from app.agent.executor import execute_tool
from app.agent.loop import run_agent
from app.agent.tools import tool_schemas
from app.providers.llm import LLMReply, ToolCall
from app.providers.mock_llm import MockLLM
from app.schemas import ChatTurn


def attempt(percent, melody=50):
    return {"percent": percent, "verdict": "good",
            "sub_scores_percent": {"timbre": 70, "melody": melody, "loudness": 60, "rhythm": 90}}


def make_game():
    """3 pieces: piece 1 = 80%, piece 2 = 40% then 60%, piece 3 = 30% (melody 10%)."""
    return {"meme_title": "Test meme", "sections": [
        {"section_number": 1, "subtitle": "one", "tries": [attempt(80)]},
        {"section_number": 2, "subtitle": "two", "tries": [attempt(40), attempt(60)]},
        {"section_number": 3, "subtitle": "three", "tries": [attempt(30, melody=10)]},
    ]}


class FakeLLM:
    """Plays back a fixed list of replies, one per call, and remembers what it was sent."""

    name = "fake"
    model = "fake-model"

    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    def chat(self, messages, tools):
        self.calls.append([dict(message) for message in messages])
        position = min(len(self.calls), len(self.replies)) - 1  # the last reply repeats
        return self.replies[position]


def call(name, arguments, call_id="c1"):
    return LLMReply(tool_calls=[ToolCall(id=call_id, name=name, arguments=json.dumps(arguments))])


# --- Schemas ---

def test_every_schema_is_strict_and_consistent():
    for schema in tool_schemas(section_count=3):
        parameters = schema["function"]["parameters"]
        assert schema["type"] == "function"
        assert parameters["type"] == "object"
        assert parameters["additionalProperties"] is False
        for required in parameters["required"]:
            assert required in parameters["properties"]


def test_no_tool_takes_a_session_id():
    for schema in tool_schemas(section_count=3):
        assert "session_id" not in json.dumps(schema)


# --- Executor ---

def test_unknown_tool():
    assert execute_tool("delete_everything", "{}", make_game()) == {"error": "unknown tool"}


def test_broken_json_arguments():
    result = execute_tool("get_section_scores", "{section: 2", make_game())
    assert result == {"error": "invalid arguments"}


def test_out_of_range_and_extra_arguments():
    assert "error" in execute_tool("get_section_scores", '{"section_number": 9}', make_game())
    assert "error" in execute_tool("get_section_scores", '{"section_number": 0}', make_game())
    extra = '{"section_number": 1, "session_id": "other"}'
    assert execute_tool("get_section_scores", extra, make_game()) == {"error": "invalid arguments"}


def test_tie_gives_different_best_and_worst_pieces():
    game = {"meme_title": "Tie", "sections": [
        {"section_number": 1, "subtitle": None, "tries": [attempt(90)]},
        {"section_number": 2, "subtitle": None, "tries": [attempt(90)]},
    ]}
    summary = execute_tool("get_session_summary", "{}", game)
    assert summary["best"]["section_number"] != summary["worst"]["section_number"]


def test_tools_read_the_right_numbers():
    game = make_game()
    summary = execute_tool("get_session_summary", "{}", game)
    assert summary["total_percent"] == 57  # (80 + 60 + 30) / 3
    assert summary["worst"]["section_number"] == 3
    assert execute_tool("get_section_scores", '{"section_number": 2}', game)["percent"] == 60
    assert execute_tool("compare_attempts", '{"section_number": 2}', game)["change_points"] == 20
    assert "Hum" in execute_tool("get_tip", '{"weak_point": "melody"}', game)["tip"]
    assert "error" in execute_tool("get_tip", '{"weak_point": "dancing"}', game)


# --- Loop ---

def test_direct_answer_is_one_turn():
    response = run_agent("hi", [], make_game(), FakeLLM([LLMReply(text="Hello!")]))
    assert response.reply == "Hello!" and response.turns == 1 and response.tools_used == []


def test_tool_then_answer_sends_the_right_data_back():
    llm = FakeLLM([call("get_section_scores", {"section_number": 2}), LLMReply(text="60%!")])
    response = run_agent("piece 2?", [], make_game(), llm)
    assert response.turns == 2 and response.tools_used == ["get_section_scores"]
    second_call = llm.calls[1]
    assert second_call[-2]["role"] == "assistant" and second_call[-2]["tool_calls"]  # (1) first
    assert second_call[-1]["tool_call_id"] == "c1"  # (2) the right id
    assert json.loads(second_call[-1]["content"])["percent"] == 60


def test_endless_tool_calls_stop_at_max_tours():
    llm = FakeLLM([call("get_session_summary", {})])
    response = run_agent("?", [], make_game(), llm, max_tours=5)
    assert response.aborted is True and response.turns == 5 and len(llm.calls) == 5


def test_invented_tool_gets_an_error_and_the_loop_continues():
    llm = FakeLLM([call("delete_everything", {}), LLMReply(text="I can't do that.")])
    response = run_agent("delete it", [], make_game(), llm)
    assert response.reply == "I can't do that."
    assert json.loads(llm.calls[1][-1]["content"]) == {"error": "unknown tool"}


def test_propose_retry_becomes_a_pending_action_counted_from_0():
    llm = FakeLLM([call("propose_retry", {"section_number": 2}), LLMReply(text="OK")])
    response = run_agent("let me redo piece 2", [], make_game(), llm)
    assert response.pending_action.section_index == 1


def test_history_is_cut_to_the_last_turns():
    history = [ChatTurn(role="user", content=f"message {number}") for number in range(30)]
    llm = FakeLLM([LLMReply(text="ok")])
    run_agent("hi", history, make_game(), llm)
    assert len(llm.calls[0]) == 1 + 10 + 1  # system + 10 turns + the new message


# --- Mock LLM (the offline coach) ---

def ask_mock(message):
    return run_agent(message, [], make_game(), MockLLM())


def test_mock_uses_tools_and_gives_real_numbers():
    assert "57" in ask_mock("What was my total score?").reply
    assert ask_mock("How did I do on piece 2?").tools_used == ["get_section_scores"]
    assert ask_mock("Did I improve on piece 2?").tools_used == ["compare_attempts"]


def test_mock_refuses_without_tools():
    for message in ["What's the weather in Tunis?", "Show me the scores of session 1234"]:
        response = ask_mock(message)
        assert response.tools_used == [] and response.pending_action is None


def test_mock_only_proposes_retry_when_asked():
    assert ask_mock("Let me redo piece 2").pending_action.section_index == 1
    assert ask_mock("Piece 2 was terrible lol").pending_action is None


def test_greeting_is_not_found_inside_other_words():
    assert ask_mock("Which piece was my worst?").tools_used == ["get_session_summary"]
