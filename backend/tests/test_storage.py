"""Tests for storage.py: save, load, and the path traversal protection."""

import pytest

from app import storage
from app.schemas import Section, SessionResponse


def make_session(session_id):
    section = Section(index=0, start_s=0, end_s=1.0, audio_url="/x")
    return SessionResponse(
        session_id=session_id, source="catalog", meme_title="Test", sections=[section]
    )


def test_save_then_load_gives_the_same_session():
    session_id = storage.new_session_id()
    storage.create_session_dir(session_id)
    original = make_session(session_id)
    storage.save_session(original)
    assert storage.load_session(session_id) == original


def test_path_traversal_id_is_not_found():
    with pytest.raises(storage.SessionNotFound):
        storage.load_session("../hack")


def test_unknown_uuid_is_not_found():
    with pytest.raises(storage.SessionNotFound):
        storage.load_session(storage.new_session_id())


def test_delete_session_removes_the_folder():
    session_id = storage.new_session_id()
    folder = storage.create_session_dir(session_id)
    storage.delete_session(session_id)
    assert not folder.exists()
