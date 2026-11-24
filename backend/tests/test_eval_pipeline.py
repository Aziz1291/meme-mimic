"""End-to-end test of the evaluation scripts on a tiny fake dataset.

Plays a game through the API (good, wrong and silent attempts), exports the attempts,
labels them like a human would, then runs evaluate, diagnose and calibrate.
Everything happens in temporary folders: the real labels.csv and dataset are never touched.
"""

import io

import numpy as np
import pytest
import soundfile
from fastapi.testclient import TestClient

from app import config
from app.main import app
from eval import common
from eval.calibrate import calibrate
from eval.diagnose import diagnose
from eval.evaluate_scoring import evaluate
from eval.export_attempts import export_all
from tests.conftest import make_chirp, make_silence

client = TestClient(app)


@pytest.fixture(autouse=True)
def fake_eval_folders(fake_catalog, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SCORER", "signal")
    monkeypatch.setattr(common, "DATASET_DIR", tmp_path / "dataset")
    monkeypatch.setattr(common, "LABELS_PATH", tmp_path / "labels.csv")
    monkeypatch.setattr(common, "RESULTS_DIR", tmp_path / "results")


def send(session_id, index, samples):
    buffer = io.BytesIO()
    soundfile.write(buffer, samples, 16000, format="WAV")
    url = f"/api/sessions/{session_id}/sections/{index}/attempts"
    return client.post(url, files={"file": ("a.wav", buffer.getvalue())}).json()


def play_and_label():
    session = client.post("/api/sessions", json={"meme_id": "meme_01"}).json()
    for section in session["sections"]:
        original, _ = soundfile.read(io.BytesIO(client.get(section["audio_url"]).content))
        pad = make_silence(0.3)
        send(session["session_id"], section["index"], np.concatenate([pad, original, pad]))
        wrong = make_chirp(1.5, 500, 250)  # the melody goes the other way
        send(session["session_id"], section["index"], np.concatenate([pad, wrong, pad]))
        send(session["session_id"], section["index"], make_silence(1.0))

    assert export_all() == 6
    rows = common.load_labels()
    labels = {"1": "great", "2": "try_again", "3": "refused"}  # by attempt number
    for row in rows:
        row["label"] = labels[row["attempt_file"][-5]]
        row["split"] = "dev" if row["section_index"] == "0" else "test"
    common.save_labels(rows)


def test_export_copies_attempts_and_originals():
    play_and_label()
    files = sorted(path.name for path in common.DATASET_DIR.iterdir())
    assert len(files) == 8  # 6 attempts + 2 originals
    assert export_all() == 0  # running it again adds nothing


def test_synthetic_refusals_are_all_refused_by_the_rules():
    from eval.common import predict
    from eval.make_synthetic import make_all
    from app.providers.scorers import MockScorer

    play_and_label()
    rows = common.load_labels()
    for row in rows:  # like a human who labeled but didn't split
        row["split"] = ""
    common.save_labels(rows)
    assert make_all() == 12
    assert make_all() == 0  # running it twice adds nothing
    rows = common.load_labels()
    assert all(row["split"] == "test" for row in rows)
    synthetic = [row for row in rows if row["speaker"] == "synthetic"]
    assert all("a3" not in row["attempt_file"] for row in synthetic)  # attempt 3 = silence
    for row in synthetic:  # every damage must really be caught by a rule
        assert predict(row, MockScorer())["prediction"] == "refused", row["attempt_file"]


def test_evaluate_diagnose_calibrate_run_and_save():
    play_and_label()
    text = evaluate("signal-v1")
    assert "macro-F1" in text and "Config used" in text
    assert "diagnosis" not in text
    diagnosis = diagnose("signal-v1")
    assert "wrong out of 3" in diagnosis
    calibration = calibrate()
    assert "Verdict thresholds" in calibration
    saved = sorted(path.suffix for path in common.RESULTS_DIR.iterdir())
    assert saved.count(".txt") == 3 and saved.count(".json") == 3
