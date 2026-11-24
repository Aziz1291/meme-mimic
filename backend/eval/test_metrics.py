"""Tests for eval/metrics.py, including one example checked by hand on paper."""

import pytest

from eval.metrics import accuracy, confusion_matrix, macro_f1, report, scores_per_class


def test_perfect_predictions_give_1_everywhere():
    labels = ["great", "good", "try_again", "refused"]
    per_class = scores_per_class(labels, labels)
    assert accuracy(labels, labels) == 1.0
    assert macro_f1(per_class) == 1.0


def test_never_predicting_refused_does_not_crash():
    truths = ["refused", "great", "good"]
    predictions = ["great", "great", "good"]
    per_class = scores_per_class(truths, predictions)
    assert per_class["refused"]["f1"] == 0.0
    assert per_class["refused"]["precision"] == 0.0  # 0 / 0 handled


def test_small_example_computed_by_hand():
    # truth:      great great good try_again
    # prediction: great good  good good
    truths = ["great", "great", "good", "try_again"]
    predictions = ["great", "good", "good", "good"]
    per_class = scores_per_class(truths, predictions)
    # great: TP=1, FP=0, FN=1 → precision 1, recall 0.5, F1 = 2*1*0.5/1.5 = 0.667
    assert per_class["great"]["f1"] == pytest.approx(2 / 3)
    # good: TP=1, FP=2, FN=0 → precision 1/3, recall 1, F1 = 2*(1/3)*1/(4/3) = 0.5
    assert per_class["good"]["f1"] == pytest.approx(0.5)
    # try_again: TP=0 → F1 0. refused: absent and never predicted → F1 0.
    # macro-F1 = (0.667 + 0.5 + 0 + 0) / 4 = 0.292
    assert macro_f1(per_class) == pytest.approx((2 / 3 + 0.5) / 4)
    assert accuracy(truths, predictions) == 0.5


def test_confusion_matrix_counts():
    matrix = confusion_matrix(["great", "great", "refused"], ["great", "good", "refused"])
    assert matrix["great"]["great"] == 1
    assert matrix["great"]["good"] == 1
    assert matrix["refused"]["refused"] == 1


def test_report_has_the_numbers():
    text, numbers = report("demo", ["great", "good"], ["great", "great"])
    assert "macro-F1" in text
    assert numbers["correct"] == 1
