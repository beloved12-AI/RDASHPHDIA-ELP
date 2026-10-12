from pathlib import Path

import pandas as pd
import pytest

from scripts.validate_learning_predictions import evaluate_dataset


def observed_dataset(rows=60):
    return pd.DataFrame({
        "learner_id": [f"learner-{i}" for i in range(rows)],
        "prediction_time": pd.date_range("2025-01-01", periods=rows, freq="D").astype(str),
        "pretest_score": [float(i % 10) / 10 for i in range(rows)],
        "practice_count": [i % 7 for i in range(rows)],
        "competency_achieved_30d": [i % 2 for i in range(rows)],
    })


def test_evaluation_uses_disjoint_learners_and_compares_baseline():
    report = evaluate_dataset(observed_dataset())
    assert report["validated_for_deployment"] is False
    assert report["train_unique_learners"] + report["test_unique_learners"] == 60
    assert report["model_metrics"].keys() == report["baseline_metrics"].keys()
    assert "brier_score" in report["model_metrics"]
    assert report["status"] == "evaluated_on_held_out_observed_data"


def test_time_aware_evaluation_uses_later_unseen_learners():
    report = evaluate_dataset(observed_dataset(), time_aware=True)
    assert report["time_cutoff_utc"] is not None
    assert report["split"].startswith("chronological")
    assert report["train_unique_learners"] + report["test_unique_learners"] <= 60


def test_duplicate_learner_rows_are_rejected():
    data = observed_dataset()
    data.loc[1, "learner_id"] = data.loc[0, "learner_id"]
    with pytest.raises(ValueError, match="one prediction row per learner"):
        evaluate_dataset(data)


def test_missing_target_column_is_rejected():
    data = observed_dataset().drop(columns=["competency_achieved_30d"])
    with pytest.raises(ValueError, match="Missing required columns"):
        evaluate_dataset(data)


def test_insufficient_dataset_fails_closed():
    with pytest.raises(ValueError, match="At least 20 rows"):
        evaluate_dataset(observed_dataset(12))


def test_repository_labels_current_predictions_as_heuristic_not_validated():
    root = Path(__file__).resolve().parents[1]
    docs = root.joinpath("docs/LEARNING_PREDICTION_VALIDATION.md").read_text(encoding="utf-8")
    assert "no empirical accuracy claim yet" in docs
    assert "prediction accuracy alone does not show" in docs.lower()
