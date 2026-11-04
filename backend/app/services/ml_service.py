"""Bridge between FastAPI and the separate ML project (ml/src/physioband_ml).

The ML package is imported from ``settings.ml_src_path`` so training code and the
API share exactly one implementation of preprocessing, rep counting and features.
CPU-heavy analysis runs in a worker thread so it never blocks the event loop.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any

from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.core.exceptions import ValidationFailed

log = logging.getLogger(__name__)

STATUS_UA_OK = 0b0001
STATUS_FA_OK = 0b0010
STATUS_LC_OK = 0b0100


def _ensure_ml_importable(src_path: str) -> None:
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def sanitize_samples(samples: list[dict]) -> list[dict]:
    """Blank out readings whose sensor reported a fault in the firmware status flags."""
    clean = []
    for s in samples:
        status = s.get("status", 0b1111)
        clean.append(
            {
                "timestamp_ms": s["timestamp_ms"],
                "ua": s["ua"] if status & STATUS_UA_OK else [None] * 6,
                "fa": s["fa"] if status & STATUS_FA_OK else [None] * 6,
                "force_n": s["force_n"] if status & STATUS_LC_OK else None,
            }
        )
    return clean


class MLService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = None
        self.load_error: str | None = None
        _ensure_ml_importable(settings.ml_src_path)

    def load_model(self) -> None:
        try:
            from physioband_ml.models import ModelLoadError, QualityModel
        except ImportError as exc:
            self.load_error = f"ML package not importable from {self.settings.ml_src_path}: {exc}"
            log.error(self.load_error)
            return
        try:
            self.model = QualityModel.load(self.settings.ml_model_path)
            self.load_error = None
            info = self.model.info()
            log.info("Loaded quality model %s v%s (dataset: %s, validated: %s)",
                     info["algorithm"], info["model_version"], info["dataset_type"], info["validated"])
        except ModelLoadError as exc:
            self.model = None
            self.load_error = str(exc)
            log.warning("Quality model unavailable: %s", exc)

    def status(self) -> dict[str, Any]:
        if self.model is None:
            return {
                "available": False,
                "validated": False,
                "status_note": "Quality model not loaded. Repetitions are counted but not classified. "
                + (self.load_error or ""),
            }
        info = self.model.info()
        return {
            "available": True,
            "algorithm": info["algorithm"],
            "model_version": info["model_version"],
            "dataset_type": info["dataset_type"],
            "validated": info["validated"],
            "status_note": info["status_note"],
        }

    def info(self) -> dict[str, Any]:
        data = self.status()
        if self.model is not None:
            data.update(self.model.info())
        data["load_error"] = self.load_error
        return data

    def _analyze_sync(self, samples: list[dict], exercise_id: str, live: bool, include_features: bool) -> dict:
        from physioband_ml.analysis import UnsupportedExerciseError, analyze_frame
        from physioband_ml.io import samples_to_frame
        from physioband_ml.preprocessing import SensorDataError

        frame = samples_to_frame(sanitize_samples(samples))
        try:
            result = analyze_frame(frame, exercise_id, model=self.model, live=live, include_features=include_features)
        except UnsupportedExerciseError as exc:
            raise ValidationFailed(str(exc), code="EXERCISE_NOT_SUPPORTED")
        except (SensorDataError, ValueError) as exc:
            raise ValidationFailed(str(exc), code="INVALID_SENSOR_DATA")
        return result.to_dict()

    async def analyze(self, samples: list[dict], exercise_id: str, mode: str, include_features: bool = False) -> dict:
        data = await run_in_threadpool(self._analyze_sync, samples, exercise_id, mode == "live", include_features)
        data["mode"] = mode
        data["analyzed_at"] = datetime.now(timezone.utc)
        data["model"] = self.status()
        return data
