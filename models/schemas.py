from pydantic import BaseModel, field_validator
from typing import List
from enum import Enum


class Recommendation(str, Enum):
    PASS = "Pass"
    TAKE_MEETING = "Take Meeting"
    FAST_TRACK = "Fast Track"


class StartupBasic(BaseModel):
    name: str
    website_url: str
    founders: str
    founded_year: int
    hq_location: str
    one_line_summary: str
    sector: str

    @field_validator("founded_year")
    @classmethod
    def must_be_recent(cls, v):
        if v < 2022:
            raise ValueError("Startup must be founded in 2022 or later")
        return v

    @field_validator("website_url")
    @classmethod
    def must_look_like_url(cls, v):
        if not v.startswith("http") or "." not in v:
            raise ValueError(f"Invalid URL format: {v}")
        return v


class FounderSignal(BaseModel):
    name: str
    background_summary: str
    has_iit_iim: bool
    has_faang_experience: bool
    has_prior_startup: bool
    has_yc_or_top_accelerator: bool
    pedigree_score: int


class TechAnalysis(BaseModel):
    startup_name: str
    core_product: str
    target_audience: str
    ai_architecture: str
    tech_stack_inference: str
    moat_assessment: str
    red_flags: List[str]
    green_flags: List[str]
    founder_signals: List[FounderSignal]
    competitors: List[str]


class ScorecardCriterion(BaseModel):
    name: str
    weight: float
    score: int
    justification: str


class InvestmentScore(BaseModel):
    startup_name: str
    weighted_total: float
    criteria: List[ScorecardCriterion]
    recommendation: Recommendation
    one_line_verdict: str

    @field_validator("weighted_total")
    @classmethod
    def valid_score_range(cls, v):
        if not 0 <= v <= 10:
            raise ValueError("Score must be between 0 and 10")
        return round(v, 2)


class FullStartupProfile(BaseModel):
    basic: StartupBasic
    tech: TechAnalysis
    score: InvestmentScore