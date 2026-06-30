"""Pydantic models — the shared contract across the whole backend.

These shapes are mirrored in the frontend (`frontend/lib/types.ts`). Keep them
in sync. The eligibility verdict shape is the strict JSON the spec mandates and
is produced identically by both the Claude path and the local rule engine, so
the frontend never knows which one ran.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Verdict = Literal["likely_eligible", "possibly_eligible", "likely_ineligible"]


class PatientProfile(BaseModel):
    age: Optional[int] = Field(default=None, ge=0, le=120)
    sex: Optional[str] = None  # "male" | "female" | "all" / free text
    condition: str
    location: Optional[str] = None
    priorTreatments: list[str] = Field(default_factory=list)
    notes: Optional[str] = None

    def to_query_text(self) -> str:
        """Flatten the profile into one search string for embedding/rerank."""
        parts = [f"Condition: {self.condition}"]
        if self.age is not None:
            parts.append(f"Age: {self.age}")
        if self.sex:
            parts.append(f"Sex: {self.sex}")
        if self.location:
            parts.append(f"Location: {self.location}")
        if self.priorTreatments:
            parts.append("Prior treatments: " + ", ".join(self.priorTreatments))
        if self.notes:
            parts.append(f"Notes: {self.notes}")
        return ". ".join(parts)


class TrialLocation(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    facility: Optional[str] = None


class TrialContact(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class Trial(BaseModel):
    """A flattened, clean ClinicalTrials.gov study record."""

    nctId: str
    briefTitle: str = ""
    conditions: list[str] = Field(default_factory=list)
    phase: Optional[str] = None
    status: Optional[str] = None
    eligibilityCriteria: str = ""
    minAge: Optional[str] = None
    maxAge: Optional[str] = None
    sex: Optional[str] = None
    healthyVolunteers: Optional[bool] = None
    locations: list[TrialLocation] = Field(default_factory=list)
    briefSummary: str = ""
    contacts: list[TrialContact] = Field(default_factory=list)

    def embed_text(self) -> str:
        """One text blob per trial for embedding (title+conditions+elig+summary)."""
        conds = ", ".join(self.conditions) if self.conditions else ""
        return "\n".join(
            [
                f"Title: {self.briefTitle}",
                f"Conditions: {conds}",
                f"Phase: {self.phase or 'N/A'}",
                f"Eligibility: {self.eligibilityCriteria}",
                f"Summary: {self.briefSummary}",
            ]
        ).strip()

    def url(self) -> str:
        return f"https://clinicaltrials.gov/study/{self.nctId}"


class Eligibility(BaseModel):
    verdict: Verdict = "possibly_eligible"
    confidence: float = 0.5
    reasons_for: list[str] = Field(default_factory=list)
    reasons_against: list[str] = Field(default_factory=list)
    plain_language_summary: str = ""


class MatchedTrial(BaseModel):
    """A trial plus its rank/scores and the eligibility verdict — what /results renders."""

    trial: Trial
    retrieval_score: float = 0.0
    rerank_score: float = 0.0
    nearest_location: Optional[TrialLocation] = None
    eligibility: Eligibility = Field(default_factory=Eligibility)
    enrichment: Optional[dict] = None  # Bright Data SERP context (optional)


class EfficiencyComparison(BaseModel):
    always_on_cost_per_day: float = 17.0
    always_on_idle_pct: float = 98.0
    flash_run_cost: float = 0.0
    flash_utilization_pct: float = 0.0
    cheaper_factor: float = 0.0


class ComputeMetrics(BaseModel):
    """The honest numbers behind the dashboard. Counts are real; GPU-sec/cost are est."""

    mode: str = "demo_simulated"  # flash_live | local_cpu | demo_simulated
    trials_total_available: int = 0  # real totalCount from CT.gov
    trials_processed: int = 0  # unique trials embedded this run
    gpu_work_items: int = 0  # ALL vectors computed (embed + query + rerank)
    batch_count: int = 0
    peak_workers: int = 0
    gpu_seconds_est: float = 0.0
    cost_est: float = 0.0
    elapsed_s: float = 0.0
    timeline: list[dict] = Field(default_factory=list)  # [{t, workers}]
    efficiency: EfficiencyComparison = Field(default_factory=EfficiencyComparison)
    telemetry: dict = Field(default_factory=dict)  # live infra facts for dashboard


class MatchResponse(BaseModel):
    results: list[MatchedTrial] = Field(default_factory=list)
    compute_metrics: ComputeMetrics = Field(default_factory=ComputeMetrics)
    searched_count: int = 0
    profile: Optional[PatientProfile] = None
