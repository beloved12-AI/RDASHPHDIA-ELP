from fastapi import FastAPI
from app.api.routes import router as api_router

app = FastAPI(title="Hybrid Particles Optimization Service")
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
