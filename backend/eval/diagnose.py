"""For each wrong test example: which stage of the pipeline failed? (bonus "diagnosis")

Stages:
  rules            the human said "refused" but no rule fired, or a rule fired on a usable recording
  threshold        the score is within ±0.05 of a verdict threshold: a near miss
  features:<name>  otherwise, the sub-score that disagrees most with the human label

Usage (inside Docker):  python -m eval.diagnose signal-v1
Saves eval/results/diagnosis_<scorer>_<date>.txt and .json.
"""

import sys
from collections import Counter
from datetime import date

from app import config
from app.providers.scorers import get_scorer
from eval.common import predict_split, save_result

NEAR_MISS = 0.05


def stage_for(result: dict) -> str:
    human = result["row"]["label"]
    app = result["prediction"]
    if human == "refused" or app == "refused":
        return "rules"
    score = result["score"]
    for threshold in (config.T_GOOD, config.T_GREAT):
        if abs(score - threshold) <= NEAR_MISS:
            return "threshold"
    # The feature to blame: if the human liked it more than the app, the LOWEST sub-score
    # pulled the score down; if the human liked it less, the HIGHEST one pushed it up.
    sub_scores = {name: value for name, value in result["sub_scores"].items() if value is not None}
    human_rank = ["try_again", "good", "great"].index(human)
    app_rank = ["try_again", "good", "great"].index(app)
    if human_rank > app_rank:
        blamed = min(sub_scores, key=sub_scores.get)
    else:
        blamed = max(sub_scores, key=sub_scores.get)
    return f"features:{blamed}"


def diagnose(scorer_name: str, split="test"):
    scorer = get_scorer(scorer_name)
    results = predict_split(split, scorer)
    wrong = [result for result in results if result["prediction"] != result["row"]["label"]]
    lines = [f"=== Diagnosis: {scorer.name} on {split} ({date.today()}) ===",
             f"{len(wrong)} wrong out of {len(results)}", ""]
    stages = []
    for result in wrong:
        stage = stage_for(result)
        stages.append(stage)
        score_text = "-" if result["score"] is None else f"{result['score']:.2f}"
        lines.append(f"  {result['row']['attempt_file']:<26} human={result['row']['label']:<10} "
                     f"app={result['prediction']:<10} score={score_text}  → {stage}")
    counts = Counter(stages)
    lines += ["", "Errors per stage:"]
    for stage, count in counts.most_common():
        lines.append(f"  {stage:<20} {count}")
    text = "\n".join(lines)
    save_result(f"diagnosis_{scorer.name}_{split}_{date.today()}", text,
                {"scorer": scorer.name, "wrong": len(wrong), "total": len(results),
                 "stages": dict(counts)})
    return text


if __name__ == "__main__":
    print(diagnose(sys.argv[1] if len(sys.argv) > 1 else "signal-v1"))
