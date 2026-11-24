"""The agent loop: the model decides which tools to call, our code runs them, until it answers.

Same structure as executer_agent in Atelier 5:
  ask the model → it asks for tools → we run them and send the results back → ... → text answer.
At most max_tours model calls, then a polite fallback (aborted = True).
"""

import json

from app import config
from app.agent.executor import execute_tool
from app.agent.prompts import FALLBACK_REPLY, INVALID_TOOL_CALL_NOTE, SYSTEM_PROMPT
from app.agent.tools import tool_schemas
from app.schemas import ChatTurn, CoachResponse, PendingAction


def build_messages(message: str, history: list[ChatTurn]) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Only the last turns: older ones cost tokens and rarely matter.
    for turn in history[-config.COACH_HISTORY_TURNS:]:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": message})
    return messages


def assistant_message(reply) -> dict:
    """The model's message WITH its tool calls, for the conversation.
    It must come before the tool results, or the API answers 400."""
    calls = []
    for call in reply.tool_calls:
        calls.append({"id": call.id, "type": "function",
                      "function": {"name": call.name, "arguments": call.arguments}})
    return {"role": "assistant", "content": reply.text or "", "tool_calls": calls}


def run_agent(message, history, game, llm, degraded=False, max_tours=None) -> CoachResponse:
    max_tours = max_tours or config.COACH_MAX_TOURS
    messages = build_messages(message, history)
    schemas = tool_schemas(len(game["sections"]))
    tools_used = []
    pending_action = None

    for tour in range(1, max_tours + 1):
        reply = llm.chat(messages, schemas)
        if reply.invalid_tool_call:
            # Like a tool error: tell the model, let it try again (this tour still counts).
            messages.append({"role": "system", "content": INVALID_TOOL_CALL_NOTE})
            continue
        if not reply.tool_calls:
            return CoachResponse(reply=reply.text or FALLBACK_REPLY, tools_used=tools_used,
                                 pending_action=pending_action, turns=tour, aborted=False,
                                 provider=llm.name, model=llm.model, degraded=degraded)
        messages.append(assistant_message(reply))
        for call in reply.tool_calls:
            result = execute_tool(call.name, call.arguments, game)
            tools_used.append(call.name)
            if call.name == "propose_retry" and "error" not in result:
                # The API counts sections from 0; the coach from 1, like the player.
                pending_action = PendingAction(type="retry_section",
                                               section_index=result["section_number"] - 1)
            # Each result carries the id of ITS call: with 2 calls, no mix-up.
            # ensure_ascii=False keeps accents and Arabic readable.
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(result, ensure_ascii=False)})
    # max_tours model calls and still no final answer: stop, and say so politely.
    return CoachResponse(reply=FALLBACK_REPLY, tools_used=tools_used,
                         pending_action=pending_action, turns=max_tours, aborted=True,
                         provider=llm.name, model=llm.model, degraded=degraded)
