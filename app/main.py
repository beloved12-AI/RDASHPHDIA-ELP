import hmac
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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
@app.middleware("http")
async def require_api_bearer_token(request: Request, call_next):
    """Require a shared bearer token for API routes when configured."""
    expected_token = os.getenv("API_AUTH_TOKEN", "").strip()
    if (
        expected_token
        and request.url.path.startswith("/api/v1/")
        and request.method != "OPTIONS"
    ):
        authorization = request.headers.get("Authorization", "")
        scheme, separator, supplied_token = authorization.partition(" ")
        if (
            not separator
            or scheme.lower() != "bearer"
            or not supplied_token
            or not hmac.compare_digest(supplied_token, expected_token)
        ):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid bearer token"},
                headers={"WWW-Authenticate": "Bearer"},
            )
    return await call_next(request)


app.include_router(api_router, prefix="/api/v1")
app.include_router(biomedical_router, prefix="/api/v1")
app.include_router(prediction_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
