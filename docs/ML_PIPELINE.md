# PhysioBand AI - ML Pipeline

Package: `ml/src/physioband_ml` (imported by both the training scripts and the FastAPI backend, so training
and inference use exactly the same code and configuration).

```text
raw samples -> validation -> resampling + gap handling -> calibration -> Butterworth low-pass
            -> gravity tracking (complementary filter) -> elbow angle / velocity / upper-arm swing
            -> repetition counting (peak / cycle detection) -> per-rep features
            -> Random Forest -> label + confidence -> feedback text -> session summary
```

## 1. Stages

| Stage | Module | What it does |
|---|---|---|
| Validation | `preprocessing/validation.py` | Requires all 13 channels; drops bad / duplicate timestamps; replaces missing, non-numeric or out-of-range values (accel > 8.5 g, gyro > 1050 deg/s, force outside -50..2000 N) with NaN |
| Missing values | `preprocessing/cleaning.py` | Linear interpolation onto a uniform 50 Hz grid; gaps > 200 ms are flagged (`gap_mask`) and reps spanning them are ignored |
| Calibration | `preprocessing/calibration.py` | Optional per-device gyro bias, accel offset, force offset/scale (the ESP32 already applies its own load-cell factor and gyro bias) |
| Noise filtering | `preprocessing/filtering.py` | 4th-order zero-phase Butterworth low-pass, 5 Hz cut-off |
| Kinematics | `segmentation/kinematics.py` | Complementary filter (alpha 0.98) tracks each IMU's gravity direction; elbow angle = angle between the two; upper-arm swing = rotation from its start direction |
| Repetition counting | `repetition_counting/counter.py` | `find_peaks` on the elbow angle with prominence >= 25 deg and distance >= 0.6 s; boundaries at movement onset/offset; duration 0.5-10 s; live mode waits 0.6 s after a rep ends |
| Features | `feature_extraction/features.py` | 31 features per rep (below) |
| Model | `models/trainer.py`, `models/predictor.py` | Random Forest (300 trees, balanced classes); optional XGBoost |
| Evaluation | `evaluation/metrics.py` | Accuracy, per-class precision / recall / F1, macro & weighted averages, confusion matrix, plots |
| Orchestration | `analysis.py` | `analyze_frame()` - used by the backend |

Configuration: `config.py` (`PipelineConfig`). The config used for training is stored inside the model file
and reused at inference time.

## 2. Features (per repetition)

* **Timing:** duration, concentric (lifting) time, eccentric (lowering) time, tempo ratio.
* **Range:** elbow range of motion, start angle, peak angle.
* **Speed:** mean |angular velocity|, peak velocity, velocity std, mean lifting / lowering velocity.
* **Smoothness:** velocity reversals, dimensionless normalised jerk.
* **Upper arm:** swing range, gyro magnitude mean / max, accel magnitude std.
* **Forearm IMU:** gyro magnitude mean / max, accel magnitude mean / std / max / min.
* **Band tension:** mean, max, min, std, coefficient of variation (consistency), range, rate-of-change std.

## 3. Classes

| Label | Meaning | Signals that support it |
|---|---|---|
| `correct` | Full range, controlled tempo, steady upper arm | ROM, duration, smoothness, swing |
| `incomplete` | Range of motion clearly reduced | ROM, peak / start angle |
| `too_fast` | Full range but very short rep | duration, velocity |
| `irregular` | Jerky / stop-and-go motion or upper-arm swinging | jerk, reversals, swing, tension variability |

These sensors cannot detect every possible posture error (e.g. wrist position, trunk lean without arm swing,
shoulder elevation). Only the four classes above are claimed.

## 4. Dataset workflow

```powershell
cd ml
..\backend\.venv\Scripts\Activate.ps1          # or a separate ml venv, see README
python scripts\collect_data.py --port COM5 --participant P01 --label correct --reps 10
python scripts\validate_dataset.py data\raw
python scripts\extract_features.py data\raw --out data\processed\features_collected.csv
python scripts\train_model.py --data data\raw
python scripts\evaluate_model.py --data data\raw\P09     # optional: separate held-out volunteers
python scripts\predict.py data\raw\P01\<file>.csv
```

* Train / test split is **participant-wise** (`GroupShuffleSplit`) whenever >= 3 participants exist, so no
  volunteer appears in both sets. With fewer participants a stratified random split is used and reported as such.
* `train_model.py` writes `saved_models/biceps_curl_quality.pkl` (loaded by FastAPI at start-up) and
  `reports/<dataset>_<algorithm>_evaluation.json`, confusion-matrix and feature-importance PNGs, test predictions CSV.
* Restart the backend after retraining. `GET /api/v1/ml/model-info` shows which model is loaded.

## 5. Synthetic data and the current demo model

No real volunteer recordings were available while building the software, so the repository contains a
**synthetic** generator (`synthetic.py`, `scripts/generate_synthetic_data.py`) that simulates the two IMUs and the
band tension for the four movement classes. It exists only to test the pipeline end to end.

The shipped `saved_models/biceps_curl_quality.pkl` was trained on 10 simulated participants (400 reps) with a
participant-wise split. It scores 100 % on the 3 held-out simulated participants. **This number is meaningless for
real use**: the synthetic classes were generated to be separable. The model metadata says
`dataset_type: synthetic, validated: false`, and the app shows a "Demo AI model" notice wherever classifications
appear. Replace it by collecting real data and re-running `train_model.py`; the metadata then changes to
`collected` automatically.

## 6. Tests

`ml/tests/test_pipeline.py` (18 tests): validation, gap handling, filtering, elbow-angle tracking, exact rep counts
for all four classes, no double counting, small-movement rejection, monotonic live counting, feature completeness,
model train / save / load / predict, behaviour without a model, unsupported exercise.

```powershell
cd ml
python -m pytest -q
```
