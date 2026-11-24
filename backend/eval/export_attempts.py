"""Copies the attempts recorded in the game into eval/dataset/, and adds rows to labels.csv.

Why through the game? The test data then goes through the same microphone settings and
the same conversion as real games. Otherwise we would measure a different system.

Usage (inside Docker):  python -m eval.export_attempts
Each new attempt gets a row with an EMPTY label: you fill it in by listening (blind).
The original section is copied next to it (..._original.wav) so you can compare by ear.
"""

import json
import shutil
from pathlib import Path

from app import config
from eval import common


def meme_id_for(title: str) -> str:
    """Sessions store the meme's title; find its id in the catalog ("upload" if none)."""
    catalog = json.loads(config.CATALOG_PATH.read_text(encoding="utf-8"))
    for meme in catalog:
        if meme["title"] == title:
            return meme["id"]
    return "upload"


def export_session(session_folder: Path, known_files: set, dataset_dir: Path) -> list[dict]:
    attempts_file = session_folder / "attempts.json"
    session_file = session_folder / "session.json"
    if not attempts_file.exists() or not session_file.exists():
        return []
    session = json.loads(session_file.read_text(encoding="utf-8"))
    short_id = session_folder.name[:8]
    new_rows = []
    for attempt in json.loads(attempts_file.read_text(encoding="utf-8")):
        index = attempt["section_index"]
        name = f"{short_id}_s{index}_a{attempt['attempt_number']}.wav"
        if name in known_files:
            continue  # already exported: never duplicate or overwrite a label
        shutil.copy(session_folder / "attempts" / attempt["file_name"], dataset_dir / name)
        original = session_folder / "sections" / f"{index}.wav"
        shutil.copy(original, dataset_dir / f"{short_id}_s{index}_original.wav")
        new_rows.append({"attempt_file": name, "meme_id": meme_id_for(session["meme_title"]),
                         "section_index": index, "label": "", "split": "",
                         "hard_case": "", "speaker": "", "notes": ""})
    return new_rows


def export_all() -> int:
    storage_dir = Path(config.STORAGE_DIR)
    dataset_dir = Path(common.DATASET_DIR)
    dataset_dir.mkdir(parents=True, exist_ok=True)
    rows = common.load_labels()
    known_files = {row["attempt_file"] for row in rows}
    added = 0
    for session_folder in sorted(Path(storage_dir).iterdir()):
        new_rows = export_session(session_folder, known_files, dataset_dir)
        rows += new_rows
        added += len(new_rows)
    common.save_labels(rows)
    return added


if __name__ == "__main__":
    count = export_all()
    print(f"Exported {count} new attempts to {common.DATASET_DIR}. Label them in eval/labels.csv.")
