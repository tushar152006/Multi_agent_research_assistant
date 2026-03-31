from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class QueryType(str, Enum):
    SIMPLE_SEARCH = "simple_search"
    DEEP_ANALYSIS = "deep_analysis"
    CRITICAL_REVIEW = "critical_review"
    STARTUP_IDEA = "startup_idea"


class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    max_results: int = Field(default=5, ge=1, le=20)
    query_type: QueryType = QueryType.SIMPLE_SEARCH


class PaperSummary(BaseModel):
    title: str
    authors: list[str]
    source: str
    external_id: str
    abstract: str
    relevance_score: int = Field(ge=0, le=100)


class ReaderRequest(BaseModel):
    title: str
    source: str = "unknown"
    content: str = Field(min_length=20)


class MethodologySummary(BaseModel):
    approach: str
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)


class ResultsSummary(BaseModel):
    primary_findings: list[str] = Field(default_factory=list)
    metrics: dict[str, str] = Field(default_factory=dict)


class ReaderResponse(BaseModel):
    title: str
    problem: str
    methodology: MethodologySummary
    results: ResultsSummary
    limitations: list[str] = Field(default_factory=list)
    future_work: list[str] = Field(default_factory=list)
    extracted_sections: dict[str, str] = Field(default_factory=dict)


class AnalystRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    papers: list[ReaderResponse] = Field(min_length=1)


class InnovationSummary(BaseModel):
    paper_title: str
    innovation: str
    impact: str


class ConflictSummary(BaseModel):
    topic: str
    description: str
    papers: list[str] = Field(default_factory=list)


class AnalystResponse(BaseModel):
    query: str
    themes: list[str] = Field(default_factory=list)
    innovations: list[InnovationSummary] = Field(default_factory=list)
    consensus: list[str] = Field(default_factory=list)
    conflicts: list[ConflictSummary] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    practical_applications: list[str] = Field(default_factory=list)


class CritiqueItem(BaseModel):
    category: str
    issue: str
    severity: str
    evidence: str
    impact: str


class CriticRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    analysis: AnalystResponse


class CriticResponse(BaseModel):
    query: str
    critiques: list[CritiqueItem] = Field(default_factory=list)
    overall_confidence: float = Field(ge=0.0, le=1.0)
    review_mode: str = "heuristic"
    llm_summary: str | None = None


class ArchitecturePlan(BaseModel):
    summary: str
    components: list[str] = Field(default_factory=list)
    data_flow: list[str] = Field(default_factory=list)


class DataRequirements(BaseModel):
    datasets: list[str] = Field(default_factory=list)
    collection_strategy: list[str] = Field(default_factory=list)
    privacy_considerations: list[str] = Field(default_factory=list)


class RoadmapPhase(BaseModel):
    name: str
    duration: str
    goals: list[str] = Field(default_factory=list)


class ChallengeMitigation(BaseModel):
    challenge: str
    mitigation: str


class BuilderRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    analysis: AnalystResponse
    critique: CriticResponse


class BuilderResponse(BaseModel):
    query: str
    project_idea: str
    value_proposition: str
    architecture: ArchitecturePlan
    data_requirements: DataRequirements
    mvp_roadmap: list[RoadmapPhase] = Field(default_factory=list)
    challenges: list[ChallengeMitigation] = Field(default_factory=list)


class AgentExecution(BaseModel):
    agent_name: str
    status: str
    detail: str


class ResearchResponse(BaseModel):
    query: str
    query_type: QueryType
    summary: str
    papers: list[PaperSummary]
    reader_outputs: list[ReaderResponse] = Field(default_factory=list)
    analysis: AnalystResponse | None = None
    critique: CriticResponse | None = None
    implementation_plan: BuilderResponse | None = None
    session_id: str | None = None
    execution_trace: list[AgentExecution]
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class SessionSummary(BaseModel):
    session_id: str
    query: str
    query_type: QueryType
    generated_at: datetime


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary] = Field(default_factory=list)
