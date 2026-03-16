import React, { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { pipelineAPI } from '../api/client';

const COMPONENT_CONFIG: Record<string, { icon: string; label: string }> = {
  orchestrator: { icon: '', label: 'Orchestrator' },
  ml_model: { icon: '', label: 'ML Model' },
  active_session: { icon: '', label: 'Session' },
  site_blocker: { icon: '', label: 'Site Blocker' }
};

const STATUS_COLORS: Record<string, string> = {
  healthy: 'bg-green-100  text-green-700  border-green-200',
  active: 'bg-green-100  text-green-700  border-green-200',
  blocking: 'bg-red-100    text-red-700    border-red-200',
  down: 'bg-red-100    text-red-700    border-red-200',
  not_trained: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  idle: 'bg-gray-100   text-gray-600   border-gray-200',
  degraded: 'bg-orange-100 text-orange-700 border-orange-200'
};

function AgentDashboard() {
  const [health, setHealth] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  useEffect(() => {
    loadAll();
    const interval = setInterval(() => {
      loadAll();
      setLastRefresh(new Date());
    }, 30_000);
    return () => clearInterval(interval);
  }, []);

  const loadAll = async () => {
    try {
      const [healthRes, summaryRes] = await Promise.all([
        pipelineAPI.getHealth(),
        pipelineAPI.getSummary()
      ]);
      setHealth(healthRes.data);
      setSummary(summaryRes.data);
    } catch (error) {
      console.error('Dashboard load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRunNow = async () => {
    setRunning(true);
    try {
      await pipelineAPI.runNow();
      await loadAll();
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100">
        <Navbar />
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-500 text-xl animate-pulse">
            Loading agent dashboard...
          </p>
        </div>
      </div>
    );
  }

  // Format risk timeline for chart
  const riskTimeline = (summary?.risk_timeline || []).map((r: any) => ({
    time: new Date(r.assessed_at).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    }),
    risk: Math.round(r.risk_score * 100),
    score: r.risk_score
  }));

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900"> Agent Dashboard</h1>
            <p className="text-gray-500 text-sm mt-1">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </p>
          </div>
          <button
            onClick={handleRunNow}
            disabled={running}
            className="px-5 py-2.5 bg-gray-900 text-white rounded-xl
              font-semibold hover:bg-gray-800 disabled:bg-gray-400
              transition text-sm"
          >
            {running ? ' Running...' : ' Run Pipeline Now'}
          </button>
        </div>

        {/* Overall status banner */}
        <div
          className={`rounded-xl border p-4 mb-8 flex items-center gap-4
          ${health?.overall_status === 'healthy'
            ? 'bg-green-50 border-green-200'
            : 'bg-orange-50 border-orange-200'
          }`}
        >
          <span className="text-3xl">{health?.overall_status === 'healthy' ? '' : ''}</span>
          <div>
            <p
              className={`font-bold text-lg ${
                health?.overall_status === 'healthy' ? 'text-green-800' : 'text-orange-800'
              }`}
            >
              System {health?.overall_status === 'healthy' ? 'Healthy' : 'Degraded'}
            </p>
            <p
              className={`text-sm ${
                health?.overall_status === 'healthy' ? 'text-green-600' : 'text-orange-600'
              }`}
            >
              Agent state: <strong>{health?.agent_state}</strong>
              {health?.last_risk_score != null &&
                `  Last risk: ${Math.round(health.last_risk_score * 100)}%`}
              {health?.last_cycle &&
                `  Last cycle: ${new Date(health.last_cycle).toLocaleTimeString()}`}
            </p>
          </div>
        </div>

        {/* Component health grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {Object.entries(health?.components || {}).map(([key, comp]: [string, any]) => {
            const cfg = COMPONENT_CONFIG[key] || { icon: '', label: key };
            const colors = STATUS_COLORS[comp.status] || STATUS_COLORS.idle;

            return (
              <div key={key} className={`bg-white rounded-xl border p-4 ${colors}`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">{cfg.icon}</span>
                  <p className="font-semibold text-sm">{cfg.label}</p>
                </div>
                <p className="text-xs capitalize font-medium">{comp.status.replace(/_/g, ' ')}</p>
                <p className="text-xs opacity-75 mt-0.5 leading-tight">{comp.description}</p>
              </div>
            );
          })}
        </div>

        {/* Today's stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            icon=""
            label="Cycles Today"
            value={summary?.total_cycles || 0}
            color="text-blue-600"
          />
          <StatCard
            icon=""
            label="Interventions"
            value={health?.today?.interventions || 0}
            color="text-orange-600"
          />
          <StatCard
            icon=""
            label="Actions Taken"
            value={health?.today?.autonomous_actions || 0}
            color="text-purple-600"
          />
          <StatCard
            icon=""
            label="Peak Risk Today"
            value={`${Math.round((summary?.peak_risk_today || 0) * 100)}%`}
            color="text-red-600"
          />
        </div>

        {/* Risk timeline chart */}
        <div className="bg-white rounded-xl shadow p-6 mb-8">
          <h2 className="text-lg font-bold text-gray-900 mb-4"> Risk Timeline Today</h2>

          {riskTimeline.length === 0 ? (
            <div className="text-center py-12">
              <span className="text-4xl block mb-3"></span>
              <p className="text-gray-500">No risk data yet. Start a session to begin monitoring.</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={riskTimeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 11, fill: '#9ca3af' }}
                  interval="preserveStartEnd"
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 11, fill: '#9ca3af' }}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip
                  formatter={(value: any) => [`${value}%`, 'Risk Score']}
                  contentStyle={{
                    borderRadius: '8px',
                    border: '1px solid #e5e7eb',
                    fontSize: '12px'
                  }}
                />
                <ReferenceLine
                  y={60}
                  stroke="#eab308"
                  strokeDasharray="4 4"
                  label={{
                    value: 'At Risk',
                    position: 'right',
                    fontSize: 10,
                    fill: '#eab308'
                  }}
                />
                <ReferenceLine
                  y={75}
                  stroke="#ef4444"
                  strokeDasharray="4 4"
                  label={{
                    value: 'Critical',
                    position: 'right',
                    fontSize: 10,
                    fill: '#ef4444'
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="risk"
                  stroke="#6366f1"
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 5, fill: '#6366f1' }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Bottom grid: Events + Interventions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Live event stream */}
          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4"> Live Event Stream</h2>
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {(summary?.events_today || []).length === 0 ? (
                <p className="text-gray-400 text-sm text-center py-8">No events yet today</p>
              ) : (
                (summary?.events_today || []).slice(0, 15).map((event: any, i: number) => (
                  <EventRow key={i} event={event} />
                ))
              )}
            </div>
          </div>

          {/* Today's interventions */}
          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4"> Today's Interventions</h2>
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {(summary?.interventions || []).length === 0 ? (
                <div className="text-center py-8">
                  <span className="text-3xl block mb-2"></span>
                  <p className="text-gray-400 text-sm">No interventions today. Great focus!</p>
                </div>
              ) : (
                (summary?.interventions || []).map((iv: any, i: number) => (
                  <InterventionRow key={i} intervention={iv} />
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  color
}: {
  icon: string;
  label: string;
  value: any;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl shadow p-5">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xl">{icon}</span>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function EventRow({ event }: { event: any }) {
  const typeIcons: Record<string, string> = {
    pipeline_cycle: '',
    alert_warning: '',
    alert_intervention: '',
    alert_recovery: '',
    monitoring_cycle: ''
  };

  const icon = typeIcons[event.event_type] || '';

  return (
    <div className="flex items-start gap-3 py-2 border-b border-gray-50 last:border-0">
      <span className="text-base mt-0.5">{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-center">
          <p className="text-xs font-medium text-gray-700 capitalize truncate">
            {event.event_type.replace(/_/g, ' ')}
          </p>
          <p className="text-xs text-gray-400 shrink-0 ml-2">
            {new Date(event.created_at).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit'
            })}
          </p>
        </div>
        {event.event_data?.risk_score != null && (
          <p className="text-xs text-gray-500">
            Risk: {Math.round(event.event_data.risk_score * 100)}%
            {event.state_after && `  ${event.state_after}`}
          </p>
        )}
      </div>
    </div>
  );
}

function InterventionRow({ intervention }: { intervention: any }) {
  const outcomeColors: Record<string, string> = {
    success: 'text-green-600',
    ignored: 'text-gray-400',
    partial: 'text-yellow-600',
    pending: 'text-blue-600'
  };

  return (
    <div className="flex items-start gap-3 py-2 border-b border-gray-50 last:border-0">
      <span className="text-base mt-0.5"></span>
      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-center">
          <p className="text-xs font-medium text-gray-700 capitalize truncate">
            {(intervention.intervention_type || '').replace(/_/g, ' ')}
          </p>
          <p
            className={`text-xs font-semibold shrink-0 ml-2 capitalize
            ${outcomeColors[intervention.outcome] || 'text-gray-500'}`}
          >
            {intervention.outcome}
          </p>
        </div>
        <p className="text-xs text-gray-500">
          Risk: {Math.round((intervention.risk_score_at_trigger || 0) * 100)}%
          {'  '}
          {new Date(intervention.created_at).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </p>
      </div>
    </div>
  );
}

export default AgentDashboard;
