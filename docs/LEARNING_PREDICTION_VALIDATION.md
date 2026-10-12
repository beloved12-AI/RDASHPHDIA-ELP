# Learning-prediction validation plan

## Status: validation-ready workflow, not yet an empirically validated model

The current ELP recommendation engine is a transparent heuristic. Its skill-gap rankings and recommendation scores are not learned outcome predictions. Do not describe them as validated learning predictions. This repository now defines an evaluation protocol and a reproducible evaluator; no real outcome dataset has been supplied, so this project has **no empirical accuracy claim yet**.

## First prediction target

For the first supervised experiment, predict:

**Will a learner achieve a defined competency within 30 days after a recorded prediction time?**

Use `competency_achieved_30d` as the binary label (1 = achieved within the window, 0 = not achieved within the window). Define the competency rubric and the 30-day observation window before collecting data. Ensure negative labels have a complete follow-up window; otherwise mark them as censored/missing rather than as failures.

## Dataset contract

One row per learner per explicitly defined prediction index. The initial evaluator intentionally requires one row per learner to prevent repeated observations from leaking across splits.

Required columns:

- `learner_id`: pseudonymous stable ID; keep direct identifiers out of the dataset.
- `prediction_time`: ISO-8601 timestamp at which the prediction would have been made.
- `competency_achieved_30d`: observed binary outcome after the prediction time.
- One or more numeric feature columns available **at prediction time only** (e.g. pre-prediction assessment score, prior course completions, practice activity counts).

Do not include post-prediction assessment scores, future completion events, final grades, labels derived from the target window, or identifiers that encode the outcome. Document feature definitions, provenance, missingness, cohort, consent/legal basis, retention, and the competency rubric. Keep data pseudonymous and access-controlled.

## Evaluation protocol

1. Freeze the target, cohort definition, feature list and metrics before inspecting test results.
2. Compare a prior-probability dummy baseline with logistic regression using a median imputer and standardization. The model is a baseline, not assumed to be best.
3. Default mode splits by learner, ensuring learner IDs cannot cross train/test. Use `--time-aware` for a stricter chronological holdout: test predictions come from later timestamps and test learners are excluded from training.
4. Require both outcome classes in train and test. Do not tune on the held-out test set. If the dataset is too small or a split lacks both classes, the evaluator fails rather than fabricating results.
5. Report accuracy, precision, recall, F1, ROC-AUC, average precision, Brier score and log loss for both baseline and model. For publication, add confidence intervals (prefer bootstrap resampling by learner/cohort), calibration plots, subgroup performance and external/prospective evaluation.
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

The evaluator will not generate example rows or invent metrics. It rejects duplicate learner IDs, invalid targets, missing required fields, insufficient samples and splits without both classes. The report sets `validated_for_deployment` to false intentionally: passing an offline split is not enough to authorize production use.

## Validation gates before any deployment claim

- [ ] Approved real outcomes and documented target/competency rubric.
- [ ] Data quality and leakage review by someone other than the model author.
- [ ] Held-out model outperforms a baseline on pre-registered primary metrics.
- [ ] Calibration, confidence intervals and subgroup analysis reviewed.
- [ ] External cohort or prospective evaluation completed.
- [ ] Human review, user communication, privacy/security, monitoring and rollback plan in place.
- [ ] Reproducible report and data/model versions retained.

Until these gates are met, label the frontend's illustrative metrics as **demo-only** and describe the recommender as a heuristic, not a validated predictor. Prediction accuracy alone does not show that recommendations cause improved learning outcomes.


## Live API gate

The API status route is `GET /api/v1/learning-prediction/status`; inference is `POST /api/v1/learning-prediction/predict` with a JSON `features` object. It returns `503 VALIDATION_PENDING` unless the configured model bundle and report both exist and the report explicitly carries `status: approved_external_validation` and `validated_for_deployment: true`. The evaluator in this repository never sets that approval flag automatically. External review must create/approve the report after reviewing real, observed outcomes.
