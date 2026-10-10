from fastapi import FastAPI
from app.api.routes import router as api_router

app = FastAPI(
    title="RDASHPHDIA-ELP Learning Intelligence Service",
    description=(
        "A prototype enterprise learning service that combines skill-gap analysis, "
        "compliance tracking, adaptive course recommendations, and a population skill field."
    ),
    version="0.2.0",
)
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
