from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ArchetypeSummary(BaseModel):
    id: str
    name: str
    frequency_pct: float
    severity: str
    record_count: int
    top_categories: List[str]
    opportunity_score: float = 0.0

class Scorecard(BaseModel):
    score: float
    frequency: float
    severity: float
    feasibility: float

class ArchetypeDetail(BaseModel):
    id: str
    name: str
    frequency_pct: float
    severity: str
    record_count: int
    top_categories: List[str]
    description: str
    evidence_quotes: List[str]
    scorecard: Optional[Scorecard] = None

class ThemeCluster(BaseModel):
    id: int
    label: str
    description: str
    record_count: int

class DashboardStats(BaseModel):
    total_records: int
    relevant_records: int
    sources_covered: int
    archetypes_identified: int

class QueryRequest(BaseModel):
    question: str
    filters: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float

class EvidenceRecord(BaseModel):
    id: str
    source: str
    raw_text: str
    cleaned_text: str
    frustration_level: str
    archetypes: List[str]
    photo_category: str
    date: str
    engagement_score: int

class PaginatedEvidence(BaseModel):
    items: List[EvidenceRecord]
    total: int
    page: int
    size: int

class MemoryCueMatrix(BaseModel):
    categories: List[str]
    cue_types: List[str]
    matrix: List[List[int]]

class BehaviorPatterns(BaseModel):
    strategies: List[str]
    outcomes: List[str]
    flow_data: List[Dict[str, Any]]

class ChartData(BaseModel):
    data: List[Dict[str, Any]]
    layout: Dict[str, Any]
