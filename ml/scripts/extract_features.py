"""Extract per-repetition features from raw sensor CSV files.

    python scripts/extract_features.py data/synthetic/synthetic_biceps_curl.csv
    python scripts/extract_features.py data/raw --out data/processed/features_collected.csv
"""
import argparse
from pathlib import Path

from _bootstrap import ML_ROOT

from physioband_ml.dataset import build_feature_table
from physioband_ml.io import load_sensor_csv, load_sensor_folder


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", help="CSV file or folder of CSV files")
    parser.add_argument("--out", default=str(ML_ROOT / "data" / "processed" / "features.csv"))
    args = parser.parse_args()

    path = Path(args.path)
    raw = load_sensor_folder(path) if path.is_dir() else load_sensor_csv(path)
    table = build_feature_table(raw)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out, index=False)
    print(f"Extracted {len(table)} repetitions from {raw['session_id'].nunique()} sets -> {out}")
    print(table["label"].value_counts().to_string())


if __name__ == "__main__":
    main()
