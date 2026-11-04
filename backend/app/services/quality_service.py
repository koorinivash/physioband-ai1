"""Exercise-quality aggregation: turns an analysis result into stored session metrics."""
from __future__ import annotations

SUMMARY_FIELDS = (
    "total_reps",
    "correct_reps",
    "incorrect_reps",
    "incomplete_reps",
    "too_fast_reps",
    "irregular_reps",
    "quality_score",
    "avg_tension_n",
    "peak_tension_n",
    "suggestions",
    "classification_available",
)


def session_fields_from_analysis(analysis: dict) -> dict:
    fields = {key: analysis[key] for key in SUMMARY_FIELDS}
    fields["model_dataset_type"] = analysis["model"].get("dataset_type")
    return fields


def empty_session_fields(reason: str) -> dict:
    return {
        "total_reps": 0,
        "correct_reps": 0,
        "incorrect_reps": 0,
        "incomplete_reps": 0,
        "too_fast_reps": 0,
        "irregular_reps": 0,
        "quality_score": None,
        "avg_tension_n": None,
        "peak_tension_n": None,
        "suggestions": [reason],
    }


def quality_of(correct: int, total: int, incorrect: int) -> float | None:
    """Quality % over classified reps only (unclassified reps are excluded)."""
    classified = correct + incorrect
    if classified == 0 or total == 0:
        return None
    return round(100.0 * correct / classified, 1)
