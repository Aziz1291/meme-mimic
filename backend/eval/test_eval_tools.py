"""Tests for the evaluation helpers: file names, split, prediction."""

import numpy as np

from app.audio.io import write_wav
from app.providers.scorers import MockScorer
from eval.common import original_file_for, predict, verdict_with
from eval.split import assign_splits
from tests.conftest import make_silence, make_tone


def row(label, split=""):
    return {"label": label, "split": split}


def test_original_file_name():
    assert original_file_for("abcd1234_s0_a12.wav") == "abcd1234_s0_original.wav"


def test_split_keeps_existing_splits_and_is_repeatable():
    rows = [row("great") for _ in range(6)] + [row("refused", "dev")]
    copy = [dict(r) for r in rows]
    assign_splits(rows)
    assign_splits(copy)
    assert [r["split"] for r in rows] == [r["split"] for r in copy]  # same seed, same result
    assert rows[-1]["split"] == "dev"  # never moved
    assert sum(1 for r in rows[:6] if r["split"] == "test") == 4  # 2/3 of 6


def test_unlabeled_rows_get_no_split():
    rows = [row("")]
    assign_splits(rows)
    assert rows[0]["split"] == ""


def test_verdict_with_other_thresholds():
    assert verdict_with(0.7, t_good=0.5, t_great=0.65) == "great"
    assert verdict_with(0.7, t_good=0.5, t_great=0.75) == "good"


def test_predict_uses_the_rules_first(tmp_path):
    write_wav(tmp_path / "x_s0_original.wav", make_tone(1.0), 16000)
    write_wav(tmp_path / "x_s0_a1.wav", make_silence(1.0), 16000)
    sound = np.concatenate([make_silence(0.3), make_tone(1.0), make_silence(0.3)])
    write_wav(tmp_path / "x_s0_a2.wav", sound, 16000)

    silent = predict({"attempt_file": "x_s0_a1.wav"}, MockScorer(), tmp_path)
    assert silent["prediction"] == "refused" and silent["refusal_reason"] == "silent"
    scored = predict({"attempt_file": "x_s0_a2.wav"}, MockScorer(), tmp_path)
    assert scored["prediction"] == "great" and scored["score"] == 0.8
