from typing import Dict, List, Literal, Set

from fastapi import APIRouter
from pydantic import BaseModel, Field, confloat, root_validator


router = APIRouter(prefix="/biomedical", tags=["Biomedical research simulator"])

SCENARIOS = {
    "targeted_cancer_therapy": {
        "title": "Redundant targeting, release, and payload channels",
        "description": "Explore synthetic targeting ligands, release cues, and therapeutic or imaging payloads.",
        "groups": {
            "targeting": ["folate_binding", "antibody_binding"],
            "release_cues": ["ph_triggered_release", "enzyme_triggered_release"],
            "payloads": ["therapeutic_payload", "imaging_payload"],
        },
    },
    "vaccine_platform": {
        "title": "Antigen and adjuvant coverage",
        "description": "Explore overlapping antigen and adjuvant pathways with synthetic signals.",
        "groups": {
            "antigens": ["antigen_a", "antigen_b"],
            "adjuvant_pathways": ["adjuvant_pathway_a", "adjuvant_pathway_b"],
        },
    },
    "antimicrobial": {
        "title": "Complementary antimicrobial mechanisms",
        "description": "Explore membrane-disruption and reactive-oxygen channels with synthetic signals.",
        "groups": {"mechanisms": ["membrane_disruption", "reactive_oxygen_species"]},
    },
    "biosensor_diagnostics": {
        "title": "Cross-checked biosensor readouts",
        "description": "Compare optical and electrochemical synthetic readouts without a diagnostic conclusion.",
        "groups": {"readouts": ["optical_readout", "electrochemical_readout"]},
    },
}

RESEARCH_NOTICE = (
    "Research simulation only. Inputs are synthetic channel scores; outputs are not validated "
    "biological measurements, diagnoses, treatment recommendations, or evidence of safety or efficacy. "
    "Do not submit patient or other sensitive health data. Validate subsystems in controlled research "
    "settings before any biological or clinical use."
)


class BiomedicalSimulationRequest(BaseModel):
    scenario: Literal[
        "targeted_cancer_therapy",
        "vaccine_platform",
        "antimicrobial",
        "biosensor_diagnostics",
    ]
    signals: Dict[str, confloat(ge=0.0, le=1.0)] = Field(default_factory=dict)
    failed_channels: List[str] = Field(default_factory=list)
    threshold: confloat(ge=0.0, le=1.0) = 0.5

    @root_validator
    def channels_must_match_scenario(cls, values):
        scenario = values.get("scenario")
        if scenario not in SCENARIOS:
            return values
        known: Set[str] = {
            channel
            for channels in SCENARIOS[scenario]["groups"].values()
            for channel in channels
        }
        supplied = set((values.get("signals") or {}).keys())
        failed = set(values.get("failed_channels") or [])
        unknown = (supplied | failed) - known
        if unknown:
            raise ValueError("unknown channels for scenario: " + ", ".join(sorted(unknown)))
        return values


def _simulate(request: BiomedicalSimulationRequest) -> dict:
    definition = SCENARIOS[request.scenario]
    failed = set(request.failed_channels)
    groups = {}
    channel_results = {}
    redundant_groups = []

    for group, channels in definition["groups"].items():
        active = [name for name in channels if name in request.signals and name not in failed]
        if len(active) > 1:
            redundant_groups.append(group)
        groups[group] = round(max((request.signals[name] for name in active), default=0.0), 4)
        for name in channels:
            channel_results[name] = {
                "state": "failed" if name in failed else "active" if name in request.signals else "not_provided",
                "synthetic_score": request.signals.get(name),
            }

    result = {
        "scenario": request.scenario,
        "research_only": True,
        "channel_results": channel_results,
        "group_coverage": groups,
        "functional_coverage": round(min(groups.values()), 4) if groups else 0.0,
        "redundant_groups": redundant_groups,
        "failed_channels": sorted(failed),
        "notice": RESEARCH_NOTICE,
    }

    if request.scenario == "biosensor_diagnostics":
        readouts = [
            request.signals[name]
            for name in definition["groups"]["readouts"]
            if name in request.signals and name not in failed
        ]
        flags = [score >= request.threshold for score in readouts]
        if len(flags) < 2:
            consistency = "insufficient_readouts"
        elif all(flags):
            consistency = "readouts_agree_above_threshold"
        elif not any(flags):
            consistency = "readouts_agree_below_threshold"
        else:
            consistency = "readouts_disagree"
        result["readout_consistency"] = consistency
        result["manual_review_suggested"] = consistency in {
            "insufficient_readouts", "readouts_disagree"
        }
        result["clinical_conclusion"] = None

    return result


@router.get("/scenarios")
async def list_scenarios():
    return {
        "research_only": True,
        "notice": RESEARCH_NOTICE,
        "scenarios": [
            {
                "scenario": name,
                "title": item["title"],
                "description": item["description"],
                "channel_groups": item["groups"],
            }
            for name, item in SCENARIOS.items()
        ],
    }


@router.post("/simulate")
async def simulate(request: BiomedicalSimulationRequest):
    return _simulate(request)
