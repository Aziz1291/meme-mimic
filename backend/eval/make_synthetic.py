"""Generates synthetic "refused" test cases from the human attempts (protocol, amendment 1).

Each case is a human attempt damaged on purpose in a way that makes it unusable,
so its label ("refused") is known BY CONSTRUCTION: no human judgment needed.
It also puts every human row that has a label but no split into "test" (no dev set).

Usage (inside Docker), after labeling:  python -m eval.make_synthetic
Running it twice adds nothing new.
"""

from pathlib import Path

import numpy as np

from app import config
from app.audio.io import load_wav, write_wav
from eval import common

TARGET_COUNT = 12  # 10 human + 12 synthetic = 22 test examples (the guide asks for ≥ 20)


def silent(samples):
    return np.zeros_like(samples)


def distorted(samples):
    # Volume ×20: most samples hit the maximum, like shouting into the mic.
    return np.clip(samples * 20, -1.0, 1.0)


def cut_short(samples):
    return samples[: int(0.15 * config.SAMPLE_RATE)]


def buried_in_noise(samples):
    # Loud constant noise: no quiet moment is left, like a TV right next to the mic.
    generator = np.random.default_rng(seed=len(samples))
    return np.clip(samples + 0.4 * generator.standard_normal(len(samples)), -1.0, 1.0)


def too_long(samples):
    return np.concatenate([samples, samples, samples, samples])


DAMAGES = [("silent", silent), ("distorted", distorted), ("short", cut_short),
           ("noisy", buried_in_noise), ("long", too_long)]


def human_rows(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row["label"] and row["speaker"] != "synthetic"]


def usable_sources(rows: list[dict]) -> list[dict]:
    """Only recordings a human found usable: "distorted silence" would still be silence,
    and wouldn't test the distortion rule."""
    return [row for row in human_rows(rows) if row["label"] != "refused"]


def make_all() -> int:
    rows = common.load_labels()
    known = {row["attempt_file"] for row in rows}
    for row in human_rows(rows):
        if not row["split"]:
            row["split"] = "test"  # amendment 1: no dev set
    sources = usable_sources(rows)
    if not sources:
        raise SystemExit("No usable labeled human attempts yet: export and label them first.")
    added = 0
    for position in range(TARGET_COUNT):
        source = sources[position % len(sources)]
        damage_name, damage = DAMAGES[position % len(DAMAGES)]
        # abcd1234_s0_a2.wav → abcd1234_s0_a2silent.wav (still points to the same original)
        name = source["attempt_file"].replace(".wav", f"{damage_name}.wav")
        if name in known:
            continue
        samples, sample_rate = load_wav(Path(common.DATASET_DIR) / source["attempt_file"])
        write_wav(Path(common.DATASET_DIR) / name, damage(samples), sample_rate)
        rows.append({"attempt_file": name, "meme_id": source["meme_id"],
                     "section_index": source["section_index"], "label": "refused",
                     "split": "test", "hard_case": f"synthetic_{damage_name}",
                     "speaker": "synthetic", "notes": f"made from {source['attempt_file']}"})
        known.add(name)
        added += 1
    common.save_labels(rows)
    return added


if __name__ == "__main__":
    print(f"Added {make_all()} synthetic refusal cases to {common.LABELS_PATH}.")
