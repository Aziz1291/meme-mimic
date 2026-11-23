"""The meme catalog: reads catalog.json and serves GET /api/memes.

catalog.json is checked with Pydantic, so a typo fails with a clear message, not in the middle of a game.
"""

import json

from fastapi import APIRouter

from app import config
from app.schemas import CatalogMeme, MemeInfo

router = APIRouter(prefix="/api", tags=["memes"])


def load_catalog() -> list[CatalogMeme]:
    """Reads and validates catalog.json. Raises an error if a meme is badly written."""
    raw_memes = json.loads(config.CATALOG_PATH.read_text(encoding="utf-8"))
    memes = []
    for raw_meme in raw_memes:
        memes.append(CatalogMeme.model_validate(raw_meme))
    return memes


def find_meme(meme_id: str) -> CatalogMeme | None:
    for meme in load_catalog():
        if meme.id == meme_id:
            return meme
    return None


@router.get("/memes", response_model=list[MemeInfo])
def list_memes():
    memes = []
    for meme in load_catalog():
        memes.append(MemeInfo(meme_id=meme.id, title=meme.title, section_count=len(meme.sections)))
    return memes
