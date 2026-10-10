from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, confloat, root_validator


Score = confloat(ge=0.0, le=1.0)


class LearnerCreate(BaseModel):
    learner_id: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=100)
    skills: Dict[str, Score] = Field(default_factory=dict)
    required_skills: Dict[str, Score] = Field(default_factory=dict)


class CourseCreate(BaseModel):
    course_id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    skills: List[str] = Field(default_factory=list)
    mandatory_for_all: bool = False
    mandatory_for_roles: List[str] = Field(default_factory=list)


class LearningEvent(BaseModel):
    event_id: str = Field(..., min_length=1, max_length=120)
    learner_id: str = Field(..., min_length=1, max_length=100)
    event_type: Literal["course_completed", "skill_assessed"]
    course_id: Optional[str] = None
    skill_id: Optional[str] = None
    score: Optional[Score] = None
    skill_scores: Dict[str, Score] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @root_validator
    def validate_event_payload(cls, values):
        event_type = values.get("event_type")
        course_id = values.get("course_id")
        skill_id = values.get("skill_id")
        score = values.get("score")
        skill_scores = values.get("skill_scores") or {}

        if event_type == "course_completed":
            if not course_id:
                raise ValueError("course_id is required for course_completed events")
            if skill_id is not None or score is not None:
                raise ValueError("use skill_scores, not skill_id or score, for course completions")
        elif event_type == "skill_assessed":
            if not skill_id or score is None:
                raise ValueError("skill_id and score are required for skill_assessed events")
            if course_id is not None or skill_scores:
                raise ValueError("skill_assessed events cannot include course_id or skill_scores")

        return values
