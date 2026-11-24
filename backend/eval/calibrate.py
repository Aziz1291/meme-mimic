"""Chooses thresholds from data, using the DEV set only (never the test set).

1. Timbre: median DTW cost of good imitations (→ TIMBRE_COST_GOOD) and of different memes
   (→ TIMBRE_COST_BAD).
2. Refusal rules: the value each rule measures, for "refused" vs usable recordings,
   so you can see where a threshold separates them.
3. Verdict thresholds: macro-F1 for every (T_GOOD, T_GREAT) pair.

Usage (inside Docker):  python -m eval.calibrate
Saves eval/results/calibration_dev_<date>.txt. Then YOU copy the chosen values to config.py.
"""

from datetime import date
from itertools import combinations
from pathlib import Path

import numpy as np

from app.audio import features, rules
from app.audio.io import load_wav
from app.audio.scoring import timbre_cost
from app.providers.scorers import get_scorer
from eval import common
from eval.common import labeled_rows, original_file_for, predict_split, save_result, verdict_with
from eval.metrics import macro_f1, scores_per_class


def rule_values(row: dict) -> dict:
    """What each rule looks at, for one attempt."""
    samples, sample_rate = load_wav(Path(common.DATASET_DIR) / row["attempt_file"])
    original, _ = load_wav(Path(common.DATASET_DIR) / original_file_for(row["attempt_file"]))
    levels = rules.frame_levels_db(samples)
    trimmed_seconds = len(features.trim(samples)) / sample_rate
    return {
        "loudest_db": float(levels.max()),
        "trimmed_seconds": trimmed_seconds,
        "clipped_percent": float(np.mean(np.abs(samples) >= 0.99) * 100),
        "dynamic_range_db": float(np.percentile(levels, 90) - np.percentile(levels, 10)),
        "length_ratio": trimmed_seconds / (len(original) / sample_rate),
    }


def text_strip(name: str, refused: list, usable: list) -> list[str]:
    """A plot in text: every value sorted, R = refused by the human, u = usable."""
    points = sorted([(value, "R") for value in refused] + [(value, "u") for value in usable])
    line = "  ".join(f"{mark}{value:.2f}" for value, mark in points)
    return [f"{name}:", f"  {line}"]


def timbre_section(dev_rows: list[dict]) -> list[str]:
    good_costs = []
    for row in dev_rows:
        if row["label"] in ("great", "good"):
            attempt, sample_rate = load_wav(Path(common.DATASET_DIR) / row["attempt_file"])
            original, _ = load_wav(Path(common.DATASET_DIR) / original_file_for(row["attempt_file"]))
            good_costs.append(timbre_cost(features.extract(original, sample_rate)["mfcc"],
                                          features.extract(attempt, sample_rate)["mfcc"]))
    originals = sorted({(row["meme_id"], original_file_for(row["attempt_file"])) for row in dev_rows})
    bad_costs = []
    for (meme_a, file_a), (meme_b, file_b) in combinations(originals, 2):
        if meme_a != meme_b:
            a, sample_rate = load_wav(Path(common.DATASET_DIR) / file_a)
            b, _ = load_wav(Path(common.DATASET_DIR) / file_b)
            bad_costs.append(timbre_cost(features.extract(a, sample_rate)["mfcc"],
                                         features.extract(b, sample_rate)["mfcc"]))
    lines = ["== 1. Timbre calibration =="]
    if good_costs:
        lines.append(f"good imitations (n={len(good_costs)}): median cost {np.median(good_costs):.3f}"
                     f"  → TIMBRE_COST_GOOD")
    if bad_costs:
        lines.append(f"different memes (n={len(bad_costs)}): median cost {np.median(bad_costs):.3f}"
                     f"  → TIMBRE_COST_BAD")
    return lines


def threshold_section(results: list[dict]) -> list[str]:
    lines = ["== 3. Verdict thresholds: dev macro-F1 (rows = T_GOOD, columns = T_GREAT) =="]
    greats = [round(value, 2) for value in np.arange(0.60, 0.91, 0.05)]
    lines.append("T_GOOD \\ T_GREAT " + "".join(f"{t:>7.2f}" for t in greats))
    truths = [result["row"]["label"] for result in results]
    for t_good in [round(value, 2) for value in np.arange(0.30, 0.71, 0.05)]:
        cells = []
        for t_great in greats:
            if t_great <= t_good:
                cells.append(f"{'-':>7}")
                continue
            predictions = []
            for result in results:
                if result["prediction"] == "refused":
                    predictions.append("refused")
                else:
                    predictions.append(verdict_with(result["score"], t_good, t_great))
            cells.append(f"{macro_f1(scores_per_class(truths, predictions)):>7.3f}")
        lines.append(f"{t_good:<17.2f}" + "".join(cells))
    lines.append("Prefer the middle of a flat good region over a single sharp peak (15 examples = luck).")
    return lines


def calibrate():
    dev_rows = labeled_rows("dev")
    if not dev_rows:
        raise SystemExit("No labeled 'dev' attempts yet: export, label, then run eval.split.")
    lines = [f"=== Calibration on dev ({len(dev_rows)} attempts, {date.today()}) ===", ""]
    lines += timbre_section(dev_rows) + ["", "== 2. Refusal rules (R = human said refused, u = usable) =="]
    values = [(row["label"] == "refused", rule_values(row)) for row in dev_rows]
    for name in ["loudest_db", "trimmed_seconds", "clipped_percent", "dynamic_range_db", "length_ratio"]:
        refused = [measured[name] for is_refused, measured in values if is_refused]
        usable = [measured[name] for is_refused, measured in values if not is_refused]
        lines += text_strip(name, refused, usable)
    lines.append("")
    lines += threshold_section(predict_split("dev", get_scorer("signal-v1")))
    text = "\n".join(lines)
    save_result(f"calibration_dev_{date.today()}", text, {"dev_size": len(dev_rows)})
    return text


if __name__ == "__main__":
    print(calibrate())
