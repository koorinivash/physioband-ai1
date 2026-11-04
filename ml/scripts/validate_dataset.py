"""Validate sensor CSV files before training.

    python scripts/validate_dataset.py data/raw
    python scripts/validate_dataset.py data/synthetic/synthetic_biceps_curl.csv
"""
import argparse
from pathlib import Path

from _bootstrap import ML_ROOT  # noqa: F401

from physioband_ml.config import QUALITY_LABELS
from physioband_ml.io import load_sensor_csv, load_sensor_folder
from physioband_ml.repetition_counting import detect_repetitions
from physioband_ml.segmentation import process_frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", help="CSV file or folder of CSV files")
    args = parser.parse_args()
    path = Path(args.path)
    df = load_sensor_folder(path) if path.is_dir() else load_sensor_csv(path)

    problems = 0
    bad_labels = set(df["label"].astype(str).unique()) - set(QUALITY_LABELS)
    if bad_labels:
        print(f"ERROR unknown labels: {sorted(bad_labels)}")
        problems += 1
    if "is_synthetic" in df and df["is_synthetic"].astype(bool).any():
        print("NOTE  dataset contains SYNTHETIC samples")

    print(f"{'session':40s} {'label':11s} {'samples':>8s} {'reps':>5s}  issues")
    for session_id, session in df.groupby("session_id"):
        try:
            sig = process_frame(session)
            reps = detect_repetitions(sig.elbow_angle, sig.sample_rate_hz, gap_mask=sig.gap_mask)
            issues = "; ".join(sig.validation.issues) or "-"
            if not reps:
                issues = "NO REPETITIONS DETECTED; " + issues
                problems += 1
            print(f"{str(session_id)[:40]:40s} {session['label'].iloc[0]:11s} {len(session):8d} {len(reps):5d}  {issues}")
        except Exception as exc:  # report and continue with other sessions
            problems += 1
            print(f"{str(session_id)[:40]:40s} ERROR {exc}")

    print("\nLabel distribution (samples):")
    print(df["label"].value_counts().to_string())
    print(f"\n{'OK' if problems == 0 else f'{problems} problem(s) found'}")


if __name__ == "__main__":
    main()
