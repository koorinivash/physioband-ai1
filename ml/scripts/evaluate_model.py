"""Evaluate a saved model on a separate labelled dataset (e.g. newly collected volunteers).

    python scripts/evaluate_model.py --data data/raw/P09 --model saved_models/biceps_curl_quality.pkl
"""
import argparse
import json
from pathlib import Path

from _bootstrap import ML_ROOT

from physioband_ml.dataset import build_feature_table
from physioband_ml.evaluation import evaluate_predictions, plot_confusion_matrix
from physioband_ml.io import load_sensor_csv, load_sensor_folder
from physioband_ml.models import QualityModel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", required=True)
    parser.add_argument("--model", default=str(ML_ROOT / "saved_models" / "biceps_curl_quality.pkl"))
    parser.add_argument("--out", default=str(ML_ROOT / "reports" / "external_evaluation.json"))
    args = parser.parse_args()

    model = QualityModel.load(args.model)
    path = Path(args.data)
    raw = load_sensor_folder(path) if path.is_dir() else load_sensor_csv(path)
    table = build_feature_table(raw, model.pipeline_config)
    preds = model.predict(table.to_dict("records"))
    y_pred = [p.label for p in preds]
    labels = sorted(set(table["label"]) | set(model.classes))
    evaluation = evaluate_predictions(table["label"], y_pred, labels)
    evaluation["model"] = model.info()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evaluation, indent=2, default=str))
    plot_confusion_matrix(evaluation, out.with_suffix(".png"), "Confusion matrix (external evaluation set)")
    print(f"Model status: {model.info()['status_note']}")
    print(f"Accuracy {evaluation['accuracy']:.4f}  Macro F1 {evaluation['macro_avg']['f1']:.4f}  n={len(table)}")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
