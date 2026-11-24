# Scoring vs human labels: summary (2026-11-24)

Protocol: `eval/PROTOCOL.md` + amendment 1 (both committed before these results).
**Test set: 28 examples.**
- 16 human attempts recorded through the app (1 speaker), labeled **blind** on `eval/label.html`: 10 good, 2 try_again, 4 refused.
- 12 synthetic refusal cases (`eval/make_synthetic.py`, label known by construction): silent ×3, distorted ×3, short ×2, noisy ×2, long ×2.

No dev set: the thresholds were **not tuned**, only checked. The test set was run **once** per scorer.

## Results

| Scorer | Correct | Accuracy | macro-F1 | Refusal precision / recall |
|---|---|---|---|---|
| `signal-v1` | **21 / 28** | 0.750 | **0.634** | 1.00 / 0.94 (15/16) |
| `signal-no-melody` (one variable: melody dropped) | 19 / 28 | 0.679 | 0.536 | 1.00 / 0.94 |

**Comparison:** a gap of **2 examples** (< 3) = **no measurable difference** by the protocol's rule. The direction favors keeping melody (2 more `good` attempts recognized), but this test set can't prove it.

Confusion matrix (`signal-v1`, rows = human, columns = app):

| | great | good | try_again | refused |
|---|---|---|---|---|
| good (10) | 0 | 4 | **6** | 0 |
| try_again (2) | 0 | 0 | 2 | 0 |
| refused (16) | 0 | 0 | 1 | 15 |

(`great` is absent: no attempt was labeled great, and the app predicted none. The class is left out of macro-F1.)

## Thresholds checked on the data

| Rule | Threshold | Usable human recordings | Refused recordings | Verdict |
|---|---|---|---|---|
| silent (loudest frame) | −45 dB | all ≥ −24.5 dB | "no sound": −61, −94, −94 dB | in the gap ✅ |
| too noisy (loud vs quiet frames) | < 10 dB | all ≥ 34.9 dB | silence / noise: 0.6–2.6 dB | in the gap ✅ |
| too short (after trim) | < 0.3 s | all ≥ 0.67 s | synthetic 0.15 s | ✅ |
| too long | > 3 × section + 1 s | length ratio ≤ 1.41 | synthetic ×4 | ✅ |
| too loud (clipped) | > 1 % | 0 % | synthetic gain ×20 | ✅ |
| verdict `T_GOOD` | 0.50 | `good` scored 0.29–0.57 | `try_again`: 0.23, 0.27 | **too high** ✗ |

## What went wrong (`eval.diagnose`)

7 errors: **features:timbre 5**, features:melody 1, rules 1.

1. **The scorer is too harsh, and timbre is to blame.** 6 of the 10 `good` attempts scored 0.29–0.42, under `T_GOOD = 0.50`. Their timbre sub-score is often near 0 (0.00–0.12), while their rhythm stays high (0.77–0.94). This is the pitch sensitivity of MFCC found in Sprint 2: the timbre calibration (`COST_GOOD = 0.30`) was a guess, and real voices are further from the original.
2. **The ranking is right; the cut-off is wrong.** Every `good` attempt scored **above** both `try_again` ones. A `T_GOOD` near 0.28 would have separated them, but choosing it now would be tuning on the test set. It's the next step, on a new dev set.
3. **One refusal missed:** an attempt labeled `refused` (not an imitation of the piece) had normal sound (−24 dB, 1.9 s, 37 dB range). The rules check the **signal quality**, not whether the content is the right meme. That's a known limit of a rule-based filter.

## Honest limits
- 1 speaker, 16 human attempts: 1 human example ≈ 6 points. Only large effects are visible.
- The synthetic refusals (12/12 caught) only show that the rules catch obvious damage.
- No `great` labels: that class is untested.

## Next step
Record a **dev set** (other speakers), then calibrate `TIMBRE_COST_GOOD` and `T_GOOD` on it (`eval.calibrate`), test MFCC c1–c5 (`MFCC_FIRST_COEFFICIENT`), and re-test once on a fresh test set.
