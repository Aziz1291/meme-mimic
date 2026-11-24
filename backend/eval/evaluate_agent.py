"""Benchmarks the coach on 20 scenarios (eval/agent_tasks.csv) with a FROZEN game.

Decision metric (chosen before running): task success = right tools AND right answer.
  right tools  : every expected tool was called, and no forbidden one ("*" = any tool)
  right answer : every required fact (a number) appears in the reply
Also: unrequested actions (propose_retry when not expected, target 0), aborts,
the 2×2 diagnosis, and the coach's latency (min / median / max).

Usage (inside Docker):
    python -m eval.evaluate_agent mock                 ← offline: checks the plumbing only
    python -m eval.evaluate_agent qwen/qwen3.8-27b     ← needs GROQ_API_KEY in backend/.env
    python -m eval.evaluate_agent openai/gpt-oss-20b   ← the second model, same everything
Saves eval/results/agent_<model>_<date>_<time>.txt and .json.
"""

import csv
import json
import statistics
import sys
import time
from datetime import datetime

from app import config
from app.agent.game_data import build_game
from app.agent.loop import run_agent
from app.providers.llm import GroqLLM, LLMUnavailable
from app.providers.mock_llm import MockLLM
from app.schemas import AttemptRecord, CoachResponse, SessionResponse
from eval.common import EVAL_DIR, save_result

FIXTURE_DIR = EVAL_DIR / "fixtures" / "demo_session"
TASKS_PATH = EVAL_DIR / "agent_tasks.csv"
PAUSE_SECONDS = 6  # Groq free tier: ~30 requests/min, and a task can need 2–3 calls


def load_frozen_game() -> dict:
    session = SessionResponse.model_validate_json((FIXTURE_DIR / "session.json").read_text())
    raw_attempts = json.loads((FIXTURE_DIR / "attempts.json").read_text())
    attempts = [AttemptRecord.model_validate(raw) for raw in raw_attempts]
    return build_game(session, attempts)


def split_list(cell: str) -> list[str]:
    return [item for item in cell.split("|") if item]


def judge(task: dict, response) -> dict:
    called = set(response.tools_used)
    expected = split_list(task["expected_tools"])
    forbidden = split_list(task["forbidden_tools"])
    if "*" in forbidden:
        forbidden_called = bool(called)
    else:
        forbidden_called = bool(called & set(forbidden))
    right_tools = set(expected) <= called and not forbidden_called
    right_answer = all(fact in response.reply for fact in split_list(task["required_facts"]))
    unrequested = "propose_retry" in called and "propose_retry" not in expected
    return {"right_tools": right_tools, "right_answer": right_answer,
            "success": right_tools and right_answer, "unrequested_action": unrequested}


def cell_2x2(result: dict) -> str:
    if result["right_tools"]:
        return "success" if result["right_answer"] else "writing failure"
    return "lucky" if result["right_answer"] else "tool-choice failure"


def make_llm(model: str):
    if model == "mock":
        return MockLLM()
    if not config.GROQ_API_KEY:
        raise SystemExit("GROQ_API_KEY is empty in backend/.env: add your key, or run with 'mock'.")
    return GroqLLM(config.GROQ_API_KEY, model)


class CountingLLM:
    """Wraps a model to count its invalid tool calls (a measured weakness, see the notes)."""

    def __init__(self, llm):
        self.llm = llm
        self.name = llm.name
        self.model = llm.model
        self.invalid_tool_calls = 0

    def chat(self, messages, tools):
        reply = self.llm.chat(messages, tools)
        if reply.invalid_tool_call:
            self.invalid_tool_calls += 1
        return reply


def failed_response(message: str) -> CoachResponse:
    """What we record when the model couldn't answer at all (the app would answer 503)."""
    return CoachResponse(reply=message, tools_used=[], turns=0, aborted=True,
                         provider="error", model="error")


def run_tasks(llm, game: dict, pause: float) -> list[dict]:
    with open(TASKS_PATH, newline="", encoding="utf-8") as file:
        tasks = list(csv.DictReader(file))
    results = []
    for task in tasks:
        started = time.perf_counter()
        before = llm.invalid_tool_calls
        try:
            response = run_agent(task["message"], [], game, llm)
        except LLMUnavailable:
            # One failed task, not a crashed benchmark.
            response = failed_response("(error: model unavailable)")
        latency_ms = (time.perf_counter() - started) * 1000
        result = judge(task, response)
        result.update({"id": task["id"], "category": task["category"], "message": task["message"],
                       "tools_used": response.tools_used, "reply": response.reply,
                       "aborted": response.aborted, "latency_ms": latency_ms,
                       "invalid_tool_calls": llm.invalid_tool_calls - before})
        result["cell"] = cell_2x2(result)
        results.append(result)
        time.sleep(pause)
    return results


def evaluate(model: str) -> str:
    llm = CountingLLM(make_llm(model))
    pause = 0 if model == "mock" else PAUSE_SECONDS
    results = run_tasks(llm, load_frozen_game(), pause)
    successes = sum(1 for result in results if result["success"])
    latencies = [result["latency_ms"] for result in results]
    cells = {name: sum(1 for r in results if r["cell"] == name)
             for name in ["success", "writing failure", "tool-choice failure", "lucky"]}
    lines = [f"=== Coach benchmark: {llm.name} / {llm.model} ({datetime.now():%Y-%m-%d %H:%M}) ===",
             f"task success      : {successes} / {len(results)}   ← decision metric",
             f"right tools       : {sum(r['right_tools'] for r in results)} / {len(results)}",
             f"right answer      : {sum(r['right_answer'] for r in results)} / {len(results)}",
             f"unrequested action: {sum(r['unrequested_action'] for r in results)}   (target: 0)",
             f"aborts (max_tours): {sum(r['aborted'] for r in results)}",
             f"invalid tool calls: {llm.invalid_tool_calls}   (refused by Groq, model corrected)",
             f"latency per task  : min {min(latencies):.0f} ms · median "
             f"{statistics.median(latencies):.0f} ms · max {max(latencies):.0f} ms",
             "", "2×2 diagnosis: " + ", ".join(f"{name} {count}" for name, count in cells.items()),
             "", "Failed tasks:"]
    for result in results:
        if not result["success"]:
            lines.append(f"  #{result['id']} [{result['category']}] {result['message']!r} → "
                         f"tools={result['tools_used']} ({result['cell']})")
            lines.append(f"      reply: {result['reply'][:150]!r}")
    lines += ["", f"temperature={config.LLM_TEMPERATURE}, max_tours={config.COACH_MAX_TOURS}"]
    text = "\n".join(lines)
    safe_model = llm.model.replace("/", "_")
    save_result(f"agent_{safe_model}_{datetime.now():%Y-%m-%d_%H%M}", text,
                {"provider": llm.name, "model": llm.model, "successes": successes,
                 "total": len(results), "cells": cells,
                 "invalid_tool_calls": llm.invalid_tool_calls, "results": results})
    return text


if __name__ == "__main__":
    print(evaluate(sys.argv[1] if len(sys.argv) > 1 else "mock"))
