// TypeScript types matching backend Pydantic schemas (src/api/schemas.py)

export interface ArchetypeSummary {
  id: string;
  name: string;
  frequency_pct: number;
  severity: string;
  record_count: number;
  top_categories: string[];
  opportunity_score?: number;
}

export interface Scorecard {
  score: number;
  frequency: number;
  severity: number;
  feasibility: number;
}

export interface ArchetypeDetail {
  id: string;
  name: string;
  frequency_pct: number;
  severity: string;
  record_count: number;
  top_categories: string[];
  description: string;
  evidence_quotes: string[];
  scorecard?: Scorecard;
}

export interface ThemeCluster {
  id: number;
  label: string;
  description: string;
  record_count: number;
}

export interface DashboardStats {
  total_records: number;
  relevant_records: number;
  sources_covered: number;
  archetypes_identified: number;
}

export interface QueryRequest {
  question: string;
  filters?: Record<string, any>;
}

export interface QueryResponse {
  answer: string;
  sources: Record<string, any>[];
  confidence: number;
}

export interface EvidenceRecord {
  id: string;
  source: string;
  raw_text: string;
  cleaned_text: string;
  frustration_level: string;
  archetypes: string[];
  photo_category: string;
  date: string;
  engagement_score: number;
}

export interface PaginatedEvidence {
  items: EvidenceRecord[];
  total: number;
  page: number;
  size: number;
}

export interface MemoryCueMatrix {
  categories: string[];
  cue_types: string[];
  matrix: number[][];
}

export interface BehaviorPatterns {
  strategies: string[];
  outcomes: string[];
  flow_data: Record<string, any>[];
}

export interface ChartData {
  data: Record<string, any>[];
  layout: Record<string, any>;
}
