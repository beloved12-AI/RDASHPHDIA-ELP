# Learning-prediction validation plan

## Status: validation-ready workflow, not yet an empirically validated model

**No empirical accuracy claim yet.** The workflow is ready for evaluation, but no validated performance claim should be made until held-out observed outcomes and the validation gates below support it.

The current ELP recommendation engine is a transparent heuristic. Its skill-gap rankings and recommendation scores are not learned outcome predictions. Do not describe them as validated learning predictions or as empirically validated performance metrics.

## First prediction target

For the first supervised experiment, predict:

**Will a learner achieve a defined competency within 30 days after a recorded prediction time?**

Use `competency_achieved_30d` as the binary label (1 = achieved within the window, 0 = not achieved within the window). Define the competency rubric and the 30-day observation window before collecting any data.

## Dataset contract

One row per learner per explicitly defined prediction index. The initial evaluator intentionally requires one row per learner to prevent repeated observations from leaking across splits.

Required columns:

- `learner_id`: pseudonymous stable ID; keep direct identifiers out of the dataset.
- `prediction_time`: ISO-8601 timestamp at which the prediction would have been made.
- `competency_achieved_30d`: observed binary outcome after the prediction time.
- One or more numeric feature columns available at prediction time only (e.g. pre-prediction assessment score, prior course completions, practice activity counts).

Do not include post-prediction assessment scores, future completion events, final grades, labels derived from the target window, or identifiers that encode the outcome. Document feature definitions and exclusions in the dataset manifest.

## Evaluation protocol

1. Freeze the target, cohort definition, feature list and metrics before inspecting test results.
2. Compare a prior-probability dummy baseline with logistic regression using a median imputer and standardization. The model is a baseline, not assumed to be best.
3. Default mode splits by learner, ensuring learner IDs cannot cross train/test. Use `--time-aware` for a stricter chronological holdout: test predictions come from later timestamps and test learners are excluded from training.
4. Require both outcome classes in train and test. Do not tune on the held-out test set. If the dataset is too small or a split lacks both classes, the evaluator fails rather than fabricating results.
5. Report accuracy, precision, recall, F1, ROC-AUC, average precision, Brier score and log loss for both baseline and model. For publication, add confidence intervals (prefer bootstrap resampling or an equivalent method) and calibration plots.
6. Keep a versioned, access-controlled dataset manifest and report model/code versions, split settings and data provenance. Never commit private learner data or reports containing personal information.

## Run the evaluator

Install dependencies, then supply your own approved, observed outcome dataset:

```bash
pip install -r requirements.txt
python scripts/validate_learning_predictions.py \
  --data /path/to/approved_learning_outcomes.csv \
  --output artifacts/learning-validation-report.json
```

For future-cohort evaluation:

```bash
python scripts/validate_learning_predictions.py \
  --data /path/to/approved_learning_outcomes.csv \
  --time-aware \
  --output artifacts/learning-validation-report.json
```

The evaluator will not generate example rows or invent metrics. It rejects duplicate learner IDs, invalid targets, missing required fields, insufficient samples and splits without both classes. The script is designed to fail closed rather than silently validate a weak experiment.

## Validation gates before any deployment claim

- [ ] Approved real outcomes and documented target/competency rubric.
- [ ] Data quality and leakage review by someone other than the model author.
- [ ] Held-out model outperforms a baseline on pre-registered primary metrics.
- [ ] Calibration, confidence intervals and subgroup analysis reviewed.
- [ ] External cohort or prospective evaluation completed.
- [ ] Human review, user communication, privacy/security, monitoring and rollback plan in place.
- [ ] Reproducible report and data/model versions retained.

Until these gates are met, label the frontend's illustrative metrics as **demo-only** and describe the recommender as a heuristic, not a validated predictor. Prediction accuracy alone does not show that the system is safe or effective in a learning context.

## Live API gate

The learning-prediction API is intentionally fail-closed until an approved model artifact and validation report are configured.

- Status route: `GET /api/v1/learning-prediction/status`
- Prediction route: `POST /api/v1/learning-prediction/predict`

Example prediction payload:

```json
{
  "features": {
    "feature_name_1": 0.42,
    "feature_name_2": 3.1
  }
}
```

When no approved artifact is configured:

- `GET /api/v1/learning-prediction/status` returns HTTP 200 with a JSON body such as:

```json
{
  "status": "validation_pending",
  "prediction_serving_enabled": false,
  "validated_for_deployment": false,
  "message": "No model artifact and validation report are configured."
}
```

- `POST /api/v1/learning-prediction/predict` returns HTTP 503 with:

```json
{
  "detail": {
    "code": "VALIDATION_PENDING",
    "message": "No model artifact and validation report are configured."
  }
}
```

Prediction serving is enabled only after both of the following are present and approved:

- a valid model artifact
- a validation report whose `validated_for_deployment` flag is `true` and whose status is `approved_external_validation`

The API does not expose live predictions before that approval gate is satisfied.
