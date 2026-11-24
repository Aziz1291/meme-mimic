"""Gives each labeled attempt a split, dev or test, ONCE.

- Fixed random seed: running it twice gives the same result.
- Stratified: each label (great, good, ...) is shared out separately, so dev and test
  get a similar mix of labels.
- Rows that already have a split are NEVER changed (moving an example from test to dev
  after seeing results would be cheating).

Usage (inside Docker):  python -m eval.split
"""

import random

from eval.common import LABELS_PATH, load_labels, save_labels

TEST_SHARE = 2 / 3  # protocol: dev ≥ 15, test ≥ 30 → about 1/3 dev, 2/3 test
SEED = 42


def assign_splits(rows: list[dict], seed=SEED) -> int:
    generator = random.Random(seed)
    assigned = 0
    labels = sorted({row["label"] for row in rows if row["label"]})
    for label in labels:
        waiting = [row for row in rows if row["label"] == label and not row["split"]]
        generator.shuffle(waiting)
        test_count = round(len(waiting) * TEST_SHARE)
        for position, row in enumerate(waiting):
            if position < test_count:
                row["split"] = "test"
            else:
                row["split"] = "dev"
            assigned += 1
    return assigned


if __name__ == "__main__":
    all_rows = load_labels()
    count = assign_splits(all_rows)
    save_labels(all_rows)
    print(f"Assigned a split to {count} attempts in {LABELS_PATH}.")
