import React, { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';
import { rlAPI } from '../api/client';
import { RLEpisode, LearningStats, PolicyEntry } from '../types/rl';

type IconName =
  | 'brain'
  | 'target'
  | 'check'
  | 'star'
  | 'flame'
  | 'history'
  | 'trend'
  | 'map';

function Icon({
  name,
  className = 'w-5 h-5',
  strokeWidth = 1.8
}: {
  name: IconName;
  className?: string;
  strokeWidth?: number;
}) {
  const commonProps = {
    viewBox: '0 0 24 24',
    fill: 'none',
    xmlns: 'http://www.w3.org/2000/svg',
    className,
    'aria-hidden': true,
    stroke: 'currentColor',
    strokeWidth,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const
  };

  switch (name) {
    case 'brain':
      return (
        <svg {...commonProps}>
          <path d="M9 6a3 3 0 0 1 6 0v1a3 3 0 1 1 2 5.2V14a3 3 0 0 1-3 3h-1" />
          <path d="M15 6a3 3 0 0 0-6 0v1a3 3 0 1 0-2 5.2V14a3 3 0 0 0 3 3h1" />
          <path d="M12 4v16" />
        </svg>
      );
    case 'target':
      return (
        <svg {...commonProps}>
          <circle cx="12" cy="12" r="8" />
          <circle cx="12" cy="12" r="4" />
          <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
        </svg>
      );
    case 'check':
      return (
        <svg {...commonProps}>
          <path d="M20 6 9 17l-5-5" />
        </svg>
      );
    case 'star':
      return (
        <svg {...commonProps}>
          <path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.8 1-6.1-4.4-4.3 6.1-.9L12 3z" />
        </svg>
      );
    case 'flame':
      return (
        <svg {...commonProps}>
          <path d="M12 3c1.5 2.2 3 4 3 6a3 3 0 1 1-6 0c0-1.2.4-2.3 1-3.5C7.6 7.2 6 9.7 6 12.5A6 6 0 0 0 18 13c0-4-2.7-7.2-6-10z" />
        </svg>
      );
    case 'history':
      return (
        <svg {...commonProps}>
          <path d="M3 12a9 9 0 1 0 2.6-6.4" />
          <path d="M3 4v4h4" />
          <path d="M12 7v5l3 2" />
        </svg>
      );
    case 'trend':
      return (
        <svg {...commonProps}>
          <path d="M3 17h18" />
          <path d="m5 14 4-4 3 3 6-6" />
        </svg>
      );
    case 'map':
      return (
        <svg {...commonProps}>
          <path d="M9 5 3 7.5v11L9 16l6 2.5 6-2.5V5.5L15 8 9 5z" />
          <path d="M9 5v11" />
          <path d="M15 8v10.5" />
        </svg>
      );
    default:
      return null;
  }
}

const ACTION_LABELS: Record<string, string> = {
  send_warning: 'Send Warning',
  block_sites: 'Block Sites',
  start_break: 'Start Break',
  send_motivation: 'Send Motivation',
  do_nothing: 'Do Nothing'
};

const ACTION_COLORS: Record<string, string> = {
  send_warning: '#f59e0b',
  block_sites: '#ef4444',
  start_break: '#10b981',
  send_motivation: '#6366f1',
  do_nothing: '#9ca3af'
};

const OUTCOME_CONFIG: Record<
  string,
  {
    label: string;
    color: string;
    bg: string;
  }
> = {
  focused_more: {
    label: 'Focused More',
    color: 'text-green-700',
    bg: 'bg-green-100'
  },
  no_change: {
    label: 'No Change',
    color: 'text-gray-600',
    bg: 'bg-gray-100'
  },
  distracted_more: {
    label: 'Distracted More',
    color: 'text-orange-700',
    bg: 'bg-orange-100'
  },
  session_ended: {
    label: 'Session Ended',
    color: 'text-red-700',
    bg: 'bg-red-100'
  }
};

function InterventionHistory() {
  const [episodes, setEpisodes] = useState<RLEpisode[]>([]);
  const [stats, setStats] = useState<LearningStats | null>(null);
  const [policy, setPolicy] = useState<PolicyEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'history' | 'learning' | 'policy'>('history');

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [epRes, statsRes, policyRes] = await Promise.all([
        rlAPI.getEpisodes(),
        rlAPI.getLearningStats(),
        rlAPI.getPolicy()
      ]);
      setEpisodes(epRes.data.episodes || []);
      setStats(statsRes.data);
      setPolicy(policyRes.data.policy || []);
    } catch (err) {
      console.error('RL load error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100">
        <Navbar />
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-500 animate-pulse text-xl">Loading intervention history...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Icon name="brain" className="w-8 h-8 text-gray-900" />
            Intervention History
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Every decision the Q-learning agent made and what it learned
          </p>
        </div>

        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard
              icon={<Icon name="target" className="w-5 h-5" />}
              label="Total Interventions"
              value={String(stats.total_episodes)}
              color="text-indigo-600"
            />
            <StatCard
              icon={<Icon name="check" className="w-5 h-5" />}
              label="Success Rate"
              value={`${stats.success_rate}%`}
              color={
                stats.success_rate >= 60
                  ? 'text-green-600'
                  : stats.success_rate >= 40
                    ? 'text-yellow-600'
                    : 'text-red-600'
              }
            />
            <StatCard
              icon={<Icon name="star" className="w-5 h-5" />}
              label="Avg Reward"
              value={String(stats.avg_reward)}
              color={
                stats.avg_reward >= 0.5
                  ? 'text-green-600'
                  : stats.avg_reward >= 0
                    ? 'text-yellow-600'
                    : 'text-red-600'
              }
            />
            <StatCard
              icon={<Icon name="flame" className="w-5 h-5" />}
              label="Most Used Action"
              value={
                ACTION_LABELS[stats.most_used_action] ||
                stats.most_used_action ||
                ' - '
              }
              color="text-orange-600"
            />
          </div>
        )}

        <div className="flex gap-1 bg-white rounded-xl shadow-sm p-1 mb-8 w-fit">
          {([
            ['history', 'History', 'history'],
            ['learning', 'Learning', 'trend'],
            ['policy', 'Policy', 'map']
          ] as const).map(([key, label, icon]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${
                tab === key
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Icon
                name={icon as IconName}
                className="w-4 h-4"
                strokeWidth={2}
              />
              {label}
            </button>
          ))}
        </div>

        {tab === 'history' && (
          <div className="bg-white rounded-xl shadow">
            <div className="p-6 border-b border-gray-100">
              <h2 className="font-bold text-gray-900">Intervention Log</h2>
              <p className="text-sm text-gray-500 mt-1">{episodes.length} interventions recorded</p>
            </div>

            {episodes.length === 0 ? (
              <EmptyState
                icon={<Icon name="brain" className="w-12 h-12 text-gray-400" />}
                title="No interventions yet"
                body="The agent will log interventions as it monitors your sessions"
              />
            ) : (
              <div className="divide-y divide-gray-50">
                {episodes.map((ep, i) => (
                  <EpisodeRow key={ep.id} episode={ep} index={i} />
                ))}
              </div>
            )}
          </div>
        )}

        {tab === 'learning' && stats && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow p-6">
              <h2 className="font-bold text-gray-900 mb-1 flex items-center gap-2">
                <Icon name="trend" className="w-5 h-5" />
                Reward Trend
              </h2>
              <p className="text-sm text-gray-500 mb-4">
                Rolling average reward over time. Upward means the agent is learning better interventions.
              </p>

              {stats.reward_trend.length === 0 ? (
                <EmptyState
                  icon={<Icon name="trend" className="w-12 h-12 text-gray-400" />}
                  title="Not enough data yet"
                  body="Complete more sessions to see the learning curve"
                />
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={stats.reward_trend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="episode"
                      tick={{ fontSize: 11, fill: '#9ca3af' }}
                      label={{
                        value: 'Episode',
                        position: 'insideBottom',
                        offset: -2,
                        fontSize: 11,
                        fill: '#9ca3af'
                      }}
                    />
                    <YAxis
                      domain={[-1, 1]}
                      tick={{ fontSize: 11, fill: '#9ca3af' }}
                      tickFormatter={(v: number) => v.toFixed(1)}
                    />
                    <Tooltip
                      formatter={(v) => [Number(v).toFixed(3), 'Avg Reward']}
                      contentStyle={{
                        borderRadius: '8px',
                        border: '1px solid #e5e7eb',
                        fontSize: '12px'
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey={() => 0}
                      stroke="#e5e7eb"
                      strokeDasharray="4 4"
                      dot={false}
                      strokeWidth={1}
                    />
                    <Line
                      type="monotone"
                      dataKey="avg_reward"
                      stroke="#6366f1"
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="bg-white rounded-xl shadow p-6">
              <h2 className="font-bold text-gray-900 mb-1 flex items-center gap-2">
                <Icon name="target" className="w-5 h-5" />
                Action Distribution
              </h2>
              <p className="text-sm text-gray-500 mb-4">How often the agent chose each action</p>

              {Object.keys(stats.action_counts).length === 0 ? (
                <EmptyState
                  icon={<Icon name="target" className="w-12 h-12 text-gray-400" />}
                  title="No actions yet"
                  body="Actions will appear as the agent intervenes"
                />
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart
                    data={Object.entries(stats.action_counts).map(([action, count]) => ({
                      action: ACTION_LABELS[action] || action,
                      count,
                      color: ACTION_COLORS[action] || '#9ca3af'
                    }))}
                    barSize={36}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="action" tick={{ fontSize: 10, fill: '#9ca3af' }} />
                    <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} />
                    <Tooltip
                      contentStyle={{
                        borderRadius: '8px',
                        border: '1px solid #e5e7eb',
                        fontSize: '12px'
                      }}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {Object.entries(stats.action_counts).map(([action], i) => (
                        <Cell key={i} fill={ACTION_COLORS[action] || '#9ca3af'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        )}

        {tab === 'policy' && (
          <div className="bg-white rounded-xl shadow">
            <div className="p-6 border-b border-gray-100">
              <h2 className="font-bold text-gray-900">Learned Policy</h2>
              <p className="text-sm text-gray-500 mt-1">
                The agent's best known action for each state it has visited
              </p>
            </div>

            {policy.length === 0 ? (
              <EmptyState
                icon={<Icon name="map" className="w-12 h-12 text-gray-400" />}
                title="Policy not yet learned"
                body="The agent builds its policy as it completes more interventions"
              />
            ) : (
              <div className="divide-y divide-gray-50">
                {policy.map((entry, i) => (
                  <PolicyRow key={i} entry={entry} rank={i + 1} />
                ))}
              </div>
            )}
          </div>
        )}
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
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl shadow p-5">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-gray-600">{icon}</span>
        <p className="text-xs text-gray-500">{label}</p>
      </div>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function EpisodeRow({
  episode,
  index
}: {
  episode: RLEpisode;
  index: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const outcome = episode.outcome
    ? OUTCOME_CONFIG[episode.outcome] || {
        label: episode.outcome,
        color: 'text-gray-600',
        bg: 'bg-gray-100'
      }
    : null;

  const actionColor = ACTION_COLORS[episode.action] || '#9ca3af';

  return (
    <div
      className="px-6 py-4 hover:bg-gray-50 transition cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-xs text-gray-400 w-8 text-right">#{index + 1}</span>

          <span
            className="text-xs font-bold px-3 py-1 rounded-full text-white"
            style={{ backgroundColor: actionColor }}
          >
            {ACTION_LABELS[episode.action] || episode.action}
          </span>

          {outcome ? (
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${outcome.bg} ${outcome.color}`}>
              {outcome.label}
            </span>
          ) : (
            <span className="text-xs text-gray-400 italic">Pending outcome...</span>
          )}
        </div>

        <div className="flex items-center gap-4">
          {episode.reward != null && (
            <span
              className={`text-sm font-bold ${
                episode.reward >= 0.5
                  ? 'text-green-600'
                  : episode.reward >= 0
                    ? 'text-yellow-600'
                    : 'text-red-600'
              }`}
            >
              {episode.reward > 0 ? '+' : ''}
              {episode.reward}
            </span>
          )}

          <span className="text-xs text-gray-400">{new Date(episode.created_at).toLocaleDateString()}</span>

          <span className={`text-gray-400 text-xs transition-transform ${expanded ? 'rotate-180' : ''}`}>
            v
          </span>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 ml-12 grid grid-cols-2 lg:grid-cols-4 gap-3">
          <DetailBox label="State" value={episode.state_key || ' - '} mono />
          <DetailBox
            label="Q Before"
            value={episode.q_value_before != null ? episode.q_value_before.toFixed(4) : ' - '}
          />
          <DetailBox
            label="Q After"
            value={episode.q_value_after != null ? episode.q_value_after.toFixed(4) : ' - '}
          />
          <DetailBox label="Mode" value="exploit / explore" />
        </div>
      )}
    </div>
  );
}

function DetailBox({
  label,
  value,
  mono = false
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={`text-xs text-gray-700 break-all ${mono ? 'font-mono' : 'font-medium'}`}>{value}</p>
    </div>
  );
}

function PolicyRow({
  entry,
  rank
}: {
  entry: PolicyEntry;
  rank: number;
}) {
  const decoded = entry.state_key.split('_');
  const actionColor = ACTION_COLORS[entry.best_action] || '#9ca3af';

  return (
    <div className="px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition">
      <div className="flex items-center gap-4">
        <span className="text-xs text-gray-400 w-6 text-right">{rank}</span>

        <div className="flex flex-wrap gap-1">
          {decoded.map((part, i) => (
            <span key={i} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
              {part}
            </span>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-4 shrink-0">
        <span
          className="text-xs font-bold px-3 py-1 rounded-full text-white"
          style={{ backgroundColor: actionColor }}
        >
          {ACTION_LABELS[entry.best_action] || entry.best_action}
        </span>

        <span
          className={`text-sm font-bold ${
            entry.best_q >= 0.5
              ? 'text-green-600'
              : entry.best_q >= 0
                ? 'text-yellow-600'
                : 'text-red-600'
          }`}
        >
          Q = {entry.best_q.toFixed(3)}
        </span>

        <span className="text-xs text-gray-400">{entry.visit_count}x visited</span>
      </div>
    </div>
  );
}

function EmptyState({
  icon,
  title,
  body
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="text-center py-16 px-4">
      <div className="mb-4 flex justify-center">{icon}</div>
      <p className="font-semibold text-gray-700 mb-2">{title}</p>
      <p className="text-sm text-gray-400 max-w-sm mx-auto">{body}</p>
    </div>
  );
}

export default InterventionHistory;
