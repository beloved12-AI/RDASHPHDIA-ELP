import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.biomedical import router as biomedical_router
from app.api.routes import router as api_router
from app.api.prediction import router as prediction_router


def _allowed_origins() -> list[str]:
    configured = os.getenv("ALLOWED_ORIGINS", "")
    defaults = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "https://beloved12-ai.github.io",
    ]
    extra = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    return list(dict.fromkeys(defaults + extra))


app = FastAPI(
    title="RDASHPHDIA-ELP Learning Intelligence Service",
    description=(
        "A prototype enterprise learning service with a synthetic-data biomedical "
        "research simulator. The biomedical endpoints are not for clinical use."
    ),
    version="0.3.1",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "Authorization"],
)
app.include_router(api_router, prefix="/api/v1")
app.include_router(biomedical_router, prefix="/api/v1")
app.include_router(prediction_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
