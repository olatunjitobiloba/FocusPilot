import React, { useState } from 'react';

interface SuggestionCardProps {
  suggestion: {
    domain: string;
    distraction_score?: number;
    confidence?: 'high' | 'medium' | 'low';
    reason?: string;
    total_visits?: number;
    total_minutes?: number;
    frequency?: number;
    total_time_seconds?: number;
    factors?: {
      low_focus_ratio?: number;
      time_score?: number;
      abandonment_ratio?: number;
      timing_score?: number;
    };
  };
  onAccept: (domain: string) => void | Promise<void>;
  onDismiss: (domain: string) => void | Promise<void>;
}

function SuggestionCard({ suggestion, onAccept, onDismiss }: SuggestionCardProps) {
  const [showDetails, setShowDetails] = useState(false);

  const score = Math.max(0, Math.min(100, suggestion.distraction_score ?? 0));
  const confidence = suggestion.confidence || 'low';
  const visits = suggestion.total_visits ?? suggestion.frequency ?? 0;
  const minutes = suggestion.total_minutes ?? (suggestion.total_time_seconds ? Math.round(suggestion.total_time_seconds / 60) : 0);

  const getScoreColor = (value: number) => {
    if (value >= 70) return 'text-red-600 bg-red-100';
    if (value >= 40) return 'text-yellow-600 bg-yellow-100';
    return 'text-green-600 bg-green-100';
  };

  const getConfidenceBadge = (value: string) => {
    const styles = {
      high: 'bg-red-100 text-red-700',
      medium: 'bg-yellow-100 text-yellow-700',
      low: 'bg-gray-100 text-gray-700',
    };
    return styles[value as keyof typeof styles] || styles.low;
  };

  const scoreBarWidth = `${score}%`;
  const faviconUrl = `https://www.google.com/s2/favicons?domain=${suggestion.domain}&sz=32`;

  return (
    <div className="bg-white rounded-lg shadow p-5 hover:shadow-md transition">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center">
          <img
            src={faviconUrl}
            alt={suggestion.domain}
            className="w-8 h-8 rounded mr-3"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
          <div>
            <p className="font-bold text-gray-900 text-lg">{suggestion.domain}</p>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getConfidenceBadge(confidence)}`}>
                {confidence} confidence
              </span>
              <span className="text-xs text-gray-500">
                {visits} visits · {minutes} min
              </span>
            </div>
          </div>
        </div>

        <div className={`px-3 py-1 rounded-full font-bold text-lg ${getScoreColor(score)}`}>
          {score}
        </div>
      </div>

      <div className="mb-3">
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Distraction Score</span>
          <span>{score}/100</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all ${
              score >= 70
                ? 'bg-red-500'
                : score >= 40
                  ? 'bg-yellow-500'
                  : 'bg-green-500'
            }`}
            style={{ width: scoreBarWidth }}
          />
        </div>
      </div>

      <p className="text-gray-700 text-sm mb-4">
        {suggestion.reason || 'Based on your focus sessions, this site appears to reduce concentration.'}
      </p>

      <button
        onClick={() => setShowDetails(!showDetails)}
        className="text-xs text-green-600 hover:underline mb-3"
      >
        {showDetails ? 'Hide details' : 'Show factor breakdown'}
      </button>

      {showDetails && (
        <div className="bg-gray-50 rounded-lg p-3 mb-4 grid grid-cols-2 gap-2">
          <FactorBar label="Low-focus visits" value={suggestion.factors?.low_focus_ratio ?? 0} max={1} />
          <FactorBar label="Time spent" value={suggestion.factors?.time_score ?? 0} max={1} />
          <FactorBar label="Session abandonment" value={suggestion.factors?.abandonment_ratio ?? 0} max={1} />
          <FactorBar label="Timing correlation" value={suggestion.factors?.timing_score ?? 0} max={1} />
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={() => onAccept(suggestion.domain)}
          className="flex-1 bg-green-600 text-white py-2 rounded-lg font-semibold hover:bg-green-700 transition text-sm"
        >
          Block This Site
        </button>
        <button
          onClick={() => onDismiss(suggestion.domain)}
          className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 transition text-sm"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

function FactorBar({ label, value, max }: { label: string; value: number; max: number }) {
  const safeMax = max <= 0 ? 1 : max;
  const pct = Math.max(0, Math.min(100, Math.round((value / safeMax) * 100)));

  return (
    <div>
      <div className="flex justify-between text-xs text-gray-600 mb-1">
        <span>{label}</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-1.5">
        <div className="bg-green-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default SuggestionCard;