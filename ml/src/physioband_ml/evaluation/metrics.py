"""Evaluation metrics and plots. All numbers are computed from real predictions on a held-out set."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support


def evaluate_predictions(y_true, y_pred, labels: list[str]) -> dict:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    macro = precision_recall_fscore_support(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    weighted = precision_recall_fscore_support(y_true, y_pred, labels=labels, average="weighted", zero_division=0)
    return {
        "labels": list(labels),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "per_class": {
            label: {
                "precision": round(float(precision[i]), 4),
                "recall": round(float(recall[i]), 4),
                "f1": round(float(f1[i]), 4),
                "support": int(support[i]),
            }
            for i, label in enumerate(labels)
        },
        "macro_avg": {"precision": round(float(macro[0]), 4), "recall": round(float(macro[1]), 4), "f1": round(float(macro[2]), 4)},
        "weighted_avg": {
            "precision": round(float(weighted[0]), 4),
            "recall": round(float(weighted[1]), 4),
            "f1": round(float(weighted[2]), 4),
        },
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "test_samples": int(len(y_true)),
    }


def plot_confusion_matrix(evaluation: dict, path: str | Path, title: str) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = evaluation["labels"]
    cm = np.array(evaluation["confusion_matrix"])
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)), labels, rotation=30, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(title, fontsize=10)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, cm[i, j], ha="center", va="center", color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_feature_importance(model, feature_names: list[str], path: str | Path, top: int = 15) -> Path | None:
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    order = np.argsort(importances)[::-1][:top]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh([feature_names[i] for i in order][::-1], importances[order][::-1], color="#14b8a6")
    ax.set_title("Random Forest feature importance")
    fig.tight_layout()
    path = Path(path)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
