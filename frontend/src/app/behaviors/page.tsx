'use client';

import { useEffect, useState } from 'react';
import { fetchBehaviors } from '@/lib/api';
import type { BehaviorPatterns } from '@/lib/types';

const OUTCOME_COLORS: Record<string, string> = {
  'Found': '#34a853',
  'Not Found': '#ea4335',
  'Gave Up': '#a142f4',
  'Used Workaround': '#fbbc04',
  'found': '#34a853',
  'not_found': '#ea4335',
  'gave_up': '#a142f4',
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
  const strategyOutcomes: Record<string, { outcome: string, count: number, percentage: number }[]> = {};
  
  if (data) {
    data.flow_data.forEach(flow => {
      const strategyKey = String(flow.strategy || flow.source || '');
      const count = flow.count || flow.value || 0;
      strategyTotals[strategyKey] = (strategyTotals[strategyKey] || 0) + count;
    });

    data.flow_data.forEach(flow => {
      const strategyKey = String(flow.strategy || flow.source || '');
      const outcomeKey = String(flow.outcome || flow.target || '');
      const count = flow.count || flow.value || 0;
      const percentage = strategyTotals[strategyKey] ? Math.round((count / strategyTotals[strategyKey]) * 100) : 0;
      
      if (!strategyOutcomes[strategyKey]) {
        strategyOutcomes[strategyKey] = [];
      }
      strategyOutcomes[strategyKey].push({ outcome: outcomeKey, count, percentage });
    });

    // Sort outcomes by percentage descending for consistent bar rendering
    Object.keys(strategyOutcomes).forEach(key => {
      strategyOutcomes[key].sort((a, b) => b.percentage - a.percentage);
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
            <div style={{ display: 'flex', gap: 'var(--space-2xl)', flexWrap: 'wrap' }}>
              
              {/* Strategies Flow Column */}
              <div style={{ flex: 3, display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', minWidth: '300px' }}>
                <div style={{ display: 'flex', gap: 'var(--space-xl)', marginBottom: '4px' }}>
                  <div style={{ flex: 1, fontSize: '0.75rem', fontWeight: 600, color: 'var(--md-on-surface-variant)', textTransform: 'uppercase' }}>Search Strategy</div>
                  <div style={{ flex: 2, fontSize: '0.75rem', fontWeight: 600, color: 'var(--md-on-surface-variant)', textTransform: 'uppercase' }}>Outcome Flow</div>
                </div>
                
                {data.strategies.map(strategyKey => {
                  const outcomes = strategyOutcomes[strategyKey] || [];
                  return (
                    <div key={strategyKey} style={{ display: 'flex', gap: 'var(--space-xl)', alignItems: 'center' }}>
                      <div style={{
                        flex: 1,
                        padding: 'var(--space-sm) var(--space-md)',
                        background: 'var(--md-primary-container)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.8125rem',
                        fontWeight: 500,
                        color: 'var(--md-on-primary-container)',
                        textTransform: 'capitalize',
                      }}>
                        {strategyKey.replace(/_/g, ' ')}
                      </div>
                      <div style={{ flex: 2 }}>
                        <div style={{ display: 'flex', width: '100%', height: 28, borderRadius: 'var(--radius-full)', overflow: 'hidden', backgroundColor: 'var(--md-surface-variant)' }}>
                          {outcomes.map(out => (
                            <div 
                              key={out.outcome} 
                              style={{ 
                                width: `${out.percentage}%`, 
                                backgroundColor: OUTCOME_COLORS[out.outcome] || 'var(--md-outline)',
                                height: '100%',
                                transition: 'width 0.3s ease',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: '#fff',
                                fontSize: '0.75rem',
                                fontWeight: 600
                              }}
                              title={`${out.outcome.replace(/_/g, ' ')}: ${out.percentage}% (${out.count})`}
                            >
                              {out.percentage >= 10 ? `${out.percentage}%` : ''}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Outcomes Legend Column */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)', minWidth: '150px' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--md-on-surface-variant)', textTransform: 'uppercase', marginBottom: '4px' }}>
                  Legend (Outcomes)
                </div>
                {data.outcomes.map((outcome) => {
                  const color = OUTCOME_COLORS[outcome] || 'var(--md-outline)';
                  return (
                    <div
                      key={outcome}
                      style={{
                        padding: 'var(--space-sm) var(--space-md)',
                        background: `${color}15`,
                        borderLeft: `4px solid ${color}`,
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.8125rem',
                        fontWeight: 500,
                        textTransform: 'capitalize',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
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
          <div style={{ overflowX: 'auto', background: 'var(--md-surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--md-outline-variant)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['Strategy', 'Total Uses', 'Outcome Distribution', 'Details'].map((header) => (
                    <th
                      key={header}
                      style={{
                        padding: 'var(--space-md)',
                        textAlign: 'left',
                        borderBottom: '2px solid var(--md-outline-variant)',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: 'var(--md-on-surface-variant)',
                        textTransform: 'uppercase',
                        background: 'var(--md-surface-container-low)'
                      }}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.strategies.map((strategyKey, idx) => {
                  const outcomes = strategyOutcomes[strategyKey] || [];
                  const total = strategyTotals[strategyKey] || 0;
                  return (
                    <tr
                      key={strategyKey}
                      style={{
                        borderBottom: idx === data.strategies.length - 1 ? 'none' : '1px solid var(--md-outline-variant)',
                      }}
                    >
                      <td style={{ padding: 'var(--space-md)', fontSize: '0.875rem', fontWeight: 600, textTransform: 'capitalize' }}>
                        {strategyKey.replace(/_/g, ' ')}
                      </td>
                      <td style={{ padding: 'var(--space-md)', fontSize: '0.875rem', color: 'var(--md-on-surface-variant)' }}>
                        <strong>{total}</strong>
                      </td>
                      <td style={{ padding: 'var(--space-md)', minWidth: '200px' }}>
                        <div style={{ display: 'flex', width: '100%', height: 10, borderRadius: 'var(--radius-full)', overflow: 'hidden', backgroundColor: 'var(--md-surface-variant)' }}>
                          {outcomes.map(out => (
                            <div 
                              key={out.outcome} 
                              style={{ 
                                width: `${out.percentage}%`, 
                                backgroundColor: OUTCOME_COLORS[out.outcome] || 'var(--md-outline)',
                                height: '100%'
                              }}
                              title={`${out.outcome.replace(/_/g, ' ')}: ${out.percentage}% (${out.count})`}
                            />
                          ))}
                        </div>
                      </td>
                      <td style={{ padding: 'var(--space-md)' }}>
                        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                          {outcomes.map(out => (
                            <span key={out.outcome} style={{ fontSize: '0.75rem', color: 'var(--md-on-surface)', display: 'flex', alignItems: 'center', gap: '4px', whiteSpace: 'nowrap' }}>
                              <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: OUTCOME_COLORS[out.outcome] }} />
                              {out.percentage}% {out.outcome.replace(/_/g, ' ')}
                            </span>
                          ))}
                        </div>
                      </td>
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
