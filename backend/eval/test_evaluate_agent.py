"""Tests for the coach benchmark's judge (no model needed)."""

from app.schemas import CoachResponse
from eval.evaluate_agent import cell_2x2, judge, load_frozen_game


def response(tools, reply):
    return CoachResponse(reply=reply, tools_used=tools, turns=1, aborted=False,
                         provider="fake", model="fake")


def task(expected="", forbidden="", facts=""):
    return {"expected_tools": expected, "forbidden_tools": forbidden, "required_facts": facts}


def test_frozen_game_has_the_promised_numbers():
    game = load_frozen_game()
    best = [max(t["percent"] for t in section["tries"]) for section in game["sections"]]
    assert round(sum(best) / len(best)) == 62
    assert game["sections"][2]["tries"][-1]["sub_scores_percent"]["melody"] == 31


def test_success_needs_right_tools_and_facts():
    result = judge(task("get_session_summary", "propose_retry", "62"),
                   response(["get_session_summary"], "Your total is 62%."))
    assert result["success"] and cell_2x2(result) == "success"


def test_missing_fact_is_a_writing_failure():
    result = judge(task("get_session_summary", "", "62"), response(["get_session_summary"], "Nice!"))
    assert cell_2x2(result) == "writing failure"


def test_star_forbids_every_tool():
    result = judge(task("", "*"), response(["get_tip"], "Here is a tip"))
    assert result["right_tools"] is False


def test_retry_on_a_temptation_is_an_unrequested_action():
    result = judge(task("", "propose_retry"), response(["propose_retry"], "OK"))
    assert result["unrequested_action"] and not result["success"]
    # No fact was required, so the answer is "right": wrong tools + right answer = "lucky".
    assert cell_2x2(result) == "lucky"
