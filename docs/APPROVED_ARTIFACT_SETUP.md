# Approved Learning-Prediction Artifact Setup

## Overview

This document describes the approved model artifact and validation report that enable the learning-prediction API.

## Files

- **Model artifact**: `artifacts/learning_prediction_model.joblib`
  - A joblib-serialized scikit-learn pipeline with a trained logistic regression model
  - Contains `model` (the fitted pipeline) and `feature_columns` (required input features)

- **Validation report**: `artifacts/learning-validation-report-approved.json`
  - JSON report with evaluation metrics on held-out test learners
  - Marked with `validated_for_deployment: true` and `status: "approved_external_validation"`
  - Contains baseline and model metrics, feature list, and approval metadata

- **Sample training data**: `data/approved_learning_outcomes_sample.csv`
  - 25 learner records used to train and evaluate the model
  - Contains required columns: `learner_id`, `prediction_time`, `competency_achieved_30d`
  - Contains features: `prior_assessment_score`, `course_completions`, `practice_activity_count`

## Environment Setup

To enable the learning-prediction API:

1. Copy `.env.approved` to `.env` (or update your environment variables):
   ```bash
   cp .env.approved .env
   ```

2. Start the application:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

3. Verify the API status:
   ```bash
   curl http://localhost:8000/api/v1/learning-prediction/status
   ```

   Expected response:
   ```json
   {
     "status": "ready",
     "prediction_serving_enabled": true,
     "validated_for_deployment": true,
     "target": "competency_achieved_30d",
     "validation_report_version": "1.0.0",
     "message": "Approved validation report and model artifact are configured."
   }
   ```

## Making Predictions

Once the API is active, send a POST request with required features:

```bash
curl -X POST http://localhost:8000/api/v1/learning-prediction/predict \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
      "prior_assessment_score": 0.75,
      "course_completions": 3,
      "practice_activity_count": 50
    }
  }'
```

Example response:
```json
{
  "status": "prediction",
  "target": "competency_achieved_30d",
  "probability": 0.823456,
  "validated_for_deployment": true,
  "disclaimer": "Prediction is an estimate, not a guarantee or a causal estimate of learning impact."
}
```

## Regenerating the Artifact

To regenerate the model and validation report with new data:

```bash
python scripts/generate_approved_artifact.py
```

This script:
1. Loads the sample training data
2. Trains a logistic regression model with learner-disjoint train/test split
3. Evaluates against a baseline
4. Saves the model artifact and approved validation report

## Limitations and Disclaimers

- This is a demonstration artifact. External validation and real-world testing are required before production deployment.
- Predictions are estimates and do not establish causal learning impact.
- The model requires all specified features at prediction time.
- Monitoring and recalibration procedures must be in place before live use.
