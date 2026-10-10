from fastapi import FastAPI

from app.api.biomedical import router as biomedical_router
from app.api.routes import router as api_router


app = FastAPI(
    title="RDASHPHDIA-ELP Learning Intelligence Service",
    description=(
        "A prototype enterprise learning service with a synthetic-data biomedical "
        "research simulator. The biomedical endpoints are not for clinical use."
    ),
    version="0.3.0",
)
app.include_router(api_router, prefix="/api/v1")
app.include_router(biomedical_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
