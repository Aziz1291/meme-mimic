"""Measures how often the game's verdict agrees with the human labels, on the TEST set.

Usage (inside Docker):
    python -m eval.evaluate_scoring signal-v1
    python -m eval.evaluate_scoring signal-no-melody     ← the one-variable comparison
Saves eval/results/scoring_<scorer>_<date>.txt and .json (a deliverable).
Protocol: the test set is used ONCE per final configuration. Tune on dev (calibrate.py).
"""

import sys
from datetime import date

from app.providers.scorers import get_scorer
from eval.common import config_snapshot, predict_split, save_result
from eval.metrics import report


def wrong_examples(results: list[dict]) -> list[dict]:
    wrong = []
    for result in results:
        if result["prediction"] != result["row"]["label"]:
            wrong.append({"file": result["row"]["attempt_file"], "human": result["row"]["label"],
                          "app": result["prediction"], "score": result["score"],
                          "refusal_reason": result["refusal_reason"],
                          "hard_case": result["row"]["hard_case"]})
    return wrong


def evaluate(scorer_name: str, split="test"):
    scorer = get_scorer(scorer_name)
    results = predict_split(split, scorer)
    if not results:
        raise SystemExit(f"No labeled '{split}' attempts in eval/labels.csv yet.")
    truths = [result["row"]["label"] for result in results]
    predictions = [result["prediction"] for result in results]
    text, numbers = report(f"{scorer.name} on {split} ({date.today()})", truths, predictions)

    refused = numbers["per_class"]["refused"]
    wrong = wrong_examples(results)
    lines = [text, "",
             f"refusal precision: {refused['precision']:.3f}   refusal recall: {refused['recall']:.3f}",
             "", f"Wrong examples ({len(wrong)}):"]
    for example in wrong:
        score_text = "-" if example["score"] is None else f"{example['score']:.2f}"
        lines.append(f"  {example['file']:<26} human={example['human']:<10} "
                     f"app={example['app']:<10} score={score_text} {example['hard_case']}")
    lines += ["", "Config used:"]
    snapshot = config_snapshot()
    for name, value in snapshot.items():
        lines.append(f"  {name} = {value}")

    numbers.update({"scorer": scorer.name, "split": split, "config": snapshot, "wrong": wrong})
    full_text = "\n".join(lines)
    save_result(f"scoring_{scorer.name}_{split}_{date.today()}", full_text, numbers)
    return full_text


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "signal-v1"
    print(evaluate(name))
