#!/usr/bin/env python3
"""Evaluate a binary learning-outcome model on held-out learners.

This script never generates synthetic evaluation data. It requires an observed
outcome column and writes metrics only when the held-out cohort supports them.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


REQUIRED_COLUMNS = {"learner_id", "prediction_time", "competency_achieved_30d"}
TARGET = "competency_achieved_30d"


def evaluate_dataset(
    data: pd.DataFrame,
    *,
    test_size: float = 0.2,
    random_state: int = 42,
    time_aware: bool = False,
) -> dict[str, Any]:
    """Evaluate against a prior-probability baseline using learner-disjoint data."""
    missing = REQUIRED_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    if not 0.1 <= test_size <= 0.5:
        raise ValueError("test_size must be between 0.1 and 0.5")
    if data["learner_id"].isna().any() or data["prediction_time"].isna().any():
        raise ValueError("learner_id and prediction_time cannot be missing")
    if data["learner_id"].duplicated().any():
        raise ValueError(
            "Provide one prediction row per learner; aggregate repeated learner "
            "records at a defined prediction index before evaluation."
        )
    if data[TARGET].isna().any() or not set(data[TARGET].unique()).issubset({0, 1}):
        raise ValueError(f"{TARGET} must contain observed binary labels 0 and 1")
    if data[TARGET].nunique() != 2 or len(data) < 20:
        raise ValueError("At least 20 rows and both target classes are required")

    excluded = {"learner_id", "prediction_time", TARGET}
    feature_columns = [column for column in data.columns if column not in excluded]
    if not feature_columns:
        raise ValueError("At least one feature column is required")
    features = data[feature_columns].apply(pd.to_numeric, errors="coerce")
    if features.isna().all(axis=None):
        raise ValueError("All feature values are missing or non-numeric")

    work = data.copy()
    work["__row_index"] = range(len(work))
    if time_aware:
        times = pd.to_datetime(work["prediction_time"], utc=True, errors="coerce")
        if times.isna().any():
            raise ValueError("prediction_time must contain valid timestamps")
        unique_times = sorted(times.unique())
        if len(unique_times) < 2:
            raise ValueError("Time-aware evaluation requires at least two timestamps")
        cutoff_index = max(1, min(len(unique_times) - 1, int(len(unique_times) * (1-test_size))))
        cutoff = unique_times[cutoff_index]
        test_mask = times >= cutoff
        train_mask = times < cutoff
        train_learners = set(work.loc[train_mask, "learner_id"])
        # Strict cohort holdout: no learner may occur on both sides.
        test_mask &= ~work["learner_id"].isin(train_learners)
        train_idx = work.loc[train_mask, "__row_index"].to_numpy()
        test_idx = work.loc[test_mask, "__row_index"].to_numpy()
        split_description = "chronological holdout; test learners absent from training"
    else:
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
        train_idx, test_idx = next(
            splitter.split(features, data[TARGET], groups=data["learner_id"])
        )
        cutoff = None
        split_description = "learner-disjoint random holdout"

    if len(train_idx) < 10 or len(test_idx) < 10:
        raise ValueError("Split leaves fewer than 10 rows in train or test; collect more data")
    y_train = data.iloc[train_idx][TARGET].astype(int)
    y_test = data.iloc[test_idx][TARGET].astype(int)
    if y_train.nunique() != 2 or y_test.nunique() != 2:
        raise ValueError("Both classes must appear in train and held-out test sets")
    train_ids = set(data.iloc[train_idx]["learner_id"])
    test_ids = set(data.iloc[test_idx]["learner_id"])
    if train_ids & test_ids:
        raise ValueError("Data leakage detected: learner IDs overlap between train and test")

    x_train, x_test = features.iloc[train_idx], features.iloc[test_idx]
    baseline = make_pipeline(SimpleImputer(strategy="median"), DummyClassifier(strategy="prior"))
    model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(max_iter=2000, class_weight=None, random_state=random_state),
    )
    baseline.fit(x_train, y_train)
    model.fit(x_train, y_train)
    results: dict[str, Any] = {
        "status": "evaluated_on_held_out_observed_data",
        "validated_for_deployment": False,
        "target": TARGET,
        "target_definition": "observed competency achievement within 30 days of prediction_time",
        "dataset_rows": int(len(data)),
        "train_rows": int(len(train_idx)),
        "test_rows": int(len(test_idx)),
        "train_unique_learners": int(len(train_ids)),
        "test_unique_learners": int(len(test_ids)),
        "split": split_description,
        "time_cutoff_utc": str(cutoff) if cutoff is not None else None,
        "feature_columns": feature_columns,
        "baseline_metrics": {},
        "model_metrics": {},
        "limitations": [
            "Offline metrics do not establish causal learning impact.",
            "External and prospective validation are still required.",
            "Subgroup fairness and calibration review are required before deployment.",
            "Model selection must not use this held-out test set.",
        ],
    }
    for name, estimator in (("baseline_metrics", baseline), ("model_metrics", model)):
        probabilities = estimator.predict_proba(x_test)[:, 1]
        predictions = estimator.predict(x_test)
        metrics = {
            "accuracy": accuracy_score(y_test, predictions),
            "precision": precision_score(y_test, predictions, zero_division=0),
            "recall": recall_score(y_test, predictions, zero_division=0),
            "f1": f1_score(y_test, predictions, zero_division=0),
            "roc_auc": roc_auc_score(y_test, probabilities),
            "average_precision": average_precision_score(y_test, probabilities),
            "brier_score": brier_score_loss(y_test, probabilities),
            "log_loss": log_loss(y_test, probabilities, labels=[0, 1]),
        }
        results[name] = {key: round(float(value), 6) for key, value in metrics.items()}
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="CSV containing observed learner outcomes")
    parser.add_argument("--output", default="artifacts/learning-validation-report.json")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--time-aware", action="store_true",
                        help="Use chronological holdout and keep test learners out of training")
    args = parser.parse_args()
    data = pd.read_csv(args.data)
    report = evaluate_dataset(data, test_size=args.test_size, time_aware=args.time_aware)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("\nMetrics are offline evaluation results, not proof of causal learning impact or deployment readiness.")


if __name__ == "__main__":
    main()
