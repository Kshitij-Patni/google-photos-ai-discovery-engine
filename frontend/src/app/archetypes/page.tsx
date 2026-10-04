'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchArchetypes } from '@/lib/api';
import type { ArchetypeSummary } from '@/lib/types';

const ARCHETYPE_COLORS = [
  '#4285f4', '#ea4335', '#fbbc04', '#34a853',
  '#ff6d01', '#46bdc6', '#9334e6', '#e8710a',
];

export default function ArchetypesPage() {
  const [archetypes, setArchetypes] = useState<ArchetypeSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchArchetypes()
      .then(setArchetypes)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="hero">
        <div>
          <h1 className="hero__title">Retrieval Problem Archetypes</h1>
          <p className="hero__subtitle">
            Classified patterns of why photo retrieval fails, ranked by frequency and severity.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="archetypes-grid">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="archetype-card">
              <div className="archetype-card__accent skeleton" />
              <div className="archetype-card__body">
                <div className="skeleton" style={{ width: '70%', height: 16, marginBottom: 8 }} />
                <div className="skeleton" style={{ width: '100%', height: 12, marginBottom: 4 }} />
                <div className="skeleton" style={{ width: '50%', height: 12 }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="archetypes-grid">
          {archetypes.map((archetype, idx) => (
            <Link
              key={archetype.id}
              href={`/archetypes/${archetype.id}`}
              style={{ textDecoration: 'none', color: 'inherit' }}
            >
              <div className="archetype-card">
                <div
                  className="archetype-card__accent"
                  style={{ backgroundColor: ARCHETYPE_COLORS[idx % ARCHETYPE_COLORS.length] }}
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
                  {archetype.top_categories.length > 0 && (
                    <div style={{ marginTop: 'var(--space-sm)', display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {archetype.top_categories.slice(0, 3).map((cat) => (
                        <span key={cat} className="badge badge--neutral" style={{ fontSize: '0.6875rem' }}>
                          {cat}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
