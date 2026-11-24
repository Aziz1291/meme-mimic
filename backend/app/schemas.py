"""The contract: every shape of data the API accepts or returns.

FastAPI uses these Pydantic models to check requests (422 if bad) and to build the /docs page.
No provider names here (no Groq, no librosa): the contract doesn't depend on how things are computed.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# --- The meme catalog (data/memes/catalog.json) ---

class CatalogSection(BaseModel):
    """One hand-cut section of a catalog meme."""

    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    subtitle: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def end_after_start(self):
        # A section that ends before it starts is a typo in catalog.json.
        if self.end_s <= self.start_s:
            raise ValueError("end_s must be greater than start_s")
        return self


class CatalogMeme(BaseModel):
    """One meme in catalog.json."""

    id: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=100)
    # Only a plain file name (letters, digits, _ - .), so it can't point outside data/memes.
    file: str = Field(pattern=r"^[A-Za-z0-9_\-]+\.[A-Za-z0-9]+$")
    sections: list[CatalogSection] = Field(min_length=1, max_length=10)


# --- What the API sends and receives ---

class MemeInfo(BaseModel):
    """One line of the meme list shown on the home page."""

    meme_id: str
    title: str
    section_count: int = Field(ge=1)


class StartSessionRequest(BaseModel):
    """Body of POST /api/sessions."""

    meme_id: str = Field(min_length=1, max_length=50)


class Section(BaseModel):
    """One 1–2 second piece of the meme that the player imitates."""

    index: int = Field(ge=0)
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)
    subtitle: str | None = None
    audio_url: str


class SessionResponse(BaseModel):
    """A game: where the meme came from and its sections."""

    session_id: str
    # Only these two values are allowed (an enumeration).
    source: Literal["catalog", "upload"]
    meme_title: str
    sections: list[Section]


# --- Attempts and results ---

class Verdict(str, Enum):
    """A closed list: the frontend and the tests can rely on exactly these 3 values."""

    great = "great"
    good = "good"
    try_again = "try_again"


class RefusalReason(str, Enum):
    """Why a recording can't be scored. A closed list, not free text."""

    silent = "silent"
    too_short = "too_short"
    too_loud = "too_loud"
    too_noisy = "too_noisy"
    too_long = "too_long"


class SubScores(BaseModel):
    """The 4 parts of the score, each between 0 and 1."""

    timbre: float = Field(ge=0, le=1)
    # None means "this sound has no melody to compare" (a scream, a noise). It's not 0.
    melody: float | None = Field(default=None, ge=0, le=1)
    loudness: float = Field(ge=0, le=1)
    rhythm: float = Field(ge=0, le=1)


class AttemptResponse(BaseModel):
    """The answer to one imitation: always the same shape, scored or refused."""

    status: Literal["scored", "refused"]
    score: float | None = Field(default=None, ge=0, le=1)
    verdict: Verdict | None = None
    refusal_reason: RefusalReason | None = None
    message: str  # a sentence for the player
    sub_scores: SubScores | None = None
    scorer: str
    latency_ms: float = Field(ge=0)


class AttemptRecord(BaseModel):
    """One attempt as saved in attempts.json (not sent to the player as is)."""

    section_index: int = Field(ge=0)
    attempt_number: int = Field(ge=1)
    file_name: str
    result: AttemptResponse


class SectionResult(BaseModel):
    index: int = Field(ge=0)
    best_score: float = Field(ge=0, le=1)
    verdict: Verdict
    attempt_count: int = Field(ge=1)


class SessionResult(BaseModel):
    """The end of the game: total % and the best attempt of each section."""

    session_id: str
    total_percent: int = Field(ge=0, le=100)
    sections: list[SectionResult]


# --- The coach (chat on the Results page) ---

class ChatTurn(BaseModel):
    """One earlier message of the chat, sent back by the browser.

    Only "user" and "assistant": if the browser could send "system" messages,
    anyone could rewrite the coach's rules from the browser.
    """

    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class CoachRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class PendingAction(BaseModel):
    """An action the coach PROPOSES. Nothing happens until the player clicks to confirm."""

    type: Literal["retry_section"]
    section_index: int = Field(ge=0)


class CoachResponse(BaseModel):
    reply: str
    tools_used: list[str]
    pending_action: PendingAction | None = None
    turns: int = Field(ge=0)
    aborted: bool  # True when max_tours was reached without a final answer
    provider: str  # "mock" or "groq": never hidden
    model: str
    degraded: bool = False  # True when "real" was asked but the mock had to answer
