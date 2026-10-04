'use client';

import { useState } from 'react';
import { queryRAG } from '@/lib/api';
import type { QueryResponse } from '@/lib/types';

const SUGGESTION_CHIPS = [
  'Top retrieval problems?',
  'Album organization issues',
  'What do users forget most?',
  'Search strategy success rates',
  'Show YouTube complaints',
];

interface QAEntry {
  question: string;
  response: QueryResponse;
}

export default function ExplorePage() {
  const [query, setQuery] = useState('');
  const [history, setHistory] = useState<QAEntry[]>([]);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(question: string) {
    if (!question.trim()) return;
    setLoading(true);
    setQuery('');
    try {
      const response = await queryRAG(question);
      setHistory((prev) => [{ question, response }, ...prev]);
    } catch (err) {
      console.error('Query failed:', err);
      setHistory((prev) => [
        {
          question,
          response: {
            answer: 'Sorry, an error occurred while processing your question. Please try again.',
            sources: [],
            confidence: 0,
          },
        },
        ...prev,
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      {/* Search Section */}
      <div style={{ textAlign: 'center', padding: '10vh 0 4vh' }}>
        <h1 style={{ marginBottom: '32px', fontSize: '2.8rem', fontWeight: 400, fontFamily: 'var(--font-display)', letterSpacing: '-0.5px' }}>
          Explore Insights
        </h1>
        <div className="google-search-bar-wrapper">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSubmit(query);
            }}
          >
            <div className="google-search-icon">
              <svg focusable="false" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">
                <path fill="currentColor" d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"></path>
              </svg>
            </div>
            <input
              type="text"
              className="google-search-bar"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question about photo retrieval insights..."
            />
          </form>
        </div>

        {/* Suggestion Chips */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-sm)', justifyContent: 'center' }}>
          {SUGGESTION_CHIPS.map((chip) => (
            <button
              key={chip}
              className="chip"
              onClick={() => handleSubmit(chip)}
              disabled={loading}
            >
              {chip}
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: 'center', padding: 'var(--space-xl)' }}>
          <p style={{ marginBottom: 'var(--space-lg)', color: 'var(--md-secondary)', fontSize: '0.9375rem', fontStyle: 'italic' }}>
            Please have patience, it may take a few moments as we search through thousands of user feedback records and synthesize a comprehensive answer...
          </p>
          <div
            className="skeleton"
            style={{ width: '60%', height: 20, margin: '0 auto var(--space-md)' }}
          />
          <div
            className="skeleton"
            style={{ width: '80%', height: 16, margin: '0 auto var(--space-sm)' }}
          />
          <div
            className="skeleton"
            style={{ width: '70%', height: 16, margin: '0 auto' }}
          />
        </div>
      )}

      {/* Results */}
      {history.length > 0 && (
        <div>
          <h3 style={{ marginBottom: 'var(--space-md)' }}>
            {history.length === 1 ? 'Result' : 'Recent Questions'}
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            {history.map((entry, index) => (
              <div key={index} className="evidence-card">
                <div
                  style={{
                    fontFamily: 'var(--font-headline)',
                    fontWeight: 600,
                    fontSize: '1rem',
                    marginBottom: 'var(--space-sm)',
                    color: 'var(--md-primary)',
                  }}
                >
                  {entry.question}
                </div>
                <div
                  style={{
                    fontSize: '0.9375rem',
                    lineHeight: 1.6,
                    color: 'var(--md-on-surface)',
                    marginBottom: 'var(--space-md)',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {entry.response.answer}
                </div>
                <div className="evidence-card__meta">
                  {entry.response.sources.length > 0 && (
                    <>
                      {entry.response.sources.slice(0, 5).map((source, sIdx) => (
                        <span
                          key={sIdx}
                          className={`source-badge source-badge--${
                            source.source === 'play_store'
                              ? 'play-store'
                              : source.source === 'app_store'
                              ? 'app-store'
                              : 'youtube'
                          }`}
                        >
                          {source.source === 'play_store'
                            ? 'Play Store'
                            : source.source === 'app_store'
                            ? 'App Store'
                            : 'YouTube'}
                        </span>
                      ))}
                    </>
                  )}
                  <span className="badge badge--primary">
                    {(entry.response.confidence * 100).toFixed(0)}% confidence
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
