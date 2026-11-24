# Evaluation protocol

Written **before** any evaluation was run (see this file's first Git commit date).
Atelier 2 rule: choose the metric before seeing results, or you'll pick the one that makes your favorite win.

## What is measured

Does the game's verdict agree with a human listening to the same attempt?

## Classes (4)

| Class | Labeling guide (the human listens to the original, then the attempt) |
|---|---|
| `great` | A friend would instantly recognize the meme; melody and rhythm match. |
| `good` | Recognizable, but with clear differences. |
| `try_again` | Not recognizable, or very different. |
| `refused` | The recording can't be judged: silence, distortion, loud background noise, cut too early. |

The app's prediction is its refusal (`refused`) if a rule fired, otherwise its verdict.

## Labeling rules

1. Listen to the original section, then the attempt, and **write the label before seeing any score**.
2. Optional: a second person labels too; we report how often the two humans agree.
3. Each attempt gets a split, `dev` or `test`, **once**, at random with a fixed seed, keeping a similar mix of labels in both (`python -m eval.split`). An example is **never** moved afterwards.

## Sizes

- dev set: at least 15 attempts. Used for **tuning** (thresholds, calibration).
- test set: at least 30 attempts. Touched **once per final configuration**.
- The test set includes at least 8 **hard cases** (opposite-gender voice, flat melody, wrong words, much faster/slower, whisper, laughing, accent) and at least 6 **cases to refuse** (silence, far from the mic, distorted, TV/music behind, cut after 0.2 s).

## Decision metric

**macro-F1 over the 4 classes**: each class counts equally, so the rare `refused` class isn't ignored.

Also reported: accuracy, per-class precision / recall / F1 / support, confusion matrix, refusal precision and recall, and the list of wrong examples.

## Significance rule

With 30 test examples, 1 example ≈ 3.3 points of accuracy.
**A gap of fewer than 3 examples = "no measurable difference".** Gaps are always reported in **number of examples**, not only in points.

## Comparisons planned

1. Scorer `signal-v1` vs `signal-no-melody`: one variable changed (melody used or not), same test set, same thresholds.
2. (Sprint 5) Two LLMs for the coach agent.

## Reproducibility

Every result file in `eval/results/` contains the scorer name and every config value used (thresholds, weights, calibration).
