"""Shared helpers for the evaluation scripts: read/write labels.csv and predict one attempt.

The prediction goes through the SAME rules and scorer as the real game,
so we measure the real system, not a copy of it.
"""

import csv
import json
from pathlib import Path

from app import config
from app.audio import rules
from app.audio.io import load_wav

EVAL_DIR = Path(__file__).resolve().parent
DATASET_DIR = EVAL_DIR / "dataset"  # audio files: private, gitignored
LABELS_PATH = EVAL_DIR / "labels.csv"  # labels only, no audio: can be committed
RESULTS_DIR = EVAL_DIR / "results"

COLUMNS = ["attempt_file", "meme_id", "section_index", "label", "split",
           "hard_case", "speaker", "notes"]


def load_labels(path=None) -> list[dict]:
    # None → the real labels.csv. (A default of LABELS_PATH would be frozen when Python
    # reads the function, and tests couldn't point it to a temporary file.)
    path = path or LABELS_PATH
    if not Path(path).exists():
        return []
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def save_labels(rows: list[dict], path=None) -> None:
    path = path or LABELS_PATH
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def original_file_for(attempt_file: str) -> str:
    """abcd1234_s0_a2.wav → abcd1234_s0_original.wav (the section it imitates)."""
    section_part = attempt_file.rsplit("_a", 1)[0]
    return f"{section_part}_original.wav"


def labeled_rows(split: str, path=None) -> list[dict]:
    """The rows of one split that have a label (rows still to label are skipped)."""
    rows = []
    for row in load_labels(path):
        if row["split"] == split and row["label"]:
            rows.append(row)
    return rows


def predict(row: dict, scorer, dataset_dir=None) -> dict:
    """Runs rules + scorer on one labeled attempt, exactly like the attempt route does."""
    dataset_dir = dataset_dir or DATASET_DIR
    original_path = Path(dataset_dir) / original_file_for(row["attempt_file"])
    attempt_samples, sample_rate = load_wav(Path(dataset_dir) / row["attempt_file"])
    original_samples, _ = load_wav(original_path)
    section_seconds = len(original_samples) / sample_rate

    reason = rules.check(attempt_samples, sample_rate, section_seconds)
    if reason is not None:
        return {"prediction": "refused", "score": None, "sub_scores": None,
                "refusal_reason": reason.value}
    score, sub_scores, verdict = scorer.score(original_path, attempt_samples, sample_rate)
    return {"prediction": verdict.value, "score": score, "sub_scores": sub_scores.model_dump(),
            "refusal_reason": None}


def verdict_with(score: float, t_good: float, t_great: float) -> str:
    """The verdict for other thresholds than config's (used by the threshold search)."""
    if score >= t_great:
        return "great"
    if score >= t_good:
        return "good"
    return "try_again"


def config_snapshot() -> dict:
    """Every value that changes a result: saved with each result, so it can be reproduced."""
    names = ["WEIGHTS", "TIMBRE_COST_GOOD", "TIMBRE_COST_BAD", "MELODY_MAX_DIFF_SEMITONES",
             "LOUDNESS_MAX_DIFF", "T_GREAT", "T_GOOD", "SILENT_DB", "MIN_ATTEMPT_SECONDS",
             "CLIP_LEVEL", "MAX_CLIPPED_SHARE", "MIN_DYNAMIC_RANGE_DB", "MAX_LENGTH_FACTOR",
             "MAX_LENGTH_EXTRA_SECONDS", "N_MFCC", "MFCC_FIRST_COEFFICIENT", "HOP_LENGTH",
             "SAMPLE_RATE"]
    snapshot = {}
    for name in names:
        snapshot[name] = getattr(config, name)
    return snapshot


def predict_split(split: str, scorer, path=None, dataset_dir=None) -> list[dict]:
    """Predicts every labeled attempt of one split. Each result also keeps its row."""
    results = []
    for row in labeled_rows(split, path):
        result = predict(row, scorer, dataset_dir)
        result["row"] = row
        results.append(result)
    return results


def save_result(name: str, text: str, numbers: dict) -> None:
    """Saves a result as .txt (to read) and .json (to reuse), in eval/results/."""
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / f"{name}.txt").write_text(text + "\n", encoding="utf-8")
    json_text = json.dumps(numbers, indent=2, default=str)
    (RESULTS_DIR / f"{name}.json").write_text(json_text, encoding="utf-8")
