// src/pages/AgentStatus.tsx
import React, { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import { agentAPI } from '../api/client';
import AppIcon, { IconName } from '../components/AppIcon';

const STATE_CONFIG = {
  idle:        { color: 'bg-gray-100  text-gray-700',   icon: 'event' as IconName,        label: 'Idle'        },
  active:      { color: 'bg-green-100 text-green-700',  icon: 'activity' as IconName,     label: 'Active'       },
  at_risk:     { color: 'bg-yellow-100 text-yellow-700',icon: 'warning' as IconName,      label: 'At Risk'     },
  intervening: { color: 'bg-red-100   text-red-700',    icon: 'intervention' as IconName, label: 'Intervening'  },
  paused:      { color: 'bg-green-100 text-green-700',  icon: 'pause' as IconName,        label: 'Paused'       }
};

const stripEmoji = (value: string | undefined | null): string => {
  if (!value) return '';
  return value
    .replace(/[\u2600-\u27BF]|[\uD83C-\uDBFF][\uDC00-\uDFFF]/g, '')
    .trim();
};

function AgentStatus() {
  const [status,        setStatus]        = useState<any>(null);
  const [events,        setEvents]        = useState<any[]>([]);
  const [interventions, setInterventions] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [loading,       setLoading]       = useState(true);
  const [cycling,       setCycling]       = useState(false);
  const [error,         setError]         = useState('');
  const [activeTab,     setActiveTab]     = useState<'events' | 'interventions'>('events');

  useEffect(() => {
    loadAll();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadAll, 30_000);
    return () => clearInterval(interval);
  }, []);

  const loadAll = async () => {
    try {
      setError('');
      const [statusRes, eventsRes, interventionsRes, notifRes] =
        await Promise.all([
          agentAPI.getStatus(),
          agentAPI.getEvents(15),
          agentAPI.getInterventions(10),
          agentAPI.getNotifications()
        ]);

      setStatus(statusRes.data);
      setEvents(eventsRes.data.events);
      setInterventions(interventionsRes.data.interventions);
      setNotifications(notifRes.data.notifications);
    } catch (err: any) {
      console.error('Error loading agent data:', err);
      setError(err?.response?.data?.detail || err?.message || 'Could not load agent data.');
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerCycle = async () => {
    setCycling(true);
    try {
      setError('');
      await agentAPI.triggerCycle();
      await loadAll();
    } catch (err: any) {
      console.error('Error triggering cycle:', err);
      setError(err?.response?.data?.detail || err?.message || 'Could not trigger cycle.');
    } finally {
      setCycling(false);
    }
  };

  const handleTogglePause = async () => {
    try {
      setError('');
      if (status?.state === 'paused') {
        await agentAPI.resume();
      } else {
        await agentAPI.pause();
      }
      await loadAll();
    } catch (err: any) {
      console.error('Error toggling pause state:', err);
      setError(err?.response?.data?.detail || err?.message || 'Could not update agent state.');
    }
  };

  const handleMarkRead = async () => {
    try {
      setError('');
      await agentAPI.markNotificationsRead();
      setNotifications([]);
    } catch (err: any) {
      console.error('Error marking notifications read:', err);
      setError(err?.response?.data?.detail || err?.message || 'Could not mark notifications as read.');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100">
        <Navbar />
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-500 text-xl animate-pulse">
            Loading agent status...
          </p>
        </div>
      </div>
    );
  }

  const stateConfig = STATE_CONFIG[status?.state as keyof typeof STATE_CONFIG]
    || STATE_CONFIG.idle;

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />

      <main className="max-w-5xl mx-auto px-4 py-8">

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Agent Control Center
            </h1>
            <p className="text-gray-600 mt-1">
              Monitor and control your AI productivity agent
            </p>
          </div>

          {/* Control buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleTriggerCycle}
              disabled={cycling}
              className="px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:bg-gray-400 transition text-sm"
            >
              {cycling ? 'Running...' : 'Run Cycle Now'}
            </button>
            <button
              onClick={handleTogglePause}
              className={`px-4 py-2 rounded-lg font-medium transition text-sm ${
                status?.state === 'paused'
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-amber-500 text-white hover:bg-amber-600'
              }`}
            >
              {status?.state === 'paused' ? 'Resume Agent' : 'Pause Agent'}
            </button>
          </div>
        </div>

        {/* Notifications banner */}
        {notifications.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="font-semibold text-yellow-800 mb-2">
                  {notifications.length} New Notification
                  {notifications.length > 1 ? 's' : ''}
                </p>
                <div className="space-y-2 max-h-64 overflow-y-auto pr-2">
                {notifications.map((n: any) => (
                  <div key={n.id} className="border-b border-yellow-100 pb-2 last:border-b-0 last:pb-0">
                    <p className="font-medium text-yellow-900 text-sm">
                      {stripEmoji(n.title)}
                    </p>
                    <p className="text-yellow-700 text-sm">{stripEmoji(n.message)}</p>
                  </div>
                ))}
                </div>
              </div>
              <button
                onClick={handleMarkRead}
                className="text-xs text-yellow-600 hover:underline ml-4"
              >
                Mark all read
              </button>
            </div>
          </div>
        )}

        {/* Status cards row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">

          {/* Agent state */}
          <div className="bg-white rounded-xl shadow p-5 col-span-2">
            <p className="text-sm text-gray-500 mb-2">Agent State</p>
            <div className="flex items-center gap-3">
              <AppIcon name={stateConfig.icon} className="text-gray-600" size={30} />
              <div>
                <span className={`px-3 py-1 rounded-full text-sm font-bold ${stateConfig.color}`}>
                  {stateConfig.label}
                </span>
                <p className="text-xs text-gray-500 mt-1">
                  {status?.state === 'idle'        && 'Waiting for active session'}
                  {status?.state === 'active'      && 'Session running. Risk is low.'}
                  {status?.state === 'at_risk'     && 'Risk rising. Monitoring closely.'}
                  {status?.state === 'intervening' && 'High risk. Taking action.'}
                  {status?.state === 'paused'      && 'Agent paused by user.'}
                </p>
              </div>
            </div>
          </div>

          {/* Risk score */}
          <div className="bg-white rounded-xl shadow p-5">
            <p className="text-sm text-gray-500 mb-1">Last Risk Score</p>
            <p className="text-3xl font-bold text-gray-900">
              {status?.last_risk_score != null
                ? `${Math.round(status.last_risk_score * 100)}%`
                : '—'
              }
            </p>
            <p className="text-xs text-gray-400 mt-1">
              {status?.last_cycle
                ? new Date(status.last_cycle).toLocaleTimeString()
                : 'No cycles yet'
              }
            </p>
          </div>

          {/* Cycle count */}
          <div className="bg-white rounded-xl shadow p-5">
            <p className="text-sm text-gray-500 mb-1">Total Cycles</p>
            <p className="text-3xl font-bold text-gray-900">
              {status?.cycle_count || 0}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Since agent started
            </p>
          </div>
        </div>

        {/* Orchestrator status */}
        <div className={`rounded-xl p-4 mb-8 flex items-center gap-3 ${
          status?.orchestrator_running
            ? 'bg-green-50 border border-green-200'
            : 'bg-red-50 border border-red-200'
        }`}>
          <AppIcon
            name={status?.orchestrator_running ? 'check-circle' : 'x-circle'}
            className={status?.orchestrator_running ? 'text-green-700' : 'text-red-700'}
            size={22}
          />
          <div>
            <p className={`font-semibold ${
              status?.orchestrator_running
                ? 'text-green-800'
                : 'text-red-800'
            }`}>
              Orchestrator {status?.orchestrator_running ? 'Running' : 'Stopped'}
            </p>
            <p className={`text-sm ${
              status?.orchestrator_running
                ? 'text-green-600'
                : 'text-red-600'
            }`}>
              {status?.orchestrator_running
                ? 'Agent checks your focus every 60 seconds automatically'
                : 'Agent is not running. Restart the backend server.'
              }
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 mb-6">
          <button
            onClick={() => setActiveTab('events')}
            className={`px-6 py-3 font-semibold text-sm transition ${
              activeTab === 'events'
                ? 'border-b-2 border-green-600 text-green-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Agent Events ({events.length})
          </button>
          <button
            onClick={() => setActiveTab('interventions')}
            className={`px-6 py-3 font-semibold text-sm transition ${
              activeTab === 'interventions'
                ? 'border-b-2 border-green-600 text-green-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Interventions ({interventions.length})
          </button>
        </div>

        {/* Events tab */}
        {activeTab === 'events' && (
          <div className="space-y-3">
            {events.length === 0 ? (
              <div className="text-center py-16">
                <div className="flex justify-center mb-4">
                  <AppIcon name="event" className="text-gray-300" size={42} />
                </div>
                <p className="text-gray-500 text-lg">No events yet.</p>
                <p className="text-gray-400 text-sm mt-1">
                  Start a session and the agent will begin monitoring.
                </p>
              </div>
            ) : (
              events.map((event: any) => (
                <EventCard key={event.id} event={event} />
              ))
            )}
          </div>
        )}

        {/* Interventions tab */}
        {activeTab === 'interventions' && (
          <div className="space-y-3">
            {interventions.length === 0 ? (
              <div className="text-center py-16">
                <div className="flex justify-center mb-4">
                  <AppIcon name="check-circle" className="text-gray-300" size={42} />
                </div>
                <p className="text-gray-500 text-lg">No interventions yet.</p>
                <p className="text-gray-400 text-sm mt-1">
                  Great! The agent has not needed to intervene.
                </p>
              </div>
            ) : (
              interventions.map((item: any) => (
                <InterventionCard key={item.id} intervention={item} />
              ))
            )}
          </div>
        )}

      </main>
    </div>
  );
}

function EventCard({ event }: { event: any }) {
  const typeIcons: Record<string, IconName> = {
    monitoring_cycle: 'cycle',
    alert_warning: 'warning',
    alert_intervention: 'intervention',
    alert_recovery: 'recovery',
  };

  const icon = typeIcons[event.event_type] || 'event';

  return (
    <div className="bg-white rounded-lg shadow-sm p-4 flex items-start gap-4">
      <AppIcon name={icon} className="text-gray-400 mt-0.5" size={16} />
      <div className="flex-1">
        <div className="flex justify-between items-start">
          <p className="font-semibold text-gray-900 capitalize text-sm">
            {event.event_type.replace(/_/g, ' ')}
          </p>
          <p className="text-xs text-gray-400">
            {new Date(event.created_at).toLocaleTimeString()}
          </p>
        </div>
        {event.event_data?.risk_score != null && (
          <p className="text-sm text-gray-600 mt-0.5">
            Risk: <span className="font-medium">
              {Math.round(event.event_data.risk_score * 100)}%
            </span>
            {' '}— {event.state_after}
          </p>
        )}
        {event.event_data?.signals?.length > 0 && (
          <p className="text-xs text-gray-400 mt-1">
            {stripEmoji(event.event_data.signals[0])}
          </p>
        )}
      </div>
    </div>
  );
}

function InterventionCard({ intervention }: { intervention: any }) {
  const outcomeColors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-700',
    resolved: 'bg-green-100  text-green-700',
    ignored: 'bg-gray-100   text-gray-600',
  };

  return (
    <div className="bg-white rounded-lg shadow-sm p-4">
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <AppIcon name="warning" className="text-gray-400" size={14} />
          <p className="font-semibold text-gray-900 capitalize text-sm">
            {intervention.intervention_type?.replace(/_/g, ' ')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            outcomeColors[intervention.outcome] || outcomeColors.pending
          }`}>
            {intervention.outcome}
          </span>
          <p className="text-xs text-gray-400">
            {new Date(intervention.created_at).toLocaleTimeString()}
          </p>
        </div>
      </div>
      <p className="text-sm text-gray-600">
        Risk at trigger:{' '}
        <span className="font-medium text-red-600">
          {Math.round((intervention.risk_score_at_trigger || 0) * 100)}%
        </span>
      </p>
      {intervention.trigger_reason && (
        <p className="text-xs text-gray-400 mt-1">
          {stripEmoji(intervention.trigger_reason)}
        </p>
      )}
    </div>
  );
}

export default AgentStatus;
