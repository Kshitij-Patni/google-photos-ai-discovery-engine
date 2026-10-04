'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchStats, fetchArchetypes } from '@/lib/api';
import type { DashboardStats, ArchetypeSummary } from '@/lib/types';
import { SOURCE_CONFIG } from '@/lib/sourceIcons';

const ARCHETYPE_COLORS = [
  '#4285f4', '#ea4335', '#fbbc04', '#34a853',
  '#ff6d01', '#46bdc6', '#9334e6', '#e8710a',
];

const ARCHETYPE_DESCRIPTIONS: Record<string, string> = {
  'ALBUM_FRAGMENTATION': 'Photos lost across albums, shared libraries, or archives due to lack of hierarchical folder support',
  'VOLUME_OVERWHELM': 'Too many photos to scroll through manually — users feel paralyzed by their library size',
  'KEYWORD_MISMATCH': "User's search terms don't match how the system indexed the photo content",
  'TEMPORAL_DECAY': "Users remember the event but can't recall when it happened — date-based retrieval fails",
  'PEOPLE_WITHOUT_NAMES': 'Users remember people in photos but faces are not tagged or identified',
  'SPATIAL_AMBIGUITY': "Users remember a place vaguely but can't pinpoint the exact location name",
  'VISUAL_MEMORY_ONLY': 'Users remember what the photo looked like but have no searchable metadata',
  'CONTEXT_WITHOUT_CONTENT': 'Users remember the context surrounding a photo but not the photo itself',
};

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [archetypes, setArchetypes] = useState<ArchetypeSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [statsData, archetypesData] = await Promise.all([
          fetchStats(),
          fetchArchetypes(),
        ]);
        setStats(statsData);
        setArchetypes(archetypesData);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div>
        <div className="metrics-grid">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="metric-card">
              <div className="skeleton" style={{ width: '60%', height: 14, marginBottom: 8 }} />
              <div className="skeleton" style={{ width: '40%', height: 32 }} />
            </div>
          ))}
        </div>
        <div className="archetypes-grid">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="archetype-card">
              <div className="archetype-card__accent skeleton" />
              <div className="archetype-card__body">
                <div className="skeleton" style={{ width: '70%', height: 16, marginBottom: 8 }} />
                <div className="skeleton" style={{ width: '100%', height: 12, marginBottom: 4 }} />
                <div className="skeleton" style={{ width: '80%', height: 12 }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const metrics = stats
    ? [
        { label: 'Total Records Analyzed', value: stats.total_records.toLocaleString() },
        { label: 'Relevant Records', value: stats.relevant_records.toLocaleString() },
        { label: 'Sources Covered', value: stats.sources_covered.toString() },
        { label: 'Archetypes Identified', value: stats.archetypes_identified.toString() },
      ]
    : [];

  return (
    <div>
      {/* Metrics Row */}
      <div className="metrics-grid">
        {metrics.map((metric) => (
          <div key={metric.label} className="metric-card">
            <div className="metric-card__label">{metric.label}</div>
            <div className="metric-card__value">{metric.value}</div>
          </div>
        ))}
      </div>

      {/* Sources Strip */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-xl)',
        padding: 'var(--space-md) var(--space-lg)',
        marginBottom: 'var(--space-lg)',
        background: 'var(--md-surface-container-low)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--md-outline)',
      }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--md-on-surface-variant)', whiteSpace: 'nowrap' }}>
          Data Sources
        </span>
        {Object.entries(SOURCE_CONFIG).map(([key, cfg]) => (
          <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <cfg.Icon size={22} />
            <span style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--md-on-surface)' }}>{cfg.label}</span>
          </div>
        ))}
      </div>

      {/* Archetypes Grid */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 'var(--space-md)' }}>
        <h2>Retrieval Problem Archetypes</h2>
        <div style={{ fontSize: '0.875rem', color: 'var(--md-on-surface-variant)' }}>
          <strong>Opportunity Score</strong> = (Frequency × 0.2) + (Severity × 0.5) + (UX Gap × 0.4) + (Feasibility × 0.2)
        </div>
      </div>
      <div className="archetypes-grid">
        {archetypes.map((archetype, index) => (
          <Link
            key={archetype.id}
            href={`/archetypes/${archetype.id}`}
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            <div className="archetype-card">
              <div
                className="archetype-card__accent"
                style={{ backgroundColor: ARCHETYPE_COLORS[index % ARCHETYPE_COLORS.length] }}
              />
              <div className="archetype-card__body">
                <div className="archetype-card__header">
                  <div className="archetype-card__name">
                    {archetype.name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </div>
                  <span className="archetype-card__badge" style={{ backgroundColor: 'var(--md-primary-container)', color: 'var(--md-on-primary-container)' }}>
                    Score: {archetype.opportunity_score?.toFixed(2) || archetype.frequency_pct.toFixed(1)}
                  </span>
                </div>
                <div className="archetype-card__description">
                  {ARCHETYPE_DESCRIPTIONS[archetype.id] || `${archetype.record_count} records classified under this archetype`}
                </div>
                <div className="archetype-card__stats">
                  <span>{archetype.record_count} records</span>
                  <span>·</span>
                  <span
                    className={`badge ${
                      archetype.severity === 'HIGH'
                        ? 'badge--error'
                        : archetype.severity === 'MEDIUM'
                        ? 'badge--warning'
                        : 'badge--neutral'
                    }`}
                  >
                    {archetype.severity}
                  </span>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Footer */}
      <div className="page-footer">
        Last pipeline run: Sep 20, 2026
      </div>
    </div>
  );
}
