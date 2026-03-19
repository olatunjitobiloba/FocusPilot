// src/pages/ProductivityDNA.tsx
import React, { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import { dnaAPI } from '../api/client';
import { DNAResult, ClusterProfile, DNAInsight, HeatmapCell, DNAEligibility } from '../types/dna';
import AppIcon, { IconName } from '../components/AppIcon';
import { BADGE_GREEN, CHART_GREEN } from '../utils/greenPalette';

const DAYS   = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS  = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21];
const DNA_CACHE_KEY = 'focuspilot_dna_cache_v1';
const LEGACY_EMOJI_ICON_MAP: Record<string, IconName> = {
  '\u{1F4C5}': 'clock',
  '\u{1F4A1}': 'lightbulb',
  '\u{1F3AF}': 'target',
  '\u26A0\uFE0F': 'warning',
  '\u26A0': 'warning',
  '\u2705': 'check-circle',
  '\u{1F525}': 'spark',
  '\u2B50': 'spark',
  '\u{1F4F1}': 'activity'
};

const normalizeIconName = (iconValue?: string | null): IconName => {
  const icon = (iconValue || '').toLowerCase().trim();
  const legacyIcon = LEGACY_EMOJI_ICON_MAP[iconValue || ''];
  if (legacyIcon) return legacyIcon;

  if (icon.includes('search')) return 'search';
  if (icon.includes('clock') || icon.includes('calendar')) return 'clock';
  if (icon.includes('light')) return 'lightbulb';
  if (icon.includes('target')) return 'target';
  if (icon.includes('warning')) return 'warning';
  if (icon.includes('check')) return 'check-circle';
  if (icon.includes('fire') || icon.includes('star')) return 'spark';
  if (icon.includes('phone')) return 'activity';

  return 'info';
};

function ProductivityDNA() {
  const [dna,      setDna]      = useState<DNAResult | null>(null);
  const [loading,  setLoading]  = useState(true);
  const [training, setTraining] = useState(false);
  const [error,    setError]    = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [eligibility, setEligibility] = useState<DNAEligibility | null>(null);

  useEffect(() => { loadDNA(); }, []);

  useEffect(() => {
    const cached = localStorage.getItem(DNA_CACHE_KEY);
    if (!cached) return;
    try {
      const parsed = JSON.parse(cached);
      if (parsed && typeof parsed === 'object') {
        setDna(parsed as DNAResult);
        setLoading(false);
      }
    } catch {
      localStorage.removeItem(DNA_CACHE_KEY);
    }
  }, []);

  useEffect(() => {
    loadEligibility();
  }, []);

  const loadDNA = async (showLoadError = true) => {
    try {
      const res = await dnaAPI.getResults();
      setDna(res.data);
      try {
        localStorage.setItem(DNA_CACHE_KEY, JSON.stringify(res.data));
      } catch {
        // Ignore cache write failures.
      }
      setLoadError(null);
      return res.data;
    } catch (err) {
      console.error('DNA load error:', err);
      const cached = localStorage.getItem(DNA_CACHE_KEY);
      if (cached) {
        try {
          const parsed = JSON.parse(cached);
          if (parsed && typeof parsed === 'object') {
            setDna(parsed as DNAResult);
          }
        } catch {
          localStorage.removeItem(DNA_CACHE_KEY);
        }
      }
      if (showLoadError) {
        setLoadError('Could not load saved DNA results right now. Please retry.');
      }
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const handleTrain = async () => {
    setTraining(true);
    setError(null);
    try {
      const trainRes = await dnaAPI.train();
      // Show fresh analysis immediately, even if follow-up /results fetch is transiently down.
      if (trainRes?.data?.n_clusters) {
        setDna({ ...trainRes.data, trained: true } as DNAResult);
        try {
          localStorage.setItem(DNA_CACHE_KEY, JSON.stringify({ ...trainRes.data, trained: true }));
        } catch {
          // Ignore cache write failures.
        }
        setLoadError(null);
      }

      try {
        await loadDNA(false);
      } catch {
        // Preserve successful training payload above; a failed reload should not
        // bounce the UI back to the not-trained state.
      }

      await loadEligibility();
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
        'Training failed. Complete at least 5 sessions first.'
      );
    } finally {
      setTraining(false);
    }
  };

  const loadEligibility = async () => {
    try {
      const res = await dnaAPI.getEligibility();
      setEligibility(res.data);
    } catch (err) {
      console.error('DNA eligibility load error:', err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100">
        <Navbar />
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-500 text-xl animate-pulse">
            Loading Productivity DNA...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />

      <main className="max-w-6xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Productivity DNA
            </h1>
            <p className="text-gray-600 mt-1">
              Your unique behavioral fingerprint — patterns found by AI
            </p>
          </div>
          <button
            onClick={handleTrain}
            disabled={training}
            className="px-5 py-2.5 rounded-xl bg-green-600 text-white font-semibold hover:bg-green-700 disabled:bg-gray-400 transition text-sm"
          >
            {training ? 'Analyzing...' : 'Retrain DNA'}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl
            p-4 mb-6 text-red-700 text-sm">
            {error}
          </div>
        )}

        {loadError && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6 text-amber-800 text-sm flex items-center justify-between gap-3">
            <span>{loadError}</span>
            <button
              onClick={() => {
                setLoading(true);
                loadDNA();
              }}
              className="px-3 py-1.5 rounded-lg bg-amber-100 hover:bg-amber-200 text-amber-900 font-semibold text-xs"
            >
              Retry
            </button>
          </div>
        )}

        {!dna && !loading ? (
          <div className="bg-white rounded-xl shadow p-8 text-center">
            <p className="text-gray-700 font-medium">DNA results are temporarily unavailable.</p>
            <p className="text-gray-500 text-sm mt-2">Try reloading this page in a few seconds.</p>
          </div>
        ) : !dna?.trained ? (
          <NotTrainedState
            onTrain={handleTrain}
            training={training}
            eligibility={eligibility}
          />
        ) : (
          <>
            {/* Stats row */}
            <div className="grid grid-cols-3 gap-4 mb-8">
              <div className="bg-white rounded-xl shadow p-5 text-center">
                <p className={`text-3xl font-bold ${BADGE_GREEN.accent}`}>
                  {dna.n_clusters}
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  Patterns Found
                </p>
              </div>
              <div className="bg-white rounded-xl shadow p-5 text-center">
                <p className="text-3xl font-bold text-green-600">
                  {dna.n_sessions}
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  Sessions Analyzed
                </p>
              </div>
              <div className="bg-white rounded-xl shadow p-5 text-center">
                <p className={`text-3xl font-bold ${BADGE_GREEN.text}`}>
                  {dna.best_session_length?.avg_minutes
                    ? `${Math.round(dna.best_session_length.avg_minutes)}m`
                    : '—'
                  }
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  Optimal Session
                </p>
              </div>
            </div>

            {/* Cluster profiles */}
            <section className="mb-8">
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                Your Focus Patterns
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {(dna.cluster_profiles || []).map(cluster => (
                  <ClusterCard key={cluster.cluster_id} cluster={cluster} />
                ))}
              </div>
            </section>

            {/* Heatmap */}
            <section className="mb-8">
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                Focus Quality Heatmap
              </h2>
              <div className="bg-white rounded-xl shadow p-6">
                <p className="text-sm text-gray-600 mb-4">
                  Darker green = better focus quality. Gray cells mean no sessions logged for that slot.
                </p>
                <FocusHeatmap heatmapData={dna.heatmap_data || []} />
              </div>
            </section>

            {/* Insights + Worst patterns */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">

              {/* Insights */}
              <section>
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  Personalized Insights
                </h2>
                <div className="space-y-3">
                  {(dna.insights || []).length === 0 ? (
                    <div className="rounded-xl border border-gray-200 bg-white p-4">
                      <p className="text-sm font-medium text-gray-700">
                        Not enough data yet for personalized insights.
                      </p>
                    </div>
                  ) : (
                    (dna.insights || []).map((insight, i) => (
                      <InsightCard key={i} insight={insight} />
                    ))
                  )}
                </div>
              </section>

              {/* Worst patterns + Peak hours */}
              <section>
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  Patterns to Avoid
                </h2>
                <div className="space-y-3 mb-6">
                  {(dna.worst_patterns || []).length === 0 ? (
                    <div className="bg-green-50 border border-green-200
                      rounded-xl p-4 text-center">
                      <span className="text-3xl block mb-2">Excellent</span>
                      <p className="text-green-700 font-medium text-sm">
                        No major negative patterns detected!
                      </p>
                    </div>
                  ) : (
                    (dna.worst_patterns || []).map((pattern, i) => (
                      <WorstPatternCard key={i} pattern={pattern} />
                    ))
                  )}
                </div>

                {/* Peak hours */}
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  Your Peak Focus Hours
                </h2>
                <div className="space-y-2">
                  {(dna.peak_hours || []).length === 0 ? (
                    <p className="text-gray-400 text-sm">
                      Not enough data yet
                    </p>
                  ) : (
                    (dna.peak_hours || []).map((ph, i) => (
                      <PeakHourRow key={i} peakHour={ph} rank={i + 1} />
                    ))
                  )}
                </div>
              </section>

            </div>

            {/* Trained at */}
            <p className="text-xs text-gray-400 text-center">
              DNA last trained:{' '}
              {dna.trained_at
                ? new Date(dna.trained_at).toLocaleString()
                : 'Unknown'
              }
              {' · '}
              <button
                onClick={handleTrain}
                disabled={training}
                className="underline hover:text-gray-600"
              >
                Retrain now
              </button>
            </p>
          </>
        )}

      </main>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────

function NotTrainedState({
  onTrain,
  training,
  eligibility
}: {
  onTrain: () => void;
  training: boolean;
  eligibility: DNAEligibility | null;
}) {
  return (
    <div className="text-center py-20">
      <span className="text-7xl block mb-6">DNA</span>
      <h2 className="text-2xl font-bold text-gray-900 mb-3">
        Your DNA is Ready to Analyze
      </h2>
      <p className="text-gray-500 max-w-md mx-auto mb-8 leading-relaxed">
        Complete at least 5 focus sessions and FocusPilot will analyze
        your behavioral patterns using K-Means clustering to find your
        unique Productivity DNA.
      </p>
      <button
        onClick={onTrain}
        disabled={training}
        className="px-8 py-3 rounded-xl bg-green-600 text-white font-bold text-lg hover:bg-green-700 disabled:bg-gray-400 transition"
      >
        {training ? 'Analyzing your sessions...' : 'Analyze My DNA'}
      </button>

      <div className="mt-6 max-w-xl mx-auto rounded-xl border border-gray-200 bg-white p-4 text-left">
        <p className="text-sm font-semibold text-gray-800 mb-2">DNA Eligibility Check</p>
        {!eligibility ? (
          <p className="text-sm text-gray-500">Checking your session data...</p>
        ) : (
          <>
            <p className="text-sm text-gray-700">
              Completed sessions: <span className="font-semibold">{eligibility.completed_sessions}</span>
              {' / '}
              <span className="font-semibold">{eligibility.required_sessions}</span>
            </p>
            <p className="text-sm text-gray-700 mt-1">
              Total sessions: <span className="font-semibold">{eligibility.total_sessions}</span>
              {' · '}
              Days tracked: <span className="font-semibold">{eligibility.days_of_data}</span>
            </p>
            <p className="text-sm mt-2 font-medium text-gray-800">
              {eligibility.can_train
                ? 'You have enough completed sessions. DNA training should work now.'
                : `You need ${eligibility.remaining_sessions} more completed session${eligibility.remaining_sessions === 1 ? '' : 's'} to train DNA.`}
            </p>
          </>
        )}
      </div>

      <div className="mt-8 grid grid-cols-3 gap-6 max-w-lg mx-auto">
        {[
          { icon: 'search' as IconName, label: 'Finds your focus patterns' },
          { icon: 'clock' as IconName, label: 'Discovers your peak hours' },
          { icon: 'lightbulb' as IconName, label: 'Gives personalized tips' }
        ].map((item, i) => (
          <div key={i} className="text-center">
            <span className="flex justify-center mb-2">
              <AppIcon name={item.icon} className={BADGE_GREEN.accent} size={28} />
            </span>
            <p className="text-xs text-gray-500">{item.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function ClusterCard({ cluster }: { cluster: ClusterProfile }) {
  const qualityColor =
    cluster.quality_score >= 70 ? 'text-green-600' :
    cluster.quality_score >= 40 ? 'text-yellow-600' :
    'text-red-600';

  return (
    <div className="bg-white rounded-xl shadow p-5 border-t-4"
      style={{ borderColor: cluster.color }}>

      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div>
          <p className="font-bold text-gray-900 text-base">
            {cluster.name}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            {cluster.n_sessions} sessions · {cluster.pct_of_total}%
          </p>
        </div>
        <div className="text-right">
          <p className={`text-2xl font-bold ${qualityColor}`}>
            {cluster.quality_score}
          </p>
          <p className="text-xs text-gray-400">quality</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="text-center bg-gray-50 rounded-lg p-2">
          <p className="text-sm font-bold text-gray-800">
            {cluster.avg_focus_score}
          </p>
          <p className="text-xs text-gray-400">focus</p>
        </div>
        <div className="text-center bg-gray-50 rounded-lg p-2">
          <p className="text-sm font-bold text-gray-800">
            {cluster.avg_duration}m
          </p>
          <p className="text-xs text-gray-400">duration</p>
        </div>
        <div className="text-center bg-gray-50 rounded-lg p-2">
          <p className="text-sm font-bold text-gray-800">
            {cluster.avg_distraction}%
          </p>
          <p className="text-xs text-gray-400">distract</p>
        </div>
      </div>

      {/* Quality bar */}
      <div className="w-full bg-gray-100 rounded-full h-1.5 mb-3">
        <div
          className="h-1.5 rounded-full transition-all"
          style={{
            width: `${cluster.quality_score}%`,
            backgroundColor: cluster.color
          }}
        />
      </div>

      {/* Characteristics */}
      <div className="space-y-1">
        {(cluster.characteristics || []).slice(0, 3).map((c, i) => (
          <p key={i} className="text-xs text-gray-500 flex items-center gap-1">
            <span className="text-gray-300">•</span> {c}
          </p>
        ))}
      </div>

    </div>
  );
}

function FocusHeatmap({ heatmapData }: { heatmapData: HeatmapCell[] }) {
  // Build lookup: {hour_day: quality}
  const lookup: Record<string, { quality: number; count: number }> = {};
  heatmapData.forEach(cell => {
    lookup[`${cell.hour}_${cell.day}`] = {
      quality: cell.quality,
      count:   cell.count
    };
  });

  const totalSlots = HOURS.length * DAYS.length;
  const filledSlots = Object.keys(lookup).length;
  const coveragePct = Math.round((filledSlots / totalSlots) * 100);
  const totalSessions = Object.values(lookup).reduce((sum, c) => sum + c.count, 0);
  const qualityValues = Object.values(lookup).map((cell) => cell.quality);
  const minQuality = qualityValues.length ? Math.min(...qualityValues) : 0;
  const maxQuality = qualityValues.length ? Math.max(...qualityValues) : 100;
  const qualityRange = Math.max(1, maxQuality - minQuality);

  const getCellTone = (quality: number | undefined) => {
    if (quality === undefined) {
      return {
        backgroundColor: '#e5e7eb',
        borderColor: '#d1d5db',
        backgroundImage: 'linear-gradient(135deg, rgba(148,163,184,0.18) 25%, transparent 25%, transparent 50%, rgba(148,163,184,0.18) 50%, rgba(148,163,184,0.18) 75%, transparent 75%, transparent)',
        backgroundSize: '8px 8px'
      };
    }

    // Scale colors relative to the user's own quality range so low/high cells
    // remain distinguishable even when absolute scores are tightly clustered.
    const normalized = (quality - minQuality) / qualityRange;

    if (normalized >= 0.75) {
      return { backgroundColor: CHART_GREEN.heatmap[3], borderColor: CHART_GREEN.heatmap[3] };
    }
    if (normalized >= 0.5) {
      return { backgroundColor: CHART_GREEN.heatmap[2], borderColor: CHART_GREEN.heatmap[2] };
    }
    if (normalized >= 0.25) {
      return { backgroundColor: CHART_GREEN.heatmap[1], borderColor: CHART_GREEN.heatmap[1] };
    }

    return { backgroundColor: CHART_GREEN.heatmap[0], borderColor: CHART_GREEN.heatmap[0] };
  };

  return (
    <div className="overflow-x-auto">
      <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-700">
        Heatmap coverage: <span className="font-semibold">{filledSlots}/{totalSlots}</span> slots ({coveragePct}%)
        {' · '}
        Sessions represented: <span className="font-semibold">{totalSessions}</span>
      </div>

      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="w-12 text-gray-400 font-normal text-left pb-2">
              Hour
            </th>
            {DAYS.map(d => (
              <th key={d}
                className="text-gray-400 font-normal text-center pb-2 px-1">
                {d}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {HOURS.map(hour => (
            <tr key={hour}>
              <td className="text-gray-400 pr-2 py-0.5 text-right">
                {hour < 12
                  ? `${hour}am`
                  : hour === 12
                  ? '12pm'
                  : `${hour - 12}pm`
                }
              </td>
              {DAYS.map((_, dayIdx) => {
                const cell = lookup[`${hour}_${dayIdx}`];
                const tone = getCellTone(cell?.quality);
                return (
                  <td key={dayIdx} className="px-1 py-0.5">
                    <div
                      className="w-full h-6 rounded border cursor-pointer
                        transition-opacity hover:opacity-85"
                      style={{
                        ...tone,
                        minWidth: '28px'
                      }}
                      title={
                        cell
                          ? `${cell.quality}% quality · ${cell.count} sessions`
                          : 'No data'
                      }
                    />
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Legend */}
      <div className="flex items-center gap-3 mt-4 justify-end">
        <span className="text-xs text-gray-500">No data</span>
        <div
          className="w-5 h-5 rounded border"
          style={{
            backgroundColor: '#e5e7eb',
            borderColor: '#d1d5db',
            backgroundImage: 'linear-gradient(135deg, rgba(148,163,184,0.18) 25%, transparent 25%, transparent 50%, rgba(148,163,184,0.18) 50%, rgba(148,163,184,0.18) 75%, transparent 75%, transparent)',
            backgroundSize: '8px 8px'
          }}
        />
        <span className="text-xs text-gray-500">Less focus</span>
        {CHART_GREEN.heatmap.map((c, i) => (
          <div
            key={i}
            className="w-5 h-5 rounded border"
            style={{ backgroundColor: c, borderColor: c }}
          />
        ))}
        <span className="text-xs text-gray-500">More focus</span>
      </div>
    </div>
  );
}

function InsightCard({ insight }: { insight: DNAInsight }) {
  const config = {
    success: { bg: 'bg-green-50  border-green-200',  text: 'text-green-800'  },
    info:    { bg: 'bg-green-50  border-green-200',  text: 'text-green-800'  },
    warning: { bg: 'bg-yellow-50 border-yellow-200', text: 'text-yellow-800' }
  };

  const c = config[insight.type] || config.info;

  return (
    <div className={`rounded-xl border p-4 ${c.bg}`}>
      <div className="flex items-start gap-3">
        <AppIcon
          name={normalizeIconName(insight.icon)}
          className="shrink-0 text-gray-700"
          size={20}
        />
        <div>
          <p className={`font-semibold text-base leading-tight ${c.text}`}>
            {insight.title}
          </p>
          <p className="text-sm font-medium text-gray-700 mt-1.5 leading-relaxed">
            {insight.body}
          </p>
        </div>
      </div>
    </div>
  );
}

function WorstPatternCard({ pattern }: { pattern: any }) {
  const severityColors: Record<string, string> = {
    high:   'bg-red-50    border-red-200    text-red-800',
    medium: 'bg-orange-50 border-orange-200 text-orange-800',
    low:    'bg-yellow-50 border-yellow-200 text-yellow-800'
  };

  const c = severityColors[pattern.severity] || severityColors.medium;

  return (
    <div className={`rounded-xl border p-4 ${c}`}>
      <div className="flex items-start gap-3">
        <AppIcon
          name={normalizeIconName(pattern.icon)}
          className="shrink-0"
          size={18}
        />
        <div>
          <p className="font-semibold text-sm">{pattern.pattern}</p>
          <p className="text-xs opacity-80 mt-0.5 leading-relaxed">
            {pattern.description}
          </p>
        </div>
      </div>
    </div>
  );
}

function PeakHourRow({
  peakHour,
  rank
}: {
  peakHour: any;
  rank: number;
}) {
  const medals: IconName[] = ['medal-gold', 'medal-silver', 'medal-bronze'];

  return (
    <div className="bg-white rounded-xl border border-gray-100
      shadow-sm p-4 flex items-center gap-4">
      <AppIcon name={medals[rank - 1] || 'clock'} className={BADGE_GREEN.accent} size={22} />
      <div className="flex-1">
        <p className="font-bold text-gray-900 text-sm">
          {peakHour.hour_label}
        </p>
        <p className="text-xs text-gray-500">
          {peakHour.session_count} high-quality sessions at this hour
        </p>
      </div>
      <div className="text-right">
        <p className={`text-lg font-bold ${BADGE_GREEN.accent}`}>
          {peakHour.quality}
        </p>
        <p className="text-xs text-gray-400">quality</p>
      </div>
    </div>
  );
}

export default ProductivityDNA;
