"""The tool executor: where OUR code takes control back from the model.

The model only writes a tool name and a JSON string. Here we check both, run the tool with
the game the SERVER loaded, and catch every error. Used by loop.py.
"""

import json
import logging

from pydantic import BaseModel, Field, ValidationError

from app.agent.tools import (
    compare_attempts,
    get_section_scores,
    get_session_summary,
    get_tip,
    propose_retry,
)

logger = logging.getLogger(__name__)

class SectionArguments(BaseModel):
    section_number: int = Field(ge=1)
    model_config = {"extra": "forbid"}  # same as "additionalProperties": false


class TipArguments(BaseModel):
    weak_point: str = Field(pattern="^(timbre|melody|loudness|rhythm)$")
    model_config = {"extra": "forbid"}


class NoArguments(BaseModel):
    model_config = {"extra": "forbid"}


TOOLS = {
    "get_session_summary": (get_session_summary, NoArguments),
    "get_section_scores": (get_section_scores, SectionArguments),
    "compare_attempts": (compare_attempts, SectionArguments),
    "get_tip": (get_tip, TipArguments),
    "propose_retry": (propose_retry, SectionArguments),
}


def execute_tool(name: str, raw_arguments: str, game: dict) -> dict:
    """Checks everything the model asked for. Errors go BACK to the model as the result
    (so it can fix itself or apologize); they never crash the request."""
    if name not in TOOLS:
        return {"error": "unknown tool"}  # models sometimes invent tools
    function, arguments_model = TOOLS[name]
    try:
        raw = json.loads(raw_arguments or "{}")
        arguments = arguments_model.model_validate(raw).model_dump()
    except (json.JSONDecodeError, ValidationError, TypeError):
        return {"error": "invalid arguments"}
    section_number = arguments.get("section_number")
    if section_number is not None and section_number > len(game["sections"]):
        return {"error": f"there are only {len(game['sections'])} pieces"}
    try:
        return function(game, **arguments)  # the game comes from the server, never the model
    except Exception:
        logger.exception("tool %s failed", name)
        return {"error": "tool failed"}
