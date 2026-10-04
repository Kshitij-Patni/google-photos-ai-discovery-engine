import type {
  DashboardStats,
  ArchetypeSummary,
  ArchetypeDetail,
  ThemeCluster,
  QueryResponse,
  PaginatedEvidence,
  MemoryCueMatrix,
  BehaviorPatterns,
  ChartData,
} from './types';

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Dashboard
export async function fetchStats(): Promise<DashboardStats> {
  return fetchJSON<DashboardStats>(`${API_BASE}/api/v1/stats`);
}

// Archetypes
export async function fetchArchetypes(): Promise<ArchetypeSummary[]> {
  return fetchJSON<ArchetypeSummary[]>(`${API_BASE}/api/v1/archetypes`);
}

export async function fetchArchetypeDetail(id: string): Promise<ArchetypeDetail> {
  return fetchJSON<ArchetypeDetail>(`${API_BASE}/api/v1/archetypes/${id}`);
}

// Themes
export async function fetchThemes(): Promise<ThemeCluster[]> {
  return fetchJSON<ThemeCluster[]>(`${API_BASE}/api/v1/themes`);
}

// RAG Q&A
export async function queryRAG(
  question: string,
  filters?: Record<string, any>
): Promise<QueryResponse> {
  return fetchJSON<QueryResponse>(`${API_BASE}/api/v1/query`, {
    method: 'POST',
    body: JSON.stringify({ question, filters }),
  });
}

// Evidence
export async function fetchEvidence(params?: {
  page?: number;
  size?: number;
  source?: string;
  archetype?: string;
  frustration_level?: string;
  sort_by?: string;
}): Promise<PaginatedEvidence> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.set(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return fetchJSON<PaginatedEvidence>(
    `${API_BASE}/api/v1/evidence${query ? `?${query}` : ''}`
  );
}

// Memory Cues
export async function fetchMemoryCues(mode: 'remembered' | 'forgotten' = 'remembered'): Promise<MemoryCueMatrix> {
  return fetchJSON<MemoryCueMatrix>(`${API_BASE}/api/v1/memory-cues?mode=${mode}`);
}

// Behaviors
export async function fetchBehaviors(): Promise<BehaviorPatterns> {
  return fetchJSON<BehaviorPatterns>(`${API_BASE}/api/v1/behaviors`);
}

// Charts
export async function fetchChart(chartName: string): Promise<ChartData> {
  return fetchJSON<ChartData>(`${API_BASE}/api/v1/charts/${chartName}`);
}
