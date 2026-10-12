"""Live prediction endpoints that fail closed until an approved artifact is configured."""
import json
import os
from pathlib import Path
from typing import Dict

import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator


router = APIRouter(prefix="/learning-prediction", tags=["learning-prediction"])


class PredictionRequest(BaseModel):
    features: Dict[str, float]

    @validator("features")
    def features_must_not_be_empty(cls, value):
        if not value:
            raise ValueError("features must contain at least one item")
        return value


def _approved_artifact():
    model_path = os.getenv("LEARNING_PREDICTION_MODEL_PATH", "").strip()
    report_path = os.getenv("LEARNING_PREDICTION_VALIDATION_REPORT", "").strip()
    if not model_path or not report_path:
        return None, "No model artifact and validation report are configured."
    model_file, report_file = Path(model_path), Path(report_path)
    if not model_file.is_file() or not report_file.is_file():
        return None, "The configured model artifact or validation report is missing."
    try:
        report = json.loads(report_file.read_text(encoding="utf-8"))
        bundle = joblib.load(model_file)
    except Exception:
        return None, "The configured model artifact or validation report could not be loaded."
    if report.get("validated_for_deployment") is not True or report.get("status") != "approved_external_validation":
        return None, "The validation report has not passed the required external validation approval gate."
    if not isinstance(bundle, dict) or not bundle.get("model") or not bundle.get("feature_columns"):
        return None, "The model artifact bundle is invalid."
    return (bundle, report), None


@router.get("/status")
async def prediction_status():
    loaded, reason = _approved_artifact()
    if loaded is None:
        return {
            "status": "validation_pending",
            "prediction_serving_enabled": False,
            "validated_for_deployment": False,
            "message": reason,
        }
    bundle, report = loaded
    return {
        "status": "ready",
        "prediction_serving_enabled": True,
        "validated_for_deployment": True,
        "target": report.get("target"),
        "validation_report_version": report.get("report_version"),
        "message": "Approved validation report and model artifact are configured.",
    }


@router.post("/predict")
async def predict(request: PredictionRequest):
    loaded, reason = _approved_artifact()
    if loaded is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "VALIDATION_PENDING", "message": reason},
        )
    bundle, report = loaded
    feature_columns = bundle["feature_columns"]
    missing = sorted(set(feature_columns) - set(request.features))
    if missing:
        raise HTTPException(status_code=422, detail={"missing_features": missing})
    row = pd.DataFrame([[request.features[column] for column in feature_columns]], columns=feature_columns)
    probability = float(bundle["model"].predict_proba(row)[0][1])
    return {
        "status": "prediction",
        "target": report.get("target", "competency_achieved_30d"),
        "probability": round(probability, 6),
        "validated_for_deployment": True,
        "disclaimer": "Prediction is an estimate, not a guarantee or a causal estimate of learning impact.",
    }
