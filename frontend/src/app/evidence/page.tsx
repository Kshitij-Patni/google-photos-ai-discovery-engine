'use client';

import { useEffect, useState, useCallback } from 'react';
import { fetchEvidence } from '@/lib/api';
import type { PaginatedEvidence, EvidenceRecord } from '@/lib/types';
import { SOURCE_CONFIG } from '@/lib/sourceIcons';

const SOURCES = ['play_store', 'app_store', 'youtube', 'support_forums'];
const ARCHETYPES = [
  'ALBUM_FRAGMENTATION', 'VOLUME_OVERWHELM', 'KEYWORD_MISMATCH', 'TEMPORAL_DECAY',
  'PEOPLE_WITHOUT_NAMES', 'SPATIAL_AMBIGUITY', 'VISUAL_MEMORY_ONLY', 'CONTEXT_WITHOUT_CONTENT',
];
const FRUSTRATION_LEVELS = [
  { value: 'low', label: 'Low', color: '#34a853' },
  { value: 'medium', label: 'Medium', color: '#fbbc04' },
  { value: 'high', label: 'High', color: '#ea4335' },
  { value: 'extreme', label: 'Extreme', color: '#d93025' },
];



export default function EvidencePage() {
  const [evidence, setEvidence] = useState<PaginatedEvidence | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    source: '' as string,
    archetype: '' as string,
    frustration_level: '' as string,
    sort_by: 'newest' as string,
  });

  const loadEvidence = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchEvidence({
        page,
        size: 20,
        source: filters.source || undefined,
        archetype: filters.archetype || undefined,
        frustration_level: filters.frustration_level || undefined,
        sort_by: filters.sort_by || undefined,
      });
      setEvidence(data);
    } catch (err) {
      console.error('Failed to load evidence:', err);
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => {
    loadEvidence();
  }, [loadEvidence]);

  function resetFilters() {
    setFilters({ source: '', archetype: '', frustration_level: '', sort_by: 'newest' });
    setPage(1);
  }

  return (
    <div className="evidence-layout" style={{ display: 'flex', gap: 0 }}>
      {/* Filter Panel */}
      <div className="filter-panel" style={{ minHeight: 'calc(100vh - var(--topbar-height) - var(--space-xl) * 2)' }}>
        {/* Source */}
        <div className="filter-panel__section">
          <div className="filter-panel__title">Source</div>
          {SOURCES.map((source) => {
            const cfg = SOURCE_CONFIG[source];
            return (
              <label
                key={source}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-sm)',
                  padding: '4px 0',
                  fontSize: '0.875rem',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="radio"
                  name="source"
                  checked={filters.source === source}
                  onChange={() => {
                    setFilters((f) => ({ ...f, source: f.source === source ? '' : source }));
                    setPage(1);
                  }}
                />
                {cfg && <cfg.Icon size={14} />}
                {cfg?.label || source}
              </label>
            );
          })}
        </div>

        {/* Archetype */}
        <div className="filter-panel__section">
          <div className="filter-panel__title">Archetype</div>
          {ARCHETYPES.map((archetype) => (
            <label
              key={archetype}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-sm)',
                padding: '4px 0',
                fontSize: '0.8125rem',
                cursor: 'pointer',
              }}
            >
              <input
                type="radio"
                name="archetype"
                checked={filters.archetype === archetype}
                onChange={() => {
                  setFilters((f) => ({ ...f, archetype: f.archetype === archetype ? '' : archetype }));
                  setPage(1);
                }}
              />
              {archetype.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </label>
          ))}
        </div>

        {/* Frustration Level */}
        <div className="filter-panel__section">
          <div className="filter-panel__title">Frustration Level</div>
          {FRUSTRATION_LEVELS.map((level) => (
            <label
              key={level.value}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-sm)',
                padding: '4px 0',
                fontSize: '0.875rem',
                cursor: 'pointer',
              }}
            >
              <input
                type="radio"
                name="frustration"
                checked={filters.frustration_level === level.value}
                onChange={() => {
                  setFilters((f) => ({
                    ...f,
                    frustration_level: f.frustration_level === level.value ? '' : level.value,
                  }));
                  setPage(1);
                }}
              />
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  backgroundColor: level.color,
                  display: 'inline-block',
                }}
              />
              {level.label}
            </label>
          ))}
        </div>

        {/* Reset */}
        <button
          onClick={resetFilters}
          style={{
            width: '100%',
            padding: 'var(--space-sm) var(--space-md)',
            borderRadius: 'var(--radius-full)',
            border: '1px solid var(--md-outline)',
            background: 'var(--md-surface)',
            fontFamily: 'var(--font-body)',
            fontSize: '0.875rem',
            cursor: 'pointer',
            color: 'var(--md-primary)',
            fontWeight: 500,
          }}
        >
          Reset Filters
        </button>
      </div>

      {/* Evidence Feed */}
      <div className="evidence-feed" style={{ flex: 1, padding: '0 var(--space-lg)' }}>
        {/* Header */}
        <div
          className="evidence-header-actions"
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 'var(--space-lg)',
          }}
        >
          <span style={{ fontSize: '0.875rem', color: 'var(--md-on-surface-variant)' }}>
            {evidence
              ? `Showing ${evidence.items.length} of ${evidence.total.toLocaleString()} results`
              : 'Loading...'}
          </span>
          <select
            value={filters.sort_by}
            onChange={(e) => {
              setFilters((f) => ({ ...f, sort_by: e.target.value }));
              setPage(1);
            }}
            style={{
              padding: 'var(--space-sm) var(--space-md)',
              borderRadius: 'var(--radius-full)',
              border: '1px solid var(--md-outline)',
              background: 'var(--md-surface)',
              fontFamily: 'var(--font-body)',
              fontSize: '0.8125rem',
            }}
          >
            <option value="newest">Newest</option>
            <option value="most_engaged">Most Engaged</option>
            <option value="highest_frustration">Highest Frustration</option>
          </select>
        </div>

        {/* Evidence Cards */}
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="evidence-card">
                <div className="skeleton" style={{ width: '95%', height: 16, marginBottom: 8 }} />
                <div className="skeleton" style={{ width: '80%', height: 16, marginBottom: 8 }} />
                <div className="skeleton" style={{ width: '40%', height: 14 }} />
              </div>
            ))}
          </div>
        ) : evidence && evidence.items.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            {evidence.items.map((item: EvidenceRecord) => (
              <div key={item.id} className="evidence-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div className="evidence-card__quote" style={{ flex: 1 }}>
                    &ldquo;{item.cleaned_text || item.raw_text}&rdquo;
                  </div>
                  {(() => {
                    const cfg = SOURCE_CONFIG[item.source];
                    return cfg ? (
                      <span className={`source-badge ${cfg.badgeClass}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                        <cfg.Icon size={12} />
                        {cfg.label}
                      </span>
                    ) : (
                      <span className="source-badge">{item.source}</span>
                    );
                  })()}
                </div>
                <div className="evidence-card__meta">
                  {item.archetypes.map((arch) => (
                    <span key={arch} className="badge badge--primary" style={{ fontSize: '0.6875rem' }}>
                      {arch.replace(/_/g, ' ')}
                    </span>
                  ))}
                  <span
                    className={`badge ${item.frustration_level === 'high' || item.frustration_level === 'extreme'
                        ? 'badge--error'
                        : item.frustration_level === 'medium'
                          ? 'badge--warning'
                          : 'badge--neutral'
                      }`}
                  >
                    {item.frustration_level === 'high' || item.frustration_level === 'extreme' ? '😤' : ''} {item.frustration_level}
                  </span>
                  <span className="badge badge--neutral">{item.date}</span>
                  <span className="badge badge--neutral">👍 {item.engagement_score}</span>
                </div>
              </div>
            ))}

            {/* Pagination */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                gap: 'var(--space-sm)',
                padding: 'var(--space-lg)',
              }}
            >
              <button
                className="chip"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
              >
                ← Previous
              </button>
              <span className="badge badge--neutral" style={{ fontSize: '0.875rem', padding: '6px 16px' }}>
                Page {page}
              </span>
              <button
                className="chip"
                onClick={() => setPage((p) => p + 1)}
                disabled={evidence.items.length < 20}
              >
                Next →
              </button>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--md-on-surface-variant)' }}>
            <p>No evidence records found. Try adjusting your filters or wire the API to load real data.</p>
          </div>
        )}
      </div>
    </div>
  );
}
