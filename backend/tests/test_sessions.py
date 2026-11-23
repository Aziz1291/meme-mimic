"""Tests for the meme and session routes: every path and every error.

A fake catalog (2 memes made of beeps) is built in a temporary folder for each test.
"""

import io
import json

import numpy as np
import pytest
import soundfile
from fastapi.testclient import TestClient

from app import config
from app.main import app
from tests.conftest import make_silence, make_tone

client = TestClient(app)


@pytest.fixture(autouse=True)
def fake_catalog(tmp_path, monkeypatch):
    memes_dir = tmp_path / "memes"
    memes_dir.mkdir()
    # 44 100 Hz stereo, like a file exported from Audacity.
    tone = make_tone(3.0, sample_rate=44100)
    soundfile.write(memes_dir / "beep.wav", np.column_stack([tone, tone]), 44100)
    catalog = [
        {"id": "meme_01", "title": "Beep", "file": "beep.wav", "sections": [
            {"start_s": 0.0, "end_s": 1.5, "subtitle": "first"},
            {"start_s": 1.5, "end_s": 3.0, "subtitle": "second"},
        ]},
        {"id": "meme_02", "title": "Broken", "file": "beep.wav", "sections": [
            {"start_s": 0.0, "end_s": 9.0},  # longer than the audio: a catalog mistake
        ]},
    ]
    (memes_dir / "catalog.json").write_text(json.dumps(catalog))
    monkeypatch.setattr(config, "MEMES_DIR", memes_dir)
    monkeypatch.setattr(config, "CATALOG_PATH", memes_dir / "catalog.json")


def upload(samples, name="clip.wav"):
    buffer = io.BytesIO()
    soundfile.write(buffer, samples, 16000, format="WAV")
    return client.post("/api/sessions/upload", files={"file": (name, buffer.getvalue())})


def test_list_memes():
    response = client.get("/api/memes")
    assert response.status_code == 200
    assert response.json()[0] == {"meme_id": "meme_01", "title": "Beep", "section_count": 2}


def test_start_catalog_session():
    response = client.post("/api/sessions", json={"meme_id": "meme_01"})
    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "catalog"
    assert len(body["sections"]) == 2
    assert body["sections"][1]["subtitle"] == "second"


def test_unknown_meme_is_404():
    assert client.post("/api/sessions", json={"meme_id": "nope"}).status_code == 404


def test_empty_meme_id_is_422():
    assert client.post("/api/sessions", json={"meme_id": ""}).status_code == 422


def test_broken_catalog_meme_is_500_without_details():
    response = client.post("/api/sessions", json={"meme_id": "meme_02"})
    assert response.status_code == 500
    assert response.json()["detail"] == "This meme can't be played."


def test_upload_valid_wav():
    samples = np.concatenate([make_tone(0.8), make_silence(0.5), make_tone(1.2)])
    response = upload(samples)
    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "upload"
    assert len(body["sections"]) == 2
    assert body["sections"][0]["subtitle"] is None


def test_upload_text_file_named_mp3_is_415():
    response = client.post("/api/sessions/upload", files={"file": ("x.mp3", b"hello")})
    assert response.status_code == 415


def test_upload_too_big_is_413(monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 1000)
    assert upload(make_tone(2.0)).status_code == 413


def test_upload_half_second_is_422():
    assert upload(make_tone(0.5)).status_code == 422


def test_upload_silence_is_422():
    response = upload(make_silence(3.0))
    assert response.status_code == 422
    assert response.json()["detail"] == "No voice found in this file."


def test_refused_upload_leaves_no_folder(temporary_storage):
    upload(make_silence(3.0))
    leftovers = list(temporary_storage.iterdir()) if temporary_storage.exists() else []
    assert leftovers == []


def test_get_session_and_section_audio():
    session = client.post("/api/sessions", json={"meme_id": "meme_01"}).json()
    assert client.get(f"/api/sessions/{session['session_id']}").json() == session
    audio = client.get(session["sections"][0]["audio_url"])
    assert audio.status_code == 200
    assert audio.headers["content-type"] == "audio/wav"


def test_section_index_out_of_range_is_404():
    session_id = client.post("/api/sessions", json={"meme_id": "meme_01"}).json()["session_id"]
    assert client.get(f"/api/sessions/{session_id}/sections/99/audio").status_code == 404


def test_bad_session_ids_are_404():
    assert client.get("/api/sessions/not-a-uuid").status_code == 404
    assert client.get("/api/sessions/..%2F..%2Fetc").status_code == 404
