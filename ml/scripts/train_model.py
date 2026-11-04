"""Train the movement-quality classifier (Random Forest baseline, optional XGBoost).

    python scripts/train_model.py --data data/synthetic/synthetic_biceps_curl.csv
    python scripts/train_model.py --data data/raw --algorithm random_forest

Outputs:
    saved_models/biceps_curl_quality.pkl   model artefact loaded by FastAPI
    reports/<name>_evaluation.json             metrics on the held-out participants
    reports/<name>_confusion_matrix.png
    reports/<name>_feature_importance.png
"""
import argparse
import json
from pathlib import Path

from _bootstrap import ML_ROOT

from physioband_ml.config import PipelineConfig
from physioband_ml.dataset import build_feature_table
from physioband_ml.evaluation import plot_confusion_matrix, plot_feature_importance
from physioband_ml.feature_extraction import FEATURE_NAMES
from physioband_ml.io import load_sensor_csv, load_sensor_folder
from physioband_ml.models.trainer import save_artefact, train_model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", required=True, help="raw sensor CSV file or folder")
    parser.add_argument("--algorithm", choices=["random_forest", "xgboost"], default="random_forest")
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model-out", default=str(ML_ROOT / "saved_models" / "biceps_curl_quality.pkl"))
    parser.add_argument("--reports-dir", default=str(ML_ROOT / "reports"))
    args = parser.parse_args()

    path = Path(args.data)
    raw = load_sensor_folder(path) if path.is_dir() else load_sensor_csv(path)
    cfg = PipelineConfig()
    table = build_feature_table(raw, cfg)
    print(f"Feature table: {len(table)} repetitions, {table['participant_id'].nunique()} participants")

    artefact, evaluation, predictions = train_model(table, args.algorithm, args.test_size, args.seed, cfg)
    meta = artefact["metadata"]
    model_path = save_artefact(artefact, args.model_out)

    reports = Path(args.reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    name = f"{meta['dataset_type']}_{args.algorithm}"
    evaluation["dataset_type"] = meta["dataset_type"]
    evaluation["status_note"] = meta["status_note"]
    (reports / f"{name}_evaluation.json").write_text(json.dumps(evaluation, indent=2))
    predictions.to_csv(reports / f"{name}_test_predictions.csv", index=False)
    title = f"Confusion matrix ({meta['dataset_type'].upper()} data, held-out participants)"
    plot_confusion_matrix(evaluation, reports / f"{name}_confusion_matrix.png", title)
    plot_feature_importance(artefact["model"], FEATURE_NAMES, reports / f"{name}_feature_importance.png")

    print(f"\n{meta['status_note']}")
    print(f"Split: {evaluation['split_method']}")
    print(f"Test participants: {', '.join(evaluation['test_participants'])}")
    print(f"Accuracy: {evaluation['accuracy']:.4f}   Macro F1: {evaluation['macro_avg']['f1']:.4f}")
    for label, m in evaluation["per_class"].items():
        print(f"  {label:11s} precision={m['precision']:.3f} recall={m['recall']:.3f} f1={m['f1']:.3f} n={m['support']}")
    print(f"\nModel saved to {model_path}")
    print(f"Reports written to {reports}")


if __name__ == "__main__":
    main()
