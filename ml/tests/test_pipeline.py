import numpy as np
import pandas as pd
import pytest

from physioband_ml.analysis import UnsupportedExerciseError, analyze_frame
from physioband_ml.config import LABEL_CORRECT, LABEL_TOO_FAST, PipelineConfig, SENSOR_CHANNELS
from physioband_ml.dataset import build_feature_table
from physioband_ml.feature_extraction import FEATURE_NAMES
from physioband_ml.io import samples_to_frame
from physioband_ml.models import ModelLoadError, QualityModel
from physioband_ml.models.trainer import save_artefact, train_model
from physioband_ml.preprocessing import SensorDataError, lowpass, resample_uniform, validate_frame
from physioband_ml.repetition_counting import detect_repetitions
from physioband_ml.segmentation import process_frame
from physioband_ml.synthetic import generate_dataset, generate_mixed_stream, generate_set, random_profile


@pytest.fixture(scope="module")
def rng():
    return np.random.default_rng(123)


def test_validation_replaces_out_of_range_and_drops_duplicates():
    df = generate_mixed_stream(seed=1).iloc[:100].copy()
    df.loc[5, "ua_ax"] = 99.0
    df.loc[6, "force_n"] = None
    df = pd.concat([df, df.iloc[[10]]])
    clean, report = validate_frame(df)
    assert report.out_of_range_values == 1
    assert report.missing_values == 1
    assert report.dropped_duplicates == 1
    assert np.isnan(clean.loc[5, "ua_ax"])


def test_validation_requires_columns():
    with pytest.raises(SensorDataError):
        validate_frame(pd.DataFrame({"timestamp_ms": [1, 2]}))


def test_resampling_fills_short_gaps_and_flags_long_ones():
    ts = np.array([0, 20, 40, 60, 600, 620, 640])
    df = pd.DataFrame({"timestamp_ms": ts, **{c: np.arange(len(ts), dtype=float) for c in SENSOR_CHANNELS}})
    t, values, gap = resample_uniform(df, 50.0, 200.0)
    assert len(t) == 33
    assert np.isfinite(values).all()
    assert gap.any() and not gap[:4].any()


def test_lowpass_removes_high_frequency_noise():
    t = np.arange(0, 10, 0.02)
    clean = np.sin(2 * np.pi * 0.5 * t)
    noisy = clean + 0.3 * np.sin(2 * np.pi * 15 * t)
    error = np.abs(lowpass(noisy, 50, 5) - clean)[25:-25]  # ignore filter edge transients
    assert error.max() < 0.05


def test_elbow_angle_tracks_true_flexion(rng):
    prof = random_profile("T", rng)
    df = generate_set(LABEL_CORRECT, 3, prof, "s", rng)
    sig = process_frame(df)
    assert sig.elbow_angle.max() > 100
    assert sig.elbow_angle[:20].mean() < 20


@pytest.mark.parametrize("label", ["correct", "incomplete", "too_fast", "irregular"])
def test_repetition_counter_counts_every_rep(label, rng):
    prof = random_profile("T", rng)
    df = generate_set(label, 8, prof, "s", rng)
    sig = process_frame(df)
    reps = detect_repetitions(sig.elbow_angle, sig.sample_rate_hz, gap_mask=sig.gap_mask)
    assert len(reps) == 8
    assert all(r.start_idx < r.peak_idx < r.end_idx for r in reps)
    assert all(a.end_idx <= b.start_idx for a, b in zip(reps, reps[1:]))  # no double counting


def test_counter_ignores_small_movements():
    t = np.arange(0, 10, 0.02)
    angle = 10 + 8 * np.sin(2 * np.pi * 0.4 * t)  # 16 deg wiggle, below the prominence threshold
    assert detect_repetitions(angle, 50.0) == []


def test_live_counting_never_decreases():
    df = generate_mixed_stream(seed=5)
    counts = [analyze_frame(df.iloc[:n], live=True).total_reps for n in range(150, len(df) + 1, 75)]
    assert counts == sorted(counts)
    assert analyze_frame(df).total_reps == 8


def test_features_are_complete_and_finite(rng):
    prof = random_profile("T", rng)
    df = generate_set(LABEL_TOO_FAST, 4, prof, "s", rng)
    table = build_feature_table(df)
    assert list(table[FEATURE_NAMES].columns) == FEATURE_NAMES
    assert np.isfinite(table[FEATURE_NAMES].to_numpy()).all()
    assert (table["duration_s"] < 1.6).all()


def test_samples_to_frame_roundtrip():
    samples = [{"timestamp_ms": i * 20, "ua": [0, 0, 1, 0, 0, 0], "fa": [0, 0, 1, 0, 0, 0], "force_n": 10} for i in range(5)]
    df = samples_to_frame(samples)
    assert list(df.columns[1:]) == SENSOR_CHANNELS
    assert len(df) == 5


def test_unsupported_exercise_rejected():
    with pytest.raises(UnsupportedExerciseError):
        analyze_frame(generate_mixed_stream(), exercise_id="shoulder_press")


def test_train_save_load_predict(tmp_path):
    raw = generate_dataset(n_participants=4, reps_per_set=6, seed=11)
    table = build_feature_table(raw)
    artefact, evaluation, _ = train_model(table, test_size=0.25, seed=1)
    assert artefact["metadata"]["dataset_type"] == "synthetic"
    assert artefact["metadata"]["validated"] is False
    assert set(evaluation["train_participants"]).isdisjoint(evaluation["test_participants"])
    assert 0.0 <= evaluation["accuracy"] <= 1.0

    path = save_artefact(artefact, tmp_path / "m.pkl")
    model = QualityModel.load(path)
    result = analyze_frame(generate_mixed_stream(seed=2), model=model)
    assert result.classification_available
    assert all(r.label in model.classes and 0 <= r.confidence <= 1 for r in result.reps)
    assert result.correct_reps + result.incorrect_reps == result.total_reps
    assert model.info()["dataset_type"] == "synthetic"


def test_without_model_reps_are_unclassified():
    result = analyze_frame(generate_mixed_stream(seed=4))
    assert result.total_reps > 0
    assert result.unclassified_reps == result.total_reps
    assert result.quality_score is None


def test_missing_model_file_raises(tmp_path):
    with pytest.raises(ModelLoadError):
        QualityModel.load(tmp_path / "missing.pkl")


def test_pipeline_config_roundtrip():
    cfg = PipelineConfig(min_rep_prominence_deg=30)
    assert PipelineConfig.from_dict(cfg.to_dict()) == cfg
