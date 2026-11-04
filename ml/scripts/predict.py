"""Run the full analysis (rep counting + quality classification) on one recording.

    python scripts/predict.py data/sample/sample_biceps_curl_synthetic.csv
"""
import argparse
import json

from _bootstrap import ML_ROOT

from physioband_ml.analysis import analyze_frame
from physioband_ml.io import load_sensor_csv
from physioband_ml.models import ModelLoadError, QualityModel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv")
    parser.add_argument("--model", default=str(ML_ROOT / "saved_models" / "biceps_curl_quality.pkl"))
    parser.add_argument("--json", action="store_true", help="print the full JSON result")
    args = parser.parse_args()

    try:
        model = QualityModel.load(args.model)
        print(f"Model: {model.info()['algorithm']} ({model.info()['status_note']})")
    except ModelLoadError as exc:
        model = None
        print(f"WARNING {exc}. Repetitions will be counted without classification.")

    df = load_sensor_csv(args.csv)
    for session_id, session in (df.groupby("session_id") if "session_id" in df else [("recording", df)]):
        result = analyze_frame(session, model=model)
        print(f"\n== {session_id}: {result.total_reps} reps, quality={result.quality_score}%, "
              f"avg tension={result.avg_tension_n} N")
        for rep in result.reps:
            conf = f"{rep.confidence:.2f}" if rep.confidence is not None else "-"
            print(f"  rep {rep.number:2d}  {rep.label_display:27s} conf={conf}  ROM={rep.rom_deg:5.1f} deg  "
                  f"duration={rep.duration_s:.2f} s")
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, default=float))


if __name__ == "__main__":
    main()
