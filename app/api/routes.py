from fastapi import APIRouter

router = APIRouter()

@router.get("/optimize")
async def optimize(q: str = "default"):
    # placeholder: return job id or optimization result
    return {"job": "not_implemented", "query": q}
