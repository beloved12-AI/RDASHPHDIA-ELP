# RDASHPHDIA implementation mapping

This repository implements an enterprise-learning MVP from the supplied proposal and a separate synthetic-data biomedical research simulator. The biomedical module is a software demonstration of redundancy and cross-checking concepts; it does not implement biological materials or clinical workflows.

## ELP data and event flow

1. A learner profile stores a role, current skill scores, and target scores for that role. Scores range from 0 to 1.
2. A course lists the skills it covers and can be mandatory for everyone or selected roles.
3. `POST /api/v1/events` records course completion or a skill assessment. Course completions may include post-course scores for covered skills.
4. Skill gaps and the shared skill-priority field are recomputed from current profiles.
5. Rules-based and adaptive recommenders score eligible courses; the adaptive score also weighs the shared skill field.
6. A weighted consensus returns ranked courses and flags disagreement for manager review.
7. Compliance compares required courses with the learner's completion record.

## API endpoints

- `POST /api/v1/learners` and `GET /api/v1/learners/{learner_id}` manage learner profiles.
- `POST /api/v1/courses` and `GET /api/v1/courses` manage the course catalogue.
- `POST /api/v1/events` records completion and assessment events.
- `GET /api/v1/learners/{learner_id}/skill-gaps` returns current and target scores.
- `GET /api/v1/learners/{learner_id}/recommendations` returns rankings and consensus status.
- `GET /api/v1/learners/{learner_id}/compliance` returns completed and outstanding mandatory courses.
- `GET /api/v1/skills/field` summarizes population-level gaps and priorities.
- `GET /api/v1/biomedical/scenarios` lists synthetic channel templates.
- `POST /api/v1/biomedical/simulate` calculates synthetic channel coverage and readout consistency.

## Biomedical simulator

| Scenario | Channels represented |
| --- | --- |
| Targeted cancer-therapy delivery | Folate and antibody targeting; pH and enzyme release cues; therapeutic and imaging payloads |
| Vaccine platform | Multiple antigen and adjuvant-pathway channels |
| Antimicrobial mechanisms | Membrane disruption and reactive oxygen species |
| Biosensor/diagnostics | Optical and electrochemical readouts |

Each channel accepts an optional numeric synthetic score from 0 to 1. Callers can mark channels failed to inspect the remaining group coverage. Biosensor outputs summarize whether two supplied readouts agree around a caller-provided threshold and may suggest manual review for missing or disagreeing readouts. The simulator returns no diagnosis or treatment recommendation, accepts no patient records, and does not persist biomedical inputs.

## Deliberate limits

The ELP agents are logical components in one process, not separately deployed services. ELP state is in-memory and neither durable nor shared across replicas. The adaptive engine is a deterministic heuristic, not a trained model. The service has no authentication or external integrations.

The biomedical simulator uses invented numeric inputs only. Its outputs are not biological measurements, evidence of safety or efficacy, clinical evidence, or medical advice. Validate any subsystem in controlled research settings before biological use; do not use this API to guide patient care or real-world biological work.
