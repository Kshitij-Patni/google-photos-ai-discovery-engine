'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { fetchArchetypeDetail, fetchThemes } from '@/lib/api';
import type { ArchetypeDetail, ThemeCluster } from '@/lib/types';

export default function ArchetypeDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [archetype, setArchetype] = useState<ArchetypeDetail | null>(null);
  const [themes, setThemes] = useState<ThemeCluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'evidence' | 'statistics' | 'themes'>('evidence');

  useEffect(() => {
    if (id) {
      fetchArchetypeDetail(id)
        .then(setArchetype)
        .catch(console.error)
        .finally(() => setLoading(false));

      fetchThemes()
        .then(setThemes)
        .catch(console.error);
    }
  }, [id]);

  if (loading) {
    return (
      <div>
        <div className="hero">
          <div>
            <div className="skeleton" style={{ width: 300, height: 32, marginBottom: 8 }} />
            <div className="skeleton" style={{ width: 500, height: 16 }} />
          </div>
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className="evidence-card" style={{ marginBottom: 'var(--space-md)' }}>
            <div className="skeleton" style={{ width: '90%', height: 16, marginBottom: 8 }} />
            <div className="skeleton" style={{ width: '70%', height: 14 }} />
          </div>
        ))}
      </div>
    );
  }

  if (!archetype) {
    return (
      <div style={{ textAlign: 'center', padding: 'var(--space-2xl)' }}>
        <h2>Archetype not found</h2>
        <p style={{ color: 'var(--md-on-surface-variant)' }}>The requested archetype could not be loaded.</p>
      </div>
    );
  }

  const displayName = archetype.name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div>
      {/* Hero */}
      <div className="hero">
        <div>
          <h1 className="hero__title">{displayName}</h1>
          <p className="hero__subtitle">{archetype.description}</p>
        </div>
        <div className="hero__stats">
          <span className="badge badge--primary" style={{ fontSize: '0.875rem', padding: '4px 14px' }}>
            {archetype.frequency_pct.toFixed(1)}% frequency
          </span>
          <span
            className={`badge ${archetype.severity === 'HIGH' ? 'badge--error' : 'badge--warning'}`}
            style={{ fontSize: '0.875rem', padding: '4px 14px' }}
          >
            {archetype.severity}
          </span>
          <span className="badge badge--neutral" style={{ fontSize: '0.875rem', padding: '4px 14px' }}>
            {archetype.record_count} records
          </span>
        </div>
      </div>

      {/* Opportunity Scorecard (Always Visible) */}
      {archetype.scorecard && (
        <div style={{ marginBottom: 'var(--space-xl)' }}>
          <h3 style={{ marginBottom: 'var(--space-md)' }}>Opportunity Scorecard</h3>
          <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
            <div className="metric-card" style={{ backgroundColor: 'var(--md-primary-container)', color: 'var(--md-on-primary-container)' }}>
              <div className="metric-card__label">Total Score</div>
              <div className="metric-card__value">{archetype.scorecard.score.toFixed(2)}</div>
            </div>
            <div className="metric-card">
              <div className="metric-card__label">Frequency %</div>
              <div className="metric-card__value">{archetype.scorecard.frequency}</div>
            </div>
            <div className="metric-card">
              <div className="metric-card__label">Severity (1-4)</div>
              <div className="metric-card__value">{archetype.scorecard.severity}</div>
            </div>
            <div className="metric-card">
              <div className="metric-card__label">Feasibility (0-10)</div>
              <div className="metric-card__value">{archetype.scorecard.feasibility}</div>
            </div>
          </div>
          <p style={{ marginTop: 'var(--space-sm)', fontSize: '0.875rem', color: 'var(--md-on-surface-variant)' }}>
            <em>Score (0-10) = (Frequency Index × 0.4) + (Severity Index × 0.4) + (Feasibility × 0.2)</em>
          </p>
        </div>
      )}

      {/* Tabs */}
      <div className="tab-bar">
        <button
          className={`tab ${activeTab === 'evidence' ? 'tab--active' : ''}`}
          onClick={() => setActiveTab('evidence')}
        >
          Evidence
        </button>
        <button
          className={`tab ${activeTab === 'statistics' ? 'tab--active' : ''}`}
          onClick={() => setActiveTab('statistics')}
        >
          Statistics
        </button>
        <button
          className={`tab ${activeTab === 'themes' ? 'tab--active' : ''}`}
          onClick={() => setActiveTab('themes')}
        >
          Related Themes
        </button>
      </div>

      {/* Evidence Tab */}
      {activeTab === 'evidence' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          {archetype.evidence_quotes.length > 0 ? (
            archetype.evidence_quotes.map((quote, idx) => (
              <div key={idx} className="evidence-card">
                <div className="evidence-card__quote">&ldquo;{quote}&rdquo;</div>
                <div className="evidence-card__meta">
                  <span className="badge badge--neutral">Evidence #{idx + 1}</span>
                </div>
              </div>
            ))
          ) : (
            <p style={{ color: 'var(--md-on-surface-variant)', padding: 'var(--space-lg)' }}>
              No evidence quotes available yet. Wire the API to load real data.
            </p>
          )}
        </div>
      )}

      {/* Statistics Tab */}
      {activeTab === 'statistics' && (
        <div>
          <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
            <div className="metric-card">
              <div className="metric-card__label">Record Count</div>
              <div className="metric-card__value">{archetype.record_count}</div>
            </div>
            <div className="metric-card">
              <div className="metric-card__label">Frequency</div>
              <div className="metric-card__value">{archetype.frequency_pct.toFixed(2)}%</div>
            </div>
            <div className="metric-card">
              <div className="metric-card__label">Severity</div>
              <div className="metric-card__value">{archetype.severity}</div>
            </div>
          </div>

          {archetype.top_categories.length > 0 && (
            <div style={{ marginTop: 'var(--space-lg)' }}>
              <h3 style={{ marginBottom: 'var(--space-sm)' }}>Top Photo Categories</h3>
              <div style={{ display: 'flex', gap: 'var(--space-sm)', flexWrap: 'wrap' }}>
                {archetype.top_categories.map((cat) => (
                  <span key={cat} className="chip chip--selected">{cat}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Related Themes Tab */}
      {activeTab === 'themes' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          {themes.length > 0 ? (
            themes.map((theme) => (
              <div key={theme.id} className="evidence-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-xs)' }}>
                  <h4 style={{ margin: 0, color: 'var(--md-primary)' }}>{theme.label}</h4>
                  <span className="badge badge--neutral">{theme.record_count} records</span>
                </div>
                <p style={{ margin: 0, fontSize: '0.9375rem', color: 'var(--md-on-surface-variant)' }}>
                  {theme.description}
                </p>
              </div>
            ))
          ) : (
            <p style={{ color: 'var(--md-on-surface-variant)', padding: 'var(--space-lg)' }}>
              No related themes found.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
