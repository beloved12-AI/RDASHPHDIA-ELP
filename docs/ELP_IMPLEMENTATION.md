# ELP implementation mapping

This prototype implements the enterprise-learning MVP described in the supplied RDASHPHDIA proposal. It uses the proposal as design context; it does not reproduce the proposal's biomedical or nanoparticle workflows.

## Data and event flow

1. A learner profile stores a role, current skill scores, and target scores for that role. Scores range from `0` to `1`.
2. A course lists the skills it covers and can be marked mandatory for everyone or for selected roles.
3. `POST /api/v1/events` records a course completion or skill assessment. Course-completion events can include measured post-course scores for the course's skills.
4. Skill gaps and the shared skill-priority field are recomputed from the current profiles. The field raises priority when a skill has a larger average gap and more learners below target.
5. Two recommendation components score eligible courses: a rules-based engine uses the learner's own gaps, while an adaptive engine also weighs the shared skill field. Mandatory courses receive priority in both.
6. The service averages the two scores. If the engines select different top courses, the response recommends manager review while still returning the weighted ranking.
7. The compliance component compares required courses with the learner's completion record.

## Current endpoints

- `POST /api/v1/learners` and `GET /api/v1/learners/{learner_id}` manage learner profiles.
- `POST /api/v1/courses` and `GET /api/v1/courses` manage the course catalogue.
- `POST /api/v1/events` ingests completion and assessment events.
- `GET /api/v1/learners/{learner_id}/skill-gaps` returns current and target scores.
- `GET /api/v1/learners/{learner_id}/recommendations` returns both engine leaders, consensus status, and ranked courses.
- `GET /api/v1/learners/{learner_id}/compliance` returns completed and outstanding mandatory courses.
- `GET /api/v1/skills/field` returns population-level skill gaps and priorities.

## Deliberate limits

The agents are logical components in one process, not separately deployed distributed agents. State is in-memory and is neither durable nor shared across replicas. The adaptive engine is a deterministic heuristic; it does not call an AI provider or learn a policy. The service has no authentication or external integrations. These limits keep the scaffold runnable while making the next implementation steps explicit: persistent storage, access controls, integration contracts, event delivery, and evaluated recommendation models.

The service is a software learning-platform prototype. It does not implement biological particles, drug delivery, gene editing, diagnostic workflows, or medical decision-making.
