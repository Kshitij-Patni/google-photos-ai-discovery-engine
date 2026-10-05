'use client';

import { useEffect, useState } from 'react';
import { fetchBehaviors } from '@/lib/api';
import type { BehaviorPatterns } from '@/lib/types';

const OUTCOME_COLORS: Record<string, string> = {
  'Found': '#34a853',
  'Not Found': '#ea4335',
  'Gave Up': '#d93025',
  'Used Workaround': '#fbbc04',
  'found': '#34a853',
  'not_found': '#ea4335',
  'gave_up': '#d93025',
  'workaround': '#fbbc04',
  'used_workaround': '#fbbc04',
};

export default function BehaviorsPage() {
  const [data, setData] = useState<BehaviorPatterns | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBehaviors()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div>
        <div className="hero">
          <div>
            <div className="skeleton" style={{ width: 300, height: 32, marginBottom: 8 }} />
            <div className="skeleton" style={{ width: 400, height: 16 }} />
          </div>
        </div>
        <div className="skeleton" style={{ width: '100%', height: 400, borderRadius: 'var(--radius-md)' }} />
      </div>
    );
  }

  const strategyTotals: Record<string, number> = {};
  if (data) {
    data.flow_data.forEach(flow => {
      const strategyKey = String(flow.strategy || flow.source || '');
      const count = flow.count || flow.value || 0;
      strategyTotals[strategyKey] = (strategyTotals[strategyKey] || 0) + count;
    });
  }

  return (
    <div>
      {/* Hero */}
      <div className="hero">
        <div>
          <h1 className="hero__title">How Users Search</h1>
          <p className="hero__subtitle">
            Search strategy → outcome flow patterns showing how users attempt photo retrieval and what happens.
          </p>
        </div>
      </div>

      {data && data.flow_data.length > 0 ? (
        <>
          {/* Sankey-style Flow Visualization */}
          <div
            style={{
              background: 'var(--md-surface-container-low)',
              borderRadius: 'var(--radius-lg)',
              padding: 'var(--space-xl)',
              marginBottom: 'var(--space-xl)',
            }}
          >
            <h3 style={{ marginBottom: 'var(--space-lg)', textAlign: 'center' }}>Strategy → Outcome Flow</h3>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                gap: 'var(--space-xl)',
                alignItems: 'stretch',
                minHeight: 300,
              }}
            >
              {/* Strategies Column */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)', flex: 1 }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--md-on-surface-variant)', textTransform: 'uppercase', marginBottom: 'var(--space-sm)' }}>
                  Search Strategy
                </div>
                {data.strategies.map((strategy) => (
                  <div
                    key={strategy}
                    style={{
                      padding: 'var(--space-sm) var(--space-md)',
                      background: 'var(--md-primary-container)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.8125rem',
                      fontWeight: 500,
                      color: 'var(--md-on-primary-container)',
                      textTransform: 'capitalize',
                    }}
                  >
                    {strategy.replace(/_/g, ' ')}
                  </div>
                ))}
              </div>

              {/* Flow Arrows */}
              <div
                style={{
                  flex: 2,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  gap: 'var(--space-sm)',
                }}
              >
                {data.flow_data.slice(0, 8).map((flow, idx) => {
                  const outcomeKey = String(flow.outcome || flow.target || '');
                  const strategyKey = String(flow.strategy || flow.source || '');
                  const color = OUTCOME_COLORS[outcomeKey] || 'var(--md-outline)';
                  const count = flow.count || flow.value || 0;
                  const percentage = strategyTotals[strategyKey] ? Math.round((count / strategyTotals[strategyKey]) * 100) : 0;
                  return (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--space-sm)',
                        padding: '2px var(--space-sm)',
                      }}
                    >
                      <span style={{ fontSize: '0.75rem', color: 'var(--md-on-surface-variant)', minWidth: 100, textTransform: 'capitalize' }}>
                        {strategyKey.replace(/_/g, ' ')}
                      </span>
                      <div
                        style={{
                          flex: 1,
                          height: Math.max(4, Math.min(percentage / 2, 24)),
                          backgroundColor: color,
                          borderRadius: 'var(--radius-full)',
                          opacity: 0.7,
                        }}
                      />
                      <span style={{ fontSize: '0.75rem', color: 'var(--md-on-surface-variant)', minWidth: 80, textTransform: 'capitalize' }}>
                        {outcomeKey.replace(/_/g, ' ')}
                      </span>
                      <span style={{ fontSize: '0.6875rem', color: 'var(--md-on-surface-variant)' }}>
                        {percentage}% ({count})
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* Outcomes Column */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)', flex: 1 }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--md-on-surface-variant)', textTransform: 'uppercase', marginBottom: 'var(--space-sm)' }}>
                  Outcome
                </div>
                {data.outcomes.map((outcome) => {
                  const color = OUTCOME_COLORS[outcome] || 'var(--md-outline)';
                  return (
                    <div
                      key={outcome}
                      style={{
                        padding: 'var(--space-sm) var(--space-md)',
                        background: `${color}20`,
                        borderLeft: `3px solid ${color}`,
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.8125rem',
                        fontWeight: 500,
                        textTransform: 'capitalize',
                      }}
                    >
                      {outcome.replace(/_/g, ' ')}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Data Table */}
          <h3 style={{ marginBottom: 'var(--space-md)' }}>Strategy Breakdown</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['Strategy', 'Percentage (Count)', 'Outcome', ''].map((header) => (
                    <th
                      key={header}
                      style={{
                        padding: 'var(--space-md)',
                        textAlign: 'left',
                        borderBottom: '2px solid var(--md-outline)',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: 'var(--md-on-surface-variant)',
                        textTransform: 'uppercase',
                      }}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.flow_data.map((row, idx) => {
                  const strategyKey = String(row.strategy || row.source || '');
                  const count = row.count || row.value || 0;
                  const percentage = strategyTotals[strategyKey] ? Math.round((count / strategyTotals[strategyKey]) * 100) : 0;
                  return (
                    <tr
                      key={idx}
                      style={{
                        backgroundColor: idx % 2 === 0 ? 'var(--md-surface)' : 'var(--md-surface-dim)',
                      }}
                    >
                      <td style={{ padding: 'var(--space-md)', fontSize: '0.875rem', fontWeight: 500, textTransform: 'capitalize' }}>
                        {strategyKey.replace(/_/g, ' ')}
                      </td>
                      <td style={{ padding: 'var(--space-md)', fontSize: '0.875rem' }}>
                        <strong>{percentage}%</strong> ({count})
                      </td>
                    <td style={{ padding: 'var(--space-md)' }}>
                      <span
                        className="badge"
                        style={{
                          backgroundColor: `${OUTCOME_COLORS[String(row.outcome || row.target || '')] || 'var(--md-outline)'}20`,
                          color: OUTCOME_COLORS[String(row.outcome || row.target || '')] || 'var(--md-on-surface-variant)',
                        }}
                      >
                        {String(row.outcome || row.target || '').replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td style={{ padding: 'var(--space-md)' }}></td>
                  </tr>
                );
              })}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--md-on-surface-variant)' }}>
          <p>No behavior pattern data available yet. Wire the API to load real data from the SQLite database.</p>
        </div>
      )}
    </div>
  );
}
