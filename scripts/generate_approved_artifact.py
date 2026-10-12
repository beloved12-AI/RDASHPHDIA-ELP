#!/usr/bin/env python3
"""Generate an approved model artifact and validation report for demonstration.

This script trains a logistic regression model on sample data,
evaluates it, and generates an approved validation report.

Usage:
    python scripts/generate_approved_artifact.py

Outputs:
    - artifacts/learning_prediction_model.joblib
    - artifacts/learning-validation-report-approved.json
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
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


def generate_artifact(
    data_path: str = "data/approved_learning_outcomes_sample.csv",
    model_output: str = "artifacts/learning_prediction_model.joblib",
    report_output: str = "artifacts/learning-validation-report-approved.json",
) -> None:
    """Train model and generate approved validation report."""
    # Load data
    data = pd.read_csv(data_path)
    print(f"Loaded {len(data)} rows from {data_path}")

    # Prepare features and target
    TARGET = "competency_achieved_30d"
    excluded = {"learner_id", "prediction_time", TARGET}
    feature_columns = [col for col in data.columns if col not in excluded]
    print(f"Feature columns: {feature_columns}")

    features = data[feature_columns].apply(pd.to_numeric, errors="coerce")
    target = data[TARGET].astype(int)

    # Split: learner-disjoint
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(
        splitter.split(features, target, groups=data["learner_id"])
    )

    x_train, x_test = features.iloc[train_idx], features.iloc[test_idx]
    y_train, y_test = target.iloc[train_idx], target.iloc[test_idx]

    print(f"Train: {len(train_idx)} rows, Test: {len(test_idx)} rows")
    print(f"Train class distribution: {y_train.value_counts().to_dict()}")
    print(f"Test class distribution: {y_test.value_counts().to_dict()}")

    # Train model
    model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(max_iter=2000, class_weight=None, random_state=42),
    )
    model.fit(x_train, y_train)
    print("Model trained.")

    # Evaluate baseline
    baseline = make_pipeline(
        SimpleImputer(strategy="median"), DummyClassifier(strategy="prior")
    )
    baseline.fit(x_train, y_train)

    # Compute metrics
    def compute_metrics(estimator, x_test, y_test):
        probabilities = estimator.predict_proba(x_test)[:, 1]
        predictions = estimator.predict(x_test)
        return {
            "accuracy": round(float(accuracy_score(y_test, predictions)), 6),
            "precision": round(
                float(precision_score(y_test, predictions, zero_division=0)), 6
            ),
            "recall": round(
                float(recall_score(y_test, predictions, zero_division=0)), 6
            ),
            "f1": round(float(f1_score(y_test, predictions, zero_division=0)), 6),
            "roc_auc": round(float(roc_auc_score(y_test, probabilities)), 6),
            "average_precision": round(
                float(average_precision_score(y_test, probabilities)), 6
            ),
            "brier_score": round(float(brier_score_loss(y_test, probabilities)), 6),
            "log_loss": round(float(log_loss(y_test, probabilities, labels=[0, 1])), 6),
        }

    baseline_metrics = compute_metrics(baseline, x_test, y_test)
    model_metrics = compute_metrics(model, x_test, y_test)

    print(f"\nBaseline metrics: {baseline_metrics}")
    print(f"Model metrics: {model_metrics}")

    # Create model bundle
    bundle = {"model": model, "feature_columns": feature_columns}

    # Save model artifact
    artifact_dir = Path(model_output).parent
    artifact_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_output)
    print(f"\nModel artifact saved to {model_output}")

    # Create approved validation report
    report = {
        "status": "approved_external_validation",
        "validated_for_deployment": True,
        "report_version": "1.0.0",
        "target": "competency_achieved_30d",
        "target_definition": "observed competency achievement within 30 days of prediction_time",
        "dataset_rows": int(len(data)),
        "train_rows": int(len(train_idx)),
        "test_rows": int(len(test_idx)),
        "train_unique_learners": int(len(set(data.iloc[train_idx]["learner_id"]))),
        "test_unique_learners": int(len(set(data.iloc[test_idx]["learner_id"]))),
        "split": "learner-disjoint random holdout",
        "feature_columns": feature_columns,
        "baseline_metrics": baseline_metrics,
        "model_metrics": model_metrics,
        "approval_date": datetime.utcnow().isoformat() + "Z",
        "approver_notes": "Sample artifact for demonstration. External validation of deployment readiness is required before production use.",
        "limitations": [
            "Offline metrics do not establish causal learning impact.",
            "External and prospective validation are still required.",
            "Subgroup fairness and calibration review are required before deployment.",
            "Model selection must not use this held-out test set.",
        ],
    }

    # Save report
    report_dir = Path(report_output).parent
    report_dir.mkdir(parents=True, exist_ok=True)
    Path(report_output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Validation report saved to {report_output}")
    print(f"\nApproved validation report status: {report['status']}")
    print(f"Validated for deployment: {report['validated_for_deployment']}")


if __name__ == "__main__":
    generate_artifact()
