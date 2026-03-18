// src/components/RiskMeter.tsx
import React, { useEffect, useState } from 'react';
import { predictionsAPI } from '../api/client';
import { RiskPrediction } from '../types/predictions';
import AppIcon, { IconName } from './AppIcon';

const FALLBACK_RISK: RiskPrediction = {
  risk_score: 0,
  risk_percentage: 0,
  risk_level: 'low',
  will_procrastinate: false,
  confidence: 'low',
  model_available: false,
  top_risk_factors: [],
  assessed_at: new Date().toISOString(),
  message: 'Risk data temporarily unavailable. Collecting data for AI model.'
};

interface RiskMeterProps {
  compact?: boolean;       // For extension popup (smaller)
  autoRefresh?: boolean;   // Poll every 60 seconds
}

function RiskMeter({ compact = false, autoRefresh = false }: RiskMeterProps) {
  const [risk, setRisk]       = useState<RiskPrediction | null>(null);
  const [loading, setLoading] = useState(true);

  const loadRisk = React.useCallback(async () => {
    try {
      const response = await predictionsAPI.getRisk();
      setRisk(response.data);
    } catch (error) {
      console.error('Error loading risk:', error);
      setRisk(FALLBACK_RISK);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRisk();

    if (autoRefresh) {
      const interval = setInterval(loadRisk, 60_000); // Every 60s
      return () => clearInterval(interval);
    }
  }, [autoRefresh, loadRisk]);

  if (loading) {
    return (
      <div className="animate-pulse bg-gray-200 rounded-lg h-24" />
    );
  }

  const safeRisk = risk || FALLBACK_RISK;

  // ── Color scheme by risk level ─────────────────────────────────────
  const colors: Record<string, { bg: string; border: string; text: string; bar: string; icon: IconName }> = {
    low:      { bg: 'bg-green-50',  border: 'border-green-200', text: 'text-green-700',  bar: 'bg-green-500',  icon: 'check-circle' },
    medium:   { bg: 'bg-yellow-50', border: 'border-yellow-200',text: 'text-yellow-700', bar: 'bg-yellow-500', icon: 'info' },
    high:     { bg: 'bg-orange-50', border: 'border-orange-200',text: 'text-orange-700', bar: 'bg-orange-500', icon: 'warning' },
    critical: { bg: 'bg-red-50',    border: 'border-red-200',   text: 'text-red-700',    bar: 'bg-red-500',    icon: 'intervention' }
  };

  const c = colors[safeRisk.risk_level] || colors.low;
  const cardShellClass = 'bg-white border-2 border-green-300 shadow-sm';

  // ── Compact version (for extension popup) ─────────────────────────
  if (compact) {
    return (
      <div className={`${cardShellClass} rounded-lg p-3`}>
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-semibold text-gray-900 flex items-center gap-1.5">
            <AppIcon name={c.icon} className={c.text} size={14} />
            Procrastination Risk
          </span>
          <span className={`text-lg font-bold ${c.text}`}>
            {safeRisk.risk_percentage}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`${c.bar} h-2 rounded-full transition-all duration-500`}
            style={{ width: `${safeRisk.risk_percentage}%` }}
          />
        </div>
        <p className={`text-xs ${c.text} mt-1 capitalize`}>
          {safeRisk.risk_level} risk
          {!safeRisk.model_available && ' (collecting data)'}
        </p>
      </div>
    );
  }

  // ── Full version (for dashboard) ──────────────────────────────────
  return (
    <div className={`${cardShellClass} rounded-xl p-6`}>

      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <AppIcon name={c.icon} className={c.text} size={18} />
            Procrastination Risk
          </h3>
          <p className="text-sm text-gray-500 mt-0.5">
            {safeRisk.model_available
              ? `Updated ${new Date(safeRisk.assessed_at).toLocaleTimeString()}`
              : 'Collecting data for AI model'
            }
          </p>
        </div>

        {/* Big risk percentage */}
        <div className="text-right">
          <p className={`text-4xl font-bold ${c.text}`}>
            {safeRisk.risk_percentage}%
          </p>
          <p className={`text-sm font-medium ${c.text} capitalize`}>
            {safeRisk.risk_level} risk
          </p>
        </div>
      </div>

      {/* Risk bar */}
      <div className="mb-4">
        <div className="w-full bg-gray-200 rounded-full h-4">
          <div
            className={`${c.bar} h-4 rounded-full transition-all duration-700`}
            style={{ width: `${safeRisk.risk_percentage}%` }}
          />
        </div>
        {/* Scale labels */}
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>Low</span>
          <span>Medium</span>
          <span>High</span>
          <span>Critical</span>
        </div>
      </div>

      {/* Risk factors */}
      {safeRisk.top_risk_factors && safeRisk.top_risk_factors.length > 0 && (
        <div>
          <p className="text-sm font-semibold text-gray-700 mb-2">
            Risk Factors:
          </p>
          <div className="space-y-2">
            {safeRisk.top_risk_factors.map((factor, i) => (
              <div
                key={i}
                className="flex items-start gap-2 text-sm"
              >
                <AppIcon
                  name={
                    factor.severity === 'high'
                      ? 'warning'
                      : factor.severity === 'medium'
                        ? 'info'
                        : 'check-circle'
                  }
                  className="mt-0.5 text-gray-500"
                  size={14}
                />
                <div>
                  <span className="font-medium text-gray-800">
                    {factor.factor}:
                  </span>{' '}
                  <span className="text-gray-600">{factor.value}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No model message */}
      {!safeRisk.model_available && (
        <div className="mt-3 p-3 bg-white bg-opacity-60 rounded-lg">
          <p className="text-sm text-gray-600">
            {safeRisk.message || 'Complete more focus sessions to enable AI predictions. The model trains automatically after 5 sessions.'}
          </p>
        </div>
      )}

      {/* Confidence badge */}
      {safeRisk.model_available && (
        <div className="mt-3 flex items-center gap-2">
          <span className="text-xs text-gray-500">Model confidence:</span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
            safeRisk.confidence === 'high'   ? 'bg-green-100 text-green-700'  :
            safeRisk.confidence === 'medium' ? 'bg-yellow-100 text-yellow-700':
                                           'bg-gray-100 text-gray-600'
          }`}>
            {safeRisk.confidence}
          </span>
        </div>
      )}
    </div>
  );
}

export default RiskMeter;
