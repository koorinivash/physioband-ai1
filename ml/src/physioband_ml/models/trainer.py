"""Model training with participant-wise train / test separation."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit, train_test_split

from physioband_ml.config import PipelineConfig
from physioband_ml.evaluation.metrics import evaluate_predictions
from physioband_ml.feature_extraction import FEATURE_NAMES


def split_by_participant(
    table: pd.DataFrame, test_size: float, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Split so that no participant appears in both train and test sets."""
    groups = table["participant_id"].astype(str)
    if groups.nunique() >= 3:
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
        train_idx, test_idx = next(splitter.split(table, groups=groups))
        return table.iloc[train_idx], table.iloc[test_idx], "participant-wise (GroupShuffleSplit)"
    stratify = table["label"] if table["label"].value_counts().min() >= 2 else None
    train, test = train_test_split(table, test_size=test_size, random_state=seed, stratify=stratify)
    return train, test, "random stratified (fewer than 3 participants available)"


def build_model(algorithm: str, seed: int):
    if algorithm == "random_forest":
        return RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=seed,
            n_jobs=-1,
        )
    if algorithm == "xgboost":
        try:
            from xgboost import XGBClassifier  # optional dependency
        except ImportError as exc:
            raise RuntimeError("xgboost is not installed: pip install xgboost") from exc
        return XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.1, random_state=seed)
    raise ValueError(f"Unknown algorithm: {algorithm}")


class _LabelEncodedModel:
    """Wraps classifiers (XGBoost) that need integer labels so predict_proba keeps string classes."""

    def __init__(self, model, classes: list[str]):
        self.model = model
        self.classes_ = np.array(classes)

    def fit(self, X, y):
        index = {c: i for i, c in enumerate(self.classes_)}
        self.model.fit(X, np.array([index[v] for v in y]))
        return self

    def predict_proba(self, X):
        return self.model.predict_proba(X)

    def predict(self, X):
        return self.classes_[np.argmax(self.predict_proba(X), axis=1)]


def train_model(
    table: pd.DataFrame,
    algorithm: str = "random_forest",
    test_size: float = 0.25,
    seed: int = 42,
    pipeline_config: PipelineConfig | None = None,
) -> tuple[dict[str, Any], dict[str, Any], pd.DataFrame]:
    """Train and evaluate. Returns ``(artefact, evaluation, test_predictions)``."""
    if table.empty:
        raise ValueError("Feature table is empty; no repetitions were detected in the dataset")
    train, test, split_method = split_by_participant(table, test_size, seed)
    labels = sorted(table["label"].unique())

    model = build_model(algorithm, seed)
    if algorithm == "xgboost":
        model = _LabelEncodedModel(model, labels)
    model.fit(train[FEATURE_NAMES].to_numpy(), train["label"].to_numpy())

    y_pred = model.predict(test[FEATURE_NAMES].to_numpy())
    evaluation = evaluate_predictions(test["label"].to_numpy(), y_pred, labels)
    evaluation["split_method"] = split_method
    evaluation["train_participants"] = sorted(train["participant_id"].astype(str).unique())
    evaluation["test_participants"] = sorted(test["participant_id"].astype(str).unique())

    is_synthetic = bool(table.get("is_synthetic", pd.Series([False])).astype(bool).any())
    metadata = {
        "algorithm": "RandomForestClassifier" if algorithm == "random_forest" else "XGBClassifier",
        "model_version": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_type": "synthetic" if is_synthetic else "collected",
        "validated": False,
        "status_note": (
            "DEMO MODEL trained on synthetic data. It only demonstrates the software pipeline "
            "and is NOT a validated exercise-quality model."
            if is_synthetic
            else "Trained on collected sensor data. Not clinically validated."
        ),
        "training_samples": int(len(train)),
        "test_samples": int(len(test)),
        "metrics": {
            "accuracy": evaluation["accuracy"],
            "macro_f1": evaluation["macro_avg"]["f1"],
            "split_method": split_method,
            "evaluated_on": "synthetic test participants" if is_synthetic else "held-out participants",
        },
        "exercise_ids": sorted(table["exercise_id"].astype(str).unique()) if "exercise_id" in table else ["biceps_curl"],
    }

    pred_df = test[["participant_id", "session_id", "rep_number", "label"]].copy()
    pred_df["predicted"] = y_pred

    artefact = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "classes": [str(c) for c in model.classes_],
        "pipeline_config": (pipeline_config or PipelineConfig()).to_dict(),
        "metadata": metadata,
    }
    return artefact, evaluation, pred_df


def save_artefact(artefact: dict[str, Any], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Standard Python pickle (.pkl); the backend loads exactly this file.
    with path.open("wb") as fh:
        pickle.dump(artefact, fh, protocol=pickle.HIGHEST_PROTOCOL)
    return path
