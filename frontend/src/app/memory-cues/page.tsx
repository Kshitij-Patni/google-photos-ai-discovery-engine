'use client';

import { useEffect, useState } from 'react';
import { fetchMemoryCues } from '@/lib/api';
import type { MemoryCueMatrix } from '@/lib/types';

function getHeatmapColor(value: number, max: number, mode: 'remembered' | 'forgotten'): string {
  if (max === 0) return 'var(--md-surface-container)';
  const intensity = value / max;
  
  if (mode === 'forgotten') {
    // Red gradient: light red → deep red
    const r = Math.round(253 - intensity * 42);
    const g = Math.round(216 - intensity * 169);
    const b = Math.round(216 - intensity * 169);
    return `rgb(${r}, ${g}, ${b})`;
  } else {
    // Google Blue gradient: light → deep
    const r = Math.round(210 - intensity * 184);
    const g = Math.round(227 - intensity * 112);
    const b = Math.round(253 - intensity * 21);
    return `rgb(${r}, ${g}, ${b})`;
  }
}

function getTextColor(value: number, max: number): string {
  return value / max > 0.5 ? '#ffffff' : 'var(--md-on-surface)';
}

export default function MemoryCuesPage() {
  const [data, setData] = useState<MemoryCueMatrix | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<'remembered' | 'forgotten'>('remembered');

  useEffect(() => {
    setLoading(true);
    fetchMemoryCues(mode)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [mode]);

  if (loading) {
    return (
      <div>
        <div className="hero">
          <div>
            <div className="skeleton" style={{ width: 400, height: 32, marginBottom: 8 }} />
            <div className="skeleton" style={{ width: 300, height: 16 }} />
          </div>
        </div>
        <div className="skeleton" style={{ width: '100%', height: 400, borderRadius: 'var(--radius-md)' }} />
      </div>
    );
  }

  const maxValue = data
    ? Math.max(...data.matrix.flat(), 1)
    : 1;

  return (
    <div>
      {/* Hero */}
      <div className="hero" style={{ borderBottom: '1px solid var(--md-outline-variant)', paddingBottom: 'var(--space-md)', marginBottom: 'var(--space-xl)' }}>
        <div>
          <h1 className="hero__title">Memory Cue Analysis</h1>
          <p className="hero__subtitle">What Users Remember vs. What They Forget</p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-sm)', alignItems: 'center' }}>
          <button
            className={`chip ${mode === 'remembered' ? 'chip--selected' : ''}`}
            onClick={() => setMode('remembered')}
          >
            Cues Remembered
          </button>
          <button
            className={`chip ${mode === 'forgotten' ? 'chip--selected' : ''}`}
            onClick={() => setMode('forgotten')}
          >
            Cues Forgotten
          </button>
        </div>
      </div>

      {/* Heatmap */}
      {data && data.categories.length > 0 ? (
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'separate',
              borderSpacing: 3,
              marginBottom: 'var(--space-xl)',
            }}
          >
            <thead>
              <tr>
                <th
                  style={{
                    textAlign: 'left',
                    padding: 'var(--space-sm)',
                    fontSize: '0.75rem',
                    color: 'var(--md-on-surface-variant)',
                    fontWeight: 600,
                  }}
                >
                  Photo Category
                </th>
                {data.cue_types.map((cue) => (
                  <th
                    key={cue}
                    style={{
                      padding: 'var(--space-sm)',
                      fontSize: '0.75rem',
                      color: 'var(--md-on-surface-variant)',
                      fontWeight: 600,
                      textAlign: 'center',
                      textTransform: 'capitalize',
                    }}
                  >
                    {cue}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.categories.map((category, rowIdx) => (
                <tr key={category}>
                  <td
                    style={{
                      padding: 'var(--space-sm) var(--space-md)',
                      fontWeight: 500,
                      fontSize: '0.875rem',
                      whiteSpace: 'nowrap',
                      textTransform: 'capitalize',
                    }}
                  >
                    {category}
                  </td>
                  {data.matrix[rowIdx]?.map((value, colIdx) => (
                    <td
                      key={colIdx}
                      style={{
                        padding: 'var(--space-sm)',
                        textAlign: 'center',
                        borderRadius: 'var(--radius-sm)',
                        backgroundColor: getHeatmapColor(value, maxValue, mode),
                        color: getTextColor(value, maxValue),
                        fontWeight: 600,
                        fontSize: '0.8125rem',
                        minWidth: 56,
                        transition: 'transform 0.1s ease',
                      }}
                    >
                      {value}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          {/* Legend */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-sm)',
              justifyContent: 'center',
              fontSize: '0.75rem',
              color: 'var(--md-on-surface-variant)',
            }}
          >
            <span>Low</span>
            <div
              style={{
                display: 'flex',
                height: 12,
                width: 200,
                borderRadius: 'var(--radius-sm)',
                overflow: 'hidden',
              }}
            >
              {Array.from({ length: 10 }, (_, i) => (
                <div
                  key={i}
                  style={{
                    flex: 1,
                    backgroundColor: getHeatmapColor(i + 1, 10, mode),
                  }}
                />
              ))}
            </div>
            <span>High</span>
          </div>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--md-on-surface-variant)' }}>
          <p>No memory cue data available yet. Wire the API to load real data from the SQLite database.</p>
        </div>
      )}

      {/* Statistical Breakdown added at the end */}
      <div style={{ marginTop: 'var(--space-2xl)', marginBottom: 'var(--space-xl)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
        <div>
          <h3 style={{ fontSize: '1.15rem', marginBottom: 'var(--space-xs)', color: 'var(--md-on-surface)' }}>Statistical Breakdown of Memory Cues</h3>
          <p style={{ color: 'var(--md-on-surface-variant)', fontSize: '0.95rem', marginBottom: 'var(--space-md)', lineHeight: '1.5' }}>
            Based on a database analysis of over 1,300 documented memory cues, nearly 60% of all user queries rely on <strong>Time</strong> and <strong>People</strong>. Users typically combine multiple cues (e.g., searching for a Visual Detail tied to a Person). When the engine fails to intersect these dimensions, users experience high frustration.
          </p>
        </div>
        
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: 'var(--space-md)',
        }}>
          {/* Card 1 */}
          <div style={{ background: 'var(--md-surface-container)', padding: 'var(--space-md)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <strong style={{ color: 'var(--md-primary)', fontSize: '1.05rem' }}>1. Time & Temporal Anchors</strong>
              <span className="badge badge--primary" style={{ fontSize: '0.8rem' }}>31.4%</span>
            </div>
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--md-on-surface-variant)', lineHeight: '1.4' }}>
              <strong>What they remember:</strong> <em>When</em> something happened (seasons, life phases, relative time like "last summer").<br/><br/>
              <strong>Why it matters:</strong> Users rely on the timeline scrubber because they know roughly when an event occurred, but get frustrated scrolling endlessly for the exact day.
            </p>
          </div>

          {/* Card 2 */}
          <div style={{ background: 'var(--md-surface-container)', padding: 'var(--space-md)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <strong style={{ color: 'var(--md-primary)', fontSize: '1.05rem' }}>2. People & Faces</strong>
              <span className="badge badge--primary" style={{ fontSize: '0.8rem' }}>27.7%</span>
            </div>
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--md-on-surface-variant)', lineHeight: '1.4' }}>
              <strong>What they remember:</strong> <em>Who</em> was in the photo (family members, friends, faces).<br/><br/>
              <strong>Why it matters:</strong> Users struggle when the system fails to tag someone correctly, or when they want to find a photo of a specific person without their face perfectly visible.
            </p>
          </div>

          {/* Card 3 */}
          <div style={{ background: 'var(--md-surface-container)', padding: 'var(--space-md)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <strong style={{ color: 'var(--md-primary)', fontSize: '1.05rem' }}>3. Visual Details & Objects</strong>
              <span className="badge badge--primary" style={{ fontSize: '0.8rem' }}>10.3%</span>
            </div>
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--md-on-surface-variant)', lineHeight: '1.4' }}>
              <strong>What they remember:</strong> Specific visual aspects like colors, clothing, or objects (e.g., "the red dress").<br/><br/>
              <strong>Why it matters:</strong> Translating a visual memory into a text search query often fails if the AI hasn't tagged that specific object or color in the image metadata.
            </p>
          </div>

          {/* Card 4 */}
          <div style={{ background: 'var(--md-surface-container)', padding: 'var(--space-md)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <strong style={{ color: 'var(--md-primary)', fontSize: '1.05rem' }}>4. Place & Location</strong>
              <span className="badge badge--primary" style={{ fontSize: '0.8rem' }}>8.3%</span>
            </div>
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--md-on-surface-variant)', lineHeight: '1.4' }}>
              <strong>What they remember:</strong> <em>Where</em> the photo was taken (geographic location, specific venue).<br/><br/>
              <strong>Why it matters:</strong> If location services were off, or if the user doesn't remember the exact city name but rather the <em>type</em> of place (e.g., "a cabin"), search often fails.
            </p>
          </div>

          {/* Card 5 */}
          <div style={{ background: 'var(--md-surface-container)', padding: 'var(--space-md)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <strong style={{ color: 'var(--md-primary)', fontSize: '1.05rem' }}>5. Emotion & Context</strong>
              <span className="badge badge--primary" style={{ fontSize: '0.8rem' }}>8.3%</span>
            </div>
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--md-on-surface-variant)', lineHeight: '1.4' }}>
              <strong>What they remember:</strong> How a photo <em>felt</em> or the emotional atmosphere (e.g., "a funny moment").<br/><br/>
              <strong>Why it matters:</strong> Abstract memory cues are challenging for traditional engines, which tend to process literal objects instead of the "vibe" of the photo.
            </p>
          </div>

          {/* Card 6 */}
          <div style={{ background: 'var(--md-surface-container)', padding: 'var(--space-md)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <strong style={{ color: 'var(--md-primary)', fontSize: '1.05rem' }}>6. Activity & Events</strong>
              <span className="badge badge--primary" style={{ fontSize: '0.8rem' }}>5.3%</span>
            </div>
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--md-on-surface-variant)', lineHeight: '1.4' }}>
              <strong>What they remember:</strong> The action or event taking place (e.g., graduation, hiking).<br/><br/>
              <strong>Why it matters:</strong> Searching for "wedding" might return photos with white dresses, but miss candid moments if the AI doesn't recognize the overarching activity.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
