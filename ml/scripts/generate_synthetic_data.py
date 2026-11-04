"""Generate a SYNTHETIC biceps-curl dataset for testing the software pipeline.

The output is clearly marked (is_synthetic=True, participant IDs start with SYN-).
Do NOT report results obtained from this data as experimental performance.

    python scripts/generate_synthetic_data.py --participants 10 --reps 10
"""
import argparse

from _bootstrap import ML_ROOT

from physioband_ml.synthetic import generate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--participants", type=int, default=10)
    parser.add_argument("--reps", type=int, default=10, help="repetitions per recorded set")
    parser.add_argument("--sets", type=int, default=1, help="sets per quality label per participant")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default=str(ML_ROOT / "data" / "synthetic" / "synthetic_biceps_curl.csv"))
    args = parser.parse_args()

    df = generate_dataset(args.participants, args.reps, args.sets, args.seed)
    from pathlib import Path

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"[SYNTHETIC] wrote {len(df)} samples, {df['session_id'].nunique()} sets, "
          f"{df['participant_id'].nunique()} simulated participants -> {out}")


if __name__ == "__main__":
    main()
