"""Hand-written metrics (same as Atelier 2's evaluation.py), so every number can be explained.

truths = the human labels, predictions = what the app said, both lists of class names.
Used by evaluate_scoring.py and calibrate.py.
"""

CLASSES = ["great", "good", "try_again", "refused"]


def accuracy(truths, predictions):
    correct = sum(1 for truth, prediction in zip(truths, predictions) if truth == prediction)
    return correct / len(truths)


def scores_per_class(truths, predictions, classes=CLASSES):
    """Precision, recall, F1 and support (number of real examples) for each class."""
    result = {}
    for name in classes:
        pairs = list(zip(truths, predictions))
        true_positives = sum(1 for t, p in pairs if t == name and p == name)
        false_positives = sum(1 for t, p in pairs if t != name and p == name)
        false_negatives = sum(1 for t, p in pairs if t == name and p != name)
        # "if ... else 0.0": a class never predicted (or never present) must not crash.
        predicted_count = true_positives + false_positives
        real_count = true_positives + false_negatives
        precision = true_positives / predicted_count if predicted_count else 0.0
        recall = true_positives / real_count if real_count else 0.0
        both = precision + recall
        f1 = 2 * precision * recall / both if both else 0.0
        result[name] = {"precision": precision, "recall": recall, "f1": f1, "support": real_count}
    return result


def macro_f1(per_class):
    """The average F1 of the classes: each class counts the same, even a rare one."""
    return sum(scores["f1"] for scores in per_class.values()) / len(per_class)


def confusion_matrix(truths, predictions, classes=CLASSES):
    """matrix[truth][prediction] = how many examples. Rows = human, columns = app."""
    matrix = {}
    for truth_name in classes:
        matrix[truth_name] = {}
        for prediction_name in classes:
            matrix[truth_name][prediction_name] = 0
    for truth, prediction in zip(truths, predictions):
        matrix[truth][prediction] += 1
    return matrix


def report(title, truths, predictions, classes=CLASSES):
    """Returns (text to print/save, numbers as a dict for the JSON file)."""
    per_class = scores_per_class(truths, predictions, classes)
    matrix = confusion_matrix(truths, predictions, classes)
    correct = sum(1 for t, p in zip(truths, predictions) if t == p)
    lines = [
        f"=== {title} ===",
        f"examples    : {len(truths)}",
        f"correct     : {correct}",
        f"accuracy    : {accuracy(truths, predictions):.3f}",
        f"macro-F1    : {macro_f1(per_class):.3f}",
        "",
        f"{'class':<12}{'precision':>10}{'recall':>8}{'F1':>7}{'n':>5}",
    ]
    for name, scores in per_class.items():
        lines.append(f"{name:<12}{scores['precision']:>10.3f}{scores['recall']:>8.3f}"
                     f"{scores['f1']:>7.3f}{scores['support']:>5d}")
    lines += ["", "Confusion matrix (rows = human, columns = app)",
              " " * 12 + "".join(f"{name[:9]:>10}" for name in classes)]
    for truth_name in classes:
        counts = "".join(f"{matrix[truth_name][p]:>10d}" for p in classes)
        lines.append(f"{truth_name:<12}{counts}")
    numbers = {"examples": len(truths), "correct": correct,
               "accuracy": accuracy(truths, predictions), "macro_f1": macro_f1(per_class),
               "per_class": per_class, "confusion_matrix": matrix}
    return "\n".join(lines), numbers
