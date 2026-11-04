"""Loading a trained model artefact and predicting movement quality.

A model artefact is a pickle (.pkl) file containing a dict:
    model            fitted scikit-learn compatible classifier (predict_proba)
    feature_names    feature order used at training time
    classes          class labels in predict_proba column order
    pipeline_config  PipelineConfig used to build the training features
    metadata         algorithm, dataset type (synthetic / collected), metrics, ...
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pickle

import joblib
import numpy as np

from physioband_ml.config import PipelineConfig
from physioband_ml.feature_extraction import FEATURE_NAMES, features_to_matrix


class ModelLoadError(RuntimeError):
    pass


@dataclass
class Prediction:
    label: str
    confidence: float
    probabilities: dict[str, float]


class QualityModel:
    def __init__(self, artefact: dict[str, Any], path: str | None = None):
        missing = {"model", "feature_names", "classes"} - set(artefact)
        if missing:
            raise ModelLoadError(f"Model artefact is missing keys: {sorted(missing)}")
        if list(artefact["feature_names"]) != FEATURE_NAMES:
            raise ModelLoadError(
                "Model was trained with a different feature set; retrain it with the current pipeline"
            )
        self.model = artefact["model"]
        if hasattr(self.model, "n_jobs"):
            self.model.n_jobs = 1  # a few reps per call: thread start-up costs more than it saves
        self.classes: list[str] = [str(c) for c in artefact["classes"]]
        self.pipeline_config = PipelineConfig.from_dict(artefact.get("pipeline_config"))
        self.metadata: dict[str, Any] = dict(artefact.get("metadata", {}))
        self.path = path

    @classmethod
    def load(cls, path: str | Path) -> "QualityModel":
        path = Path(path)
        if not path.exists():
            raise ModelLoadError(f"Model file not found: {path}")
        try:
            # Pickle files can run code when loaded: only load models you trained yourself.
            if path.suffix == ".pkl":
                with path.open("rb") as fh:
                    artefact = pickle.load(fh)
            else:
                artefact = joblib.load(path)  # older .joblib artefacts
        except Exception as exc:  # corrupted file or incompatible library version
            raise ModelLoadError(f"Could not load model file {path}: {exc}") from exc
        return cls(artefact, path=str(path))

    def predict(self, feature_rows: list[dict[str, float]]) -> list[Prediction]:
        if not feature_rows:
            return []
        X = features_to_matrix(feature_rows)
        proba = self.model.predict_proba(X)
        model_classes = [str(c) for c in getattr(self.model, "classes_", self.classes)]
        results = []
        for row in proba:
            best = int(np.argmax(row))
            results.append(
                Prediction(
                    label=model_classes[best],
                    confidence=float(row[best]),
                    probabilities={c: round(float(p), 4) for c, p in zip(model_classes, row)},
                )
            )
        return results

    def info(self) -> dict[str, Any]:
        return {
            "algorithm": self.metadata.get("algorithm", type(self.model).__name__),
            "model_version": self.metadata.get("model_version", "unknown"),
            "trained_at": self.metadata.get("trained_at"),
            "dataset_type": self.metadata.get("dataset_type", "unknown"),
            "validated": bool(self.metadata.get("validated", False)),
            "status_note": self.metadata.get("status_note", ""),
            "classes": self.classes,
            "feature_count": len(FEATURE_NAMES),
            "training_samples": self.metadata.get("training_samples"),
            "test_samples": self.metadata.get("test_samples"),
            "metrics": self.metadata.get("metrics"),
            "exercise_ids": self.metadata.get("exercise_ids", ["biceps_curl"]),
        }
