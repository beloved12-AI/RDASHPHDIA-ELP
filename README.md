# RDASHPHDIA-ELP Learning Intelligence Service

A FastAPI prototype that turns the Enterprise Learning Platform (ELP) portion of the RDASHPHDIA proposal into an executable learning-path service. It models learner skills, course requirements, learning events, compliance, and a group-level skill-priority field.

The proposal's “hybrid particles” are represented here as changing skill weights in a learner graph. Separate rule-based and adaptive recommenders provide overlapping recommendations; a weighted consensus selects a learning path and flags disagreements for manager review.

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

The interactive API reference is available at `http://localhost:8080/docs`. To run the container instead, use `make build` followed by `make run`.

## API overview

All application routes are under `/api/v1`.

| Route | Purpose |
| --- | --- |
| `POST /learners` | Register a learner with current and role-required skills |
| `GET /learners/{learner_id}` | Read a learner's skill profile and completed courses |
| `POST /courses` | Add a course and the skills or roles it covers |
| `GET /courses` | List the course catalogue |
| `POST /events` | Record course completion or a skill assessment |
| `GET /learners/{learner_id}/skill-gaps` | Compare current skills with role targets |
| `GET /learners/{learner_id}/recommendations` | Compare rule-based and adaptive rankings, then return a consensus path |
| `GET /learners/{learner_id}/compliance` | List required training that is complete or outstanding |
| `GET /skills/field` | Summarize skill gaps and struggle rates across registered learners |
| `GET /health` | Check service availability |

`GET /api/v1/optimize?learner_id=...` remains as a deprecated alias for recommendations.

## Example flow

Register a learner and a course:

```bash
curl -X POST http://localhost:8080/api/v1/learners \
  -H "Content-Type: application/json" \
  -d '{"learner_id":"learner-1","role":"analyst","skills":{"data-analysis":0.25},"required_skills":{"data-analysis":0.8}}'

curl -X POST http://localhost:8080/api/v1/courses \
  -H "Content-Type: application/json" \
  -d '{"course_id":"analysis-foundations","title":"Analysis Foundations","skills":["data-analysis"],"mandatory_for_all":false,"mandatory_for_roles":[]}'
```

Review the skill gap and recommendation, then record a completion event with the observed post-course skill score:

```bash
curl http://localhost:8080/api/v1/learners/learner-1/recommendations

curl -X POST http://localhost:8080/api/v1/events \
  -H "Content-Type: application/json" \
  -d '{"event_id":"event-1","learner_id":"learner-1","event_type":"course_completed","course_id":"analysis-foundations","skill_scores":{"data-analysis":0.7}}'
```

Event IDs are idempotent: a repeated event with the same ID and payload is acknowledged without applying its updates twice. Reusing an ID for a different event returns `409 Conflict`.

## Prototype boundaries

- Learners, courses, and events live in process memory and reset on restart. Keep the service to one replica until a shared persistent store is added.
- The “agents” are independent decision components in one API process. There is no external LLM, message broker, HRIS, or LMS integration.
- This prototype has no authentication, authorization, or encryption layer. Use synthetic data only; do not send real employee or other sensitive records to it.
- The adaptive scores are transparent heuristics for demonstrating the proposal, not trained model outputs or evidence of improved learning outcomes.

See [`docs/ELP_IMPLEMENTATION.md`](docs/ELP_IMPLEMENTATION.md) for the architecture mapping and [`docs/RDASHPHDIA.pdf`](docs/RDASHPHDIA.pdf) for the supplied proposal.


## Biomedical research simulator

The supplied proposal's biomedical concepts are exposed as a synthetic-data research simulator. The endpoints are:

- `GET /api/v1/biomedical/scenarios` lists the four scenario templates and their channel names.
- `POST /api/v1/biomedical/simulate` compares channel coverage and shows how a simulated channel failure affects coverage.

The scenarios cover redundant targeting and release cues with therapeutic or imaging payload channels; antigen and adjuvant coverage; membrane disruption and reactive oxygen channels; and agreement between optical and electrochemical readouts. Submit synthetic numeric scores from 0 to 1 only. Unknown channels and out-of-range scores are rejected. The biosensor scenario reports readout agreement and can suggest manual review when a readout is missing or disagrees; it never returns a diagnosis.

Example synthetic request:

```bash
curl -X POST http://localhost:8080/api/v1/biomedical/simulate \
  -H "Content-Type: application/json" \
  -d '{"scenario":"biosensor_diagnostics","signals":{"optical_readout":0.8,"electrochemical_readout":0.3},"threshold":0.5}'
```

These outputs are software demonstrations, not validated biological measurements, safety or efficacy estimates, clinical evidence, or treatment advice. The module does not accept patient records and does not persist simulator inputs. Keep all examples synthetic and conduct controlled validation before any biological use.
