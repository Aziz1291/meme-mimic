"""The contract: every shape of data the API accepts or returns.

FastAPI uses these Pydantic models to check requests (422 if bad) and to build the /docs page.
No provider names here (no Groq, no librosa): the contract doesn't depend on how things are computed.
"""

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
