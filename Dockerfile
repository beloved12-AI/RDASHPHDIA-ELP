FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
EXPOSE 8080

# Set environment variables for approved model and validation report
ENV LEARNING_PREDICTION_MODEL_PATH=/app/artifacts/learning_prediction_model.joblib
ENV LEARNING_PREDICTION_VALIDATION_REPORT=/app/artifacts/learning-validation-report-approved.json

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
