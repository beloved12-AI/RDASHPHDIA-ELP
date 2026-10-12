import json
import os
import sqlite3
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.api.schemas import CourseCreate, LearnerCreate, LearningEvent


class NotFoundError(LookupError):
    """Raised when an API request refers to an unknown learner or course."""


class ConflictError(ValueError):
    """Raised when a resource or event identifier conflicts with stored data."""


class LearningService:
    """SQLite-backed ELP model; JSON payloads preserve the existing API contract."""

    def __init__(self, database_path: str | None = None):
        configured_path = database_path or os.getenv(
            "LEARNING_DATABASE_PATH", "data/rdashphdia_elp.db"
        )
        self.database_path = configured_path
        if configured_path != ":memory:":
            Path(configured_path).expanduser().resolve().parent.mkdir(
                parents=True, exist_ok=True
            )
        self.learners: Dict[str, Dict[str, Any]] = {}
        self.courses: Dict[str, Dict[str, Any]] = {}
        self.events: Dict[str, Dict[str, Any]] = {}
        self._initialize_database()
        self._load_state()

    def _connect(self):
        return sqlite3.connect(self.database_path, timeout=10)

    def _initialize_database(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS learners "
                "(resource_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS courses "
                "(resource_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS events "
                "(resource_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )

    def _load_state(self) -> None:
        with closing(self._connect()) as connection, connection:
            for resource_id, payload in connection.execute(
                "SELECT resource_id, payload FROM learners"
            ):
                self.learners[resource_id] = json.loads(payload)
            for resource_id, payload in connection.execute(
                "SELECT resource_id, payload FROM courses"
            ):
                self.courses[resource_id] = json.loads(payload)
            for resource_id, payload in connection.execute(
                "SELECT resource_id, payload FROM events"
            ):
                self.events[resource_id] = json.loads(payload)

    def _persist(self) -> None:
        """Atomically save the current in-process state to SQLite."""
        with closing(self._connect()) as connection, connection:
            for table, records in (
                ("learners", self.learners),
                ("courses", self.courses),
                ("events", self.events),
            ):
                connection.execute(f"DELETE FROM {table}")
                connection.executemany(
                    f"INSERT INTO {table} (resource_id, payload) VALUES (?, ?)",
                    [
                        (
                            resource_id,
                            json.dumps(record, sort_keys=True, default=str),
                        )
                        for resource_id, record in records.items()
                    ],
                )

    def reset(self) -> None:
        """Clear all records; intended for isolated tests and local development."""
        self.learners.clear()
        self.courses.clear()
        self.events.clear()
        self._persist()

    def create_learner(self, request: LearnerCreate) -> Dict[str, Any]:
        if request.learner_id in self.learners:
            raise ConflictError("learner_id already exists")

        learner = request.dict()
        learner["completed_courses"] = []
        self.learners[request.learner_id] = learner
        self._persist()
        return self.get_learner(request.learner_id)

    def get_learner(self, learner_id: str) -> Dict[str, Any]:
        learner = self.learners.get(learner_id)
        if learner is None:
            raise NotFoundError("learner not found")
        return deepcopy(learner)

    def create_course(self, request: CourseCreate) -> Dict[str, Any]:
        if request.course_id in self.courses:
            raise ConflictError("course_id already exists")

        course = request.dict()
        course["skills"] = sorted(set(course["skills"]))
        course["mandatory_for_roles"] = sorted(set(course["mandatory_for_roles"]))
        self.courses[request.course_id] = course
        self._persist()
        return deepcopy(course)

    def list_courses(self) -> List[Dict[str, Any]]:
        return [deepcopy(self.courses[key]) for key in sorted(self.courses)]

    def record_event(self, request: LearningEvent) -> Dict[str, Any]:
        learner = self._learner(request.learner_id)
        event = request.dict()
        previous = self.events.get(request.event_id)
        if previous is not None:
            if self._comparable_event(previous) == self._comparable_event(event):
                return {
                    "event_id": request.event_id,
                    "status": "accepted",
                    "duplicate": True,
                    "learner_id": request.learner_id,
                }
            raise ConflictError("event_id was already used for a different event")

        if request.event_type == "course_completed":
            course = self._course(request.course_id or "")
            unknown_skills = sorted(set(request.skill_scores) - set(course["skills"]))
            if unknown_skills:
                raise ConflictError(
                    "skill_scores must refer to skills taught by the course: "
                    + ", ".join(unknown_skills)
                )

            if request.course_id not in learner["completed_courses"]:
                learner["completed_courses"].append(request.course_id)
                learner["completed_courses"].sort()
            learner["skills"].update(request.skill_scores)
        else:
            learner["skills"][request.skill_id or ""] = request.score

        self.events[request.event_id] = event
        self._persist()
        return {
            "event_id": request.event_id,
            "status": "accepted",
            "duplicate": False,
            "learner_id": request.learner_id,
        }

    def skill_gaps(self, learner_id: str) -> Dict[str, Any]:
        learner = self._learner(learner_id)
        gaps = []
        for skill_id, target in sorted(learner["required_skills"].items()):
            current = learner["skills"].get(skill_id, 0.0)
            gap = max(target - current, 0.0)
            gaps.append(
                {
                    "skill_id": skill_id,
                    "current": round(current, 4),
                    "target": round(target, 4),
                    "gap": round(gap, 4),
                    "status": "gap" if gap > 0 else "met",
                }
            )
        return {"learner_id": learner_id, "gaps": gaps}

    def recommendations(self, learner_id: str, limit: int = 5) -> Dict[str, Any]:
        learner = self._learner(learner_id)
        gaps = self.skill_gaps(learner_id)["gaps"]
        open_gaps = {item["skill_id"]: item for item in gaps if item["gap"] > 0}
        field_priority = {
            item["skill_id"]: item["priority"] for item in self.skill_field()["skills"]
        }

        candidates = []
        for course in self.courses.values():
            if course["course_id"] in learner["completed_courses"]:
                continue

            required_by_role = {
                role.casefold() for role in course["mandatory_for_roles"]
            }
            mandatory = course["mandatory_for_all"] or learner["role"].casefold() in required_by_role
            relevant_gaps = [
                open_gaps[skill_id]
                for skill_id in course["skills"]
                if skill_id in open_gaps
            ]
            if not mandatory and not relevant_gaps:
                continue

            relative_gaps = [
                min(item["gap"] / item["target"], 1.0)
                for item in relevant_gaps
                if item["target"] > 0
            ]
            personal_score = self._mean(relative_gaps)
            population_score = self._mean(
                [field_priority.get(skill_id, 0.0) for skill_id in course["skills"]]
            )

            rules_score = 1.0 if mandatory else personal_score
            adaptive_score = (
                1.0
                if mandatory
                else (0.7 * personal_score) + (0.3 * population_score)
            )
            candidates.append(
                {
                    "course_id": course["course_id"],
                    "title": course["title"],
                    "mandatory": mandatory,
                    "skill_ids": [item["skill_id"] for item in relevant_gaps],
                    "rules_score": round(rules_score, 4),
                    "adaptive_score": round(adaptive_score, 4),
                    "consensus_score": round((rules_score + adaptive_score) / 2, 4),
                }
            )

        rules_ranked = sorted(
            candidates, key=lambda item: (-item["rules_score"], item["course_id"])
        )
        adaptive_ranked = sorted(
            candidates, key=lambda item: (-item["adaptive_score"], item["course_id"])
        )
        consensus_ranked = sorted(
            candidates, key=lambda item: (-item["consensus_score"], item["course_id"])
        )

        rules_top = rules_ranked[0]["course_id"] if rules_ranked else None
        adaptive_top = adaptive_ranked[0]["course_id"] if adaptive_ranked else None
        agreement = rules_top == adaptive_top if rules_top is not None else False
        selected = consensus_ranked[0]["course_id"] if consensus_ranked else None

        return {
            "learner_id": learner_id,
            "engines": {
                "rule_based_top_course": rules_top,
                "adaptive_top_course": adaptive_top,
            },
            "consensus": {
                "selected_course": selected,
                "engines_agree": agreement,
                "manager_review_recommended": bool(candidates) and not agreement,
            },
            "recommendations": consensus_ranked[:limit],
        }

    def compliance(self, learner_id: str) -> Dict[str, Any]:
        learner = self._learner(learner_id)
        role = learner["role"].casefold()
        mandatory = [
            course
            for course in self.courses.values()
            if course["mandatory_for_all"]
            or role in {item.casefold() for item in course["mandatory_for_roles"]}
        ]
        completed = [
            course["course_id"]
            for course in mandatory
            if course["course_id"] in learner["completed_courses"]
        ]
        outstanding = [
            course["course_id"]
            for course in mandatory
            if course["course_id"] not in learner["completed_courses"]
        ]
        total = len(mandatory)
        return {
            "learner_id": learner_id,
            "completed": sorted(completed),
            "outstanding": sorted(outstanding),
            "completion_rate": round(len(completed) / total, 4) if total else 1.0,
        }

    def skill_field(self) -> Dict[str, Any]:
        aggregate: Dict[str, List[Tuple[float, bool]]] = {}
        for learner in self.learners.values():
            for skill_id, target in learner["required_skills"].items():
                gap = max(target - learner["skills"].get(skill_id, 0.0), 0.0)
                aggregate.setdefault(skill_id, []).append((gap, gap > 0))

        skills = []
        for skill_id, observations in aggregate.items():
            mean_gap = self._mean([item[0] for item in observations])
            struggle_rate = self._mean([1.0 if item[1] else 0.0 for item in observations])
            priority = (0.6 * mean_gap) + (0.4 * struggle_rate)
            skills.append(
                {
                    "skill_id": skill_id,
                    "learners_in_scope": len(observations),
                    "mean_gap": round(mean_gap, 4),
                    "struggle_rate": round(struggle_rate, 4),
                    "priority": round(priority, 4),
                }
            )

        skills.sort(key=lambda item: (-item["priority"], item["skill_id"]))
        return {"learner_count": len(self.learners), "skills": skills}

    def _learner(self, learner_id: str) -> Dict[str, Any]:
        learner = self.learners.get(learner_id)
        if learner is None:
            raise NotFoundError("learner not found")
        return learner

    def _course(self, course_id: str) -> Dict[str, Any]:
        course = self.courses.get(course_id)
        if course is None:
            raise NotFoundError("course not found")
        return course

    @staticmethod
    def _comparable_event(event: Dict[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in event.items() if key != "occurred_at"}

    @staticmethod
    def _mean(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0
