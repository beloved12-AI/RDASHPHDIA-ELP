from typing import Callable

from fastapi import APIRouter, HTTPException, Query, status

from app.api.schemas import CourseCreate, LearnerCreate, LearningEvent
from app.services.learning import ConflictError, LearningService, NotFoundError


router = APIRouter()
learning = LearningService()


def _call(action: Callable):
    try:
        return action()
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except ConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.post("/learners", status_code=status.HTTP_201_CREATED)
async def create_learner(request: LearnerCreate):
    return _call(lambda: learning.create_learner(request))


@router.get("/learners/{learner_id}")
async def get_learner(learner_id: str):
    return _call(lambda: learning.get_learner(learner_id))


@router.post("/courses", status_code=status.HTTP_201_CREATED)
async def create_course(request: CourseCreate):
    return _call(lambda: learning.create_course(request))


@router.get("/courses")
async def list_courses():
    return learning.list_courses()


@router.post("/events")
async def ingest_event(request: LearningEvent):
    return _call(lambda: learning.record_event(request))


@router.get("/learners/{learner_id}/skill-gaps")
async def get_skill_gaps(learner_id: str):
    return _call(lambda: learning.skill_gaps(learner_id))


@router.get("/learners/{learner_id}/recommendations")
async def get_recommendations(
    learner_id: str,
    limit: int = Query(5, ge=1, le=50),
):
    return _call(lambda: learning.recommendations(learner_id, limit))


@router.get("/learners/{learner_id}/compliance")
async def get_compliance(learner_id: str):
    return _call(lambda: learning.compliance(learner_id))


@router.get("/skills/field")
async def get_skill_field():
    return learning.skill_field()


@router.get("/optimize", deprecated=True)
async def optimize(
    learner_id: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=50),
):
    """Compatibility alias for the consensus learning-path endpoint."""
    return _call(lambda: learning.recommendations(learner_id, limit))
