# PhysioBand AI - sensor data

| Folder | Contents |
|---|---|
| `raw/` | **Real** recordings collected from volunteers with `scripts/collect_data.py` (one CSV per recorded set, grouped by participant). |
| `processed/` | Per-repetition feature tables produced by `scripts/extract_features.py`. |
| `sample/` | `sensor_data_template.csv` (header only) and `sample_biceps_curl_synthetic.csv` (**SYNTHETIC**, 1 simulated participant, 4 sets). |
| `synthetic/` | Output of `scripts/generate_synthetic_data.py` (**SYNTHETIC**, git-ignored, reproducible with the same seed). |

## CSV format (one row per sample, 50 Hz)

| Column | Unit | Description |
|---|---|---|
| `participant_id` | - | Anonymous volunteer ID, e.g. `P01`. Synthetic IDs start with `SYN-`. |
| `session_id` | - | One recorded set, e.g. `P01-correct-20261104-101500`. |
| `exercise_id` | - | `biceps_curl` |
| `label` | - | `correct`, `incomplete`, `too_fast` or `irregular` (the quality the volunteer was asked to perform). |
| `is_synthetic` | bool | `True` for simulated data, `False` for real recordings. |
| `timestamp_ms` | ms | ESP32 `millis()` at sampling time. |
| `ua_ax, ua_ay, ua_az` | g | Upper-arm MPU6050 (I2C 0x68) accelerometer. |
| `ua_gx, ua_gy, ua_gz` | deg/s | Upper-arm gyroscope (bias-corrected on the ESP32). |
| `fa_ax ... fa_gz` | g, deg/s | Forearm MPU6050 (I2C 0x69). |
| `force_n` | N | Resistance-band tension from the S-type load cell + HX711. |

## Labelling protocol (real data)

1. Strap the sensors as described in `docs/HARDWARE_SETUP.md`, tare the load cell, run `gyrocal`.
2. For each volunteer record **one set per label** (more sets are better), 8-12 reps each:
   * `correct` - full range (straight arm to forearm near vertical), about 2 s up / 2 s down, upper arm still.
   * `incomplete` - stop roughly half way up or do not straighten the arm at the bottom.
   * `too_fast` - full range but each rep under about 1 s.
   * `irregular` - jerky / stop-and-go motion, or swinging the upper arm to cheat the weight.
3. `python scripts/collect_data.py --port COM5 --participant P01 --label correct --reps 10`
4. Validate: `python scripts/validate_dataset.py data/raw`
5. Train: `python scripts/train_model.py --data data/raw` - the split is participant-wise, so collect at least 3 volunteers (ideally 8+).

Every repetition found by the repetition counter inside a set inherits that set's label.
Remove failed sets (e.g. the volunteer did the wrong movement) before training.
