"""POST /api/sessions/{id}/coach: chat with the coach about a finished game.

The server loads THIS session and gives it to the tools: the model never chooses
which game it reads.
"""

from fastapi import APIRouter, HTTPException, status

from app import storage
from app.agent.game_data import build_game
from app.agent.loop import run_agent
from app.api.attempts import finished_game
from app.providers.llm import LLMUnavailable, get_llm
from app.schemas import CoachRequest, CoachResponse

router = APIRouter(prefix="/api", tags=["coach"])


@router.post("/sessions/{session_id}/coach", response_model=CoachResponse)
def ask_coach(session_id: str, request: CoachRequest):
    session, _ = finished_game(session_id)  # 404 unknown, 409 not finished
    game = build_game(session, storage.load_attempts(session.session_id))
    llm, degraded = get_llm()
    try:
        return run_agent(request.message, request.history, game, llm, degraded)
    except LLMUnavailable:
        # Quota, network, bad key...: the details are in the log, never in the response.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "The coach is busy, try again in a moment.")
