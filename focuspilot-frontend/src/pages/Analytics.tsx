import React, { useEffect, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import Navbar from '../components/Navbar';
import { analyticsAPI } from '../api/client';
import {
  AnalyticsSummary,
  DailyBreakdown,
  SessionRow,
  WeeklyReport,
} from '../types/analytics';

const RANGE_OPTIONS = [
  { label: '7 days', value: 7 },
  { label: '14 days', value: 14 },
  { label: '30 days', value: 30 },
];

type RiskTrendPoint = {
  day_label: string;
  risk_pct: number;
};

type TimeCategory = {
  name: string;
  minutes: number;
  pct: number;
  color: string;
};

type TopSite = {
  domain: string;
  minutes: number;
  pct: number;
  is_distraction: boolean;
  is_productive: boolean;
};

type TimeBreakdown = {
  categories: TimeCategory[];
  top_sites: TopSite[];
};

type StreakInfo = {
  current_streak: number;
  longest_streak: number;
};

type BestInfo = {
  day_name?: string;
  hour_label?: string;
  avg_score: number;
};

type OverviewResponse = {
  summary?: AnalyticsSummary;
  daily_breakdown?: DailyBreakdown[];
  risk_trend?: RiskTrendPoint[];
  time_breakdown?: TimeBreakdown;
  sessions?: SessionRow[];
  streak?: StreakInfo;
  best_day?: BestInfo;
  best_hour?: BestInfo;
};

const EMPTY_SUMMARY: AnalyticsSummary = {
  total_sessions: 0,
  total_focused_hours: 0,
  avg_focus_score: 0,
  avg_session_duration: 0,
  total_distraction_mins: 0,
  completion_rate: 0,
};

function Analytics() {
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [report, setReport] = useState<WeeklyReport | null>(null);
  const [range, setRange] = useState(30);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'overview' | 'sessions' | 'report'>('overview');

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [overviewRes, reportRes] = await Promise.all([
          analyticsAPI.getOverview(range),
          analyticsAPI.getWeeklyReport(),
        ]);

        setOverview((overviewRes.data || {}) as OverviewResponse);
        setReport((reportRes.data || null) as WeeklyReport | null);
      } catch (error) {
        console.error('Analytics load error:', error);
      } finally {
        setLoading(false);
      }
    };

    void loadData();
  }, [range]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100">
        <Navbar />
        <div className="flex h-64 items-center justify-center">
          <p className="animate-pulse text-xl text-gray-500">Loading analytics...</p>
        </div>
      </div>
    );
  }

  const summary: AnalyticsSummary = overview?.summary || EMPTY_SUMMARY;

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />

      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-8 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
            <p className="mt-1 text-sm text-gray-500">Your productivity trends and insights</p>
          </div>

          <div className="flex gap-2">
            {RANGE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setRange(opt.value)}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                  range === opt.value
                    ? 'bg-gray-900 text-white'
                    : 'bg-white text-gray-600 shadow-sm hover:bg-gray-50'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-8 w-fit rounded-xl bg-white p-1 shadow-sm">
          {(['overview', 'sessions', 'report'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`capitalize rounded-lg px-5 py-2 text-sm font-medium transition ${
                tab === t ? 'bg-gray-900 text-white' : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {t === 'overview' ? 'Overview' : t === 'sessions' ? 'Sessions' : 'Weekly report'}
            </button>
          ))}
        </div>

        {tab === 'overview' && (
          <>
            <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-3">
              <SummaryCard
                label="Focused Hours"
                value={`${summary.total_focused_hours || 0}h`}
                color="text-blue-600"
                sub={`${summary.total_sessions || 0} sessions`}
              />
              <SummaryCard
                label="Avg Focus Score"
                value={`${summary.avg_focus_score || 0}/10`}
                color="text-yellow-600"
                sub={`${summary.completion_rate || 0}% completion`}
              />
              <SummaryCard
                label="Current Streak"
                value={`${overview?.streak?.current_streak || 0} days`}
                color="text-orange-600"
                sub={`Best: ${overview?.streak?.longest_streak || 0} days`}
              />
              <SummaryCard
                label="Best Day"
                value={overview?.best_day?.day_name || '-'}
                color="text-green-600"
                sub={`Avg score: ${overview?.best_day?.avg_score || 0}`}
              />
              <SummaryCard
                label="Peak Hour"
                value={overview?.best_hour?.hour_label || '-'}
                color="text-indigo-600"
                sub={`Avg score: ${overview?.best_hour?.avg_score || 0}`}
              />
              <SummaryCard
                label="Distraction Time"
                value={`${summary.total_distraction_mins || 0}m`}
                color="text-red-600"
                sub="Total this period"
              />
            </div>

            <div className="mb-6 rounded-xl bg-white p-6 shadow">
              <h2 className="mb-4 text-lg font-bold text-gray-900">Daily Focus Score</h2>
              <DailyFocusChart data={overview?.daily_breakdown || []} />
            </div>

            <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="rounded-xl bg-white p-6 shadow">
                <h2 className="mb-4 text-lg font-bold text-gray-900">Risk Score Trend</h2>
                <RiskTrendChart data={overview?.risk_trend || []} />
              </div>

              <div className="rounded-xl bg-white p-6 shadow">
                <h2 className="mb-4 text-lg font-bold text-gray-900">Time Breakdown</h2>
                <TimeBreakdownChart data={overview?.time_breakdown} />
              </div>
            </div>

            <div className="rounded-xl bg-white p-6 shadow">
              <h2 className="mb-4 text-lg font-bold text-gray-900">Top Sites by Time</h2>
              <TopSitesTable sites={overview?.time_breakdown?.top_sites || []} />
            </div>
          </>
        )}

        {tab === 'sessions' && (
          <div className="rounded-xl bg-white shadow">
            <div className="border-b border-gray-100 p-6">
              <h2 className="text-lg font-bold text-gray-900">Session History</h2>
              <p className="mt-1 text-sm text-gray-500">
                {overview?.sessions?.length || 0} sessions in the last {range} days
              </p>
            </div>
            <SessionHistoryTable sessions={overview?.sessions || []} />
          </div>
        )}

        {tab === 'report' && report && <WeeklyReportView report={report} />}
      </main>
    </div>
  );
}

type SummaryCardProps = {
  label: string;
  value: string;
  color: string;
  sub: string;
};

function SummaryCard({ label, value, color, sub }: SummaryCardProps) {
  return (
    <div className="rounded-xl bg-white p-5 shadow">
      <p className="mb-2 text-sm text-gray-500">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="mt-1 text-xs text-gray-400">{sub}</p>
    </div>
  );
}

function DailyFocusChart({ data }: { data: DailyBreakdown[] }) {
  if (!data.length) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-gray-400">No data yet</p>
      </div>
    );
  }

  const chartData = data.slice(-14);

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} barSize={18}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="day_short" tick={{ fontSize: 11, fill: '#9ca3af' }} />
        <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: '#9ca3af' }} />
        <Tooltip
          formatter={(value: number | string | undefined) => [value ?? 0, 'Focus score']}
          contentStyle={{
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
            fontSize: '12px',
          }}
        />
        <Bar dataKey="avg_score" fill="#4f46e5" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function RiskTrendChart({ data }: { data: RiskTrendPoint[] }) {
  if (!data.length) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-gray-400">No risk data yet</p>
      </div>
    );
  }

  const chartData = data.slice(-14);

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="day_label" tick={{ fontSize: 10, fill: '#9ca3af' }} interval="preserveStartEnd" />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 10, fill: '#9ca3af' }}
          tickFormatter={(v: number) => `${v}%`}
        />
        <Tooltip
          formatter={(value: number | string | undefined) => [`${value ?? 0}%`, 'Avg risk']}
          contentStyle={{
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
            fontSize: '12px',
          }}
        />
        <Line
          type="monotone"
          dataKey="risk_pct"
          stroke="#ef4444"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function TimeBreakdownChart({ data }: { data?: TimeBreakdown }) {
  const categories = data?.categories || [];

  if (!categories.length) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-gray-400">No activity data yet</p>
      </div>
    );
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={160}>
        <PieChart>
          <Pie
            data={categories}
            dataKey="pct"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={65}
            innerRadius={35}
          >
            {categories.map((entry, i) => (
              <Cell key={`${entry.name}-${i}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number | string | undefined) => [`${value ?? 0}%`, 'Share']}
            contentStyle={{
              borderRadius: '8px',
              border: '1px solid #e5e7eb',
              fontSize: '12px',
            }}
          />
        </PieChart>
      </ResponsiveContainer>

      <div className="mt-2 flex flex-col gap-2">
        {categories.map((c, i) => (
          <div key={`${c.name}-${i}`} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full" style={{ backgroundColor: c.color }} />
              <span className="text-sm text-gray-600">{c.name}</span>
            </div>
            <span className="text-sm font-medium text-gray-800">
              {c.minutes}m ({c.pct}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TopSitesTable({ sites }: { sites: TopSite[] }) {
  if (!sites.length) {
    return <p className="py-8 text-center text-sm text-gray-400">No browsing data yet</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100">
            <th className="pb-3 text-left font-medium text-gray-500">Domain</th>
            <th className="pb-3 text-right font-medium text-gray-500">Time</th>
            <th className="pb-3 text-right font-medium text-gray-500">Share</th>
            <th className="pb-3 text-right font-medium text-gray-500">Type</th>
          </tr>
        </thead>
        <tbody>
          {sites.map((site, i) => (
            <tr key={`${site.domain}-${i}`} className="border-b border-gray-50 last:border-0">
              <td className="py-3 font-medium text-gray-800">{site.domain}</td>
              <td className="py-3 text-right text-gray-600">{site.minutes}m</td>
              <td className="py-3 text-right text-gray-600">{site.pct}%</td>
              <td className="py-3 text-right">
                {site.is_distraction ? (
                  <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-600">
                    Distraction
                  </span>
                ) : site.is_productive ? (
                  <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-600">
                    Productive
                  </span>
                ) : (
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
                    Neutral
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SessionHistoryTable({ sessions }: { sessions: SessionRow[] }) {
  if (!sessions.length) {
    return (
      <div className="py-16 text-center">
        <p className="text-gray-400">No sessions in this period</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100">
            {['Date', 'Day', 'Start', 'Duration', 'Score', 'Type'].map((h) => (
              <th key={h} className="px-6 py-3 text-left font-medium text-gray-500 first:pl-6">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sessions.map((s, i) => (
            <tr key={`${s.id}-${i}`} className="border-b border-gray-50 transition last:border-0 hover:bg-gray-50">
              <td className="px-6 py-3 font-medium text-gray-800">{s.date}</td>
              <td className="px-6 py-3 text-gray-500">{s.day}</td>
              <td className="px-6 py-3 text-gray-600">{s.start_time}</td>
              <td className="px-6 py-3 text-gray-600">{s.duration_mins}m</td>
              <td className="px-6 py-3">
                {s.focus_score != null ? (
                  <span
                    className={`font-bold ${
                      s.focus_score >= 7
                        ? 'text-green-600'
                        : s.focus_score >= 5
                        ? 'text-yellow-600'
                        : 'text-red-600'
                    }`}
                  >
                    {s.focus_score}/10
                  </span>
                ) : (
                  <span className="text-gray-300">-</span>
                )}
              </td>
              <td className="px-6 py-3">
                {s.auto_started ? (
                  <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-600">
                    Auto
                  </span>
                ) : (
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
                    Manual
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WeeklyReportView({ report }: { report: WeeklyReport }) {
  const imp = report.improvement || {};

  const ImpBadge = ({ pct }: { pct: number }) => (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-bold ${
        pct > 0 ? 'bg-green-100 text-green-700' : pct < 0 ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'
      }`}
    >
      {pct > 0 ? `+${pct}%` : `${pct}%`}
    </span>
  );

  return (
    <div className="space-y-6">
      <div className="rounded-xl bg-white p-6 shadow">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Weekly Report</h2>
            <p className="mt-1 text-sm text-gray-500">{report.week_label}</p>
          </div>
          <span className="text-sm font-semibold text-gray-500">
            {imp.is_improving ? 'Improving' : 'Declining'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          {
            label: 'Sessions',
            this: report.this_week?.total_sessions,
            pct: imp.sessions_pct as number | null,
          },
          {
            label: 'Focus Hours',
            this: `${report.this_week?.total_focused_hours}h`,
            pct: imp.hours_pct as number | null,
          },
          {
            label: 'Avg Score',
            this: `${report.this_week?.avg_focus_score}/10`,
            pct: imp.score_pct as number | null,
          },
          {
            label: 'Completion',
            this: `${report.this_week?.completion_rate}%`,
            pct: null,
          },
        ].map((item, i) => (
          <div key={i} className="rounded-xl bg-white p-5 shadow">
            <p className="mb-1 text-sm text-gray-500">{item.label}</p>
            <p className="text-2xl font-bold text-gray-900">{item.this}</p>
            {item.pct != null && (
              <div className="mt-2">
                <ImpBadge pct={item.pct} />
                <span className="ml-1 text-xs text-gray-400">vs last week</span>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl bg-white p-6 shadow">
          <h3 className="mb-4 font-bold text-gray-900">Achievements This Week</h3>
          {(report.achievements || []).length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-400">
              Complete more sessions to unlock achievements
            </p>
          ) : (
            <div className="space-y-3">
              {(report.achievements || []).map((a, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 rounded-xl border border-green-100 bg-green-50 p-3"
                >
                  <div>
                    <p className="text-sm font-semibold text-green-800">{a.title}</p>
                    <p className="mt-0.5 text-xs text-green-600">{a.body}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-xl bg-white p-6 shadow">
          <h3 className="mb-4 font-bold text-gray-900">Areas to Improve</h3>
          {(report.improvements || []).length === 0 ? (
            <div className="py-6 text-center">
              <p className="text-sm text-gray-400">No major issues this week</p>
            </div>
          ) : (
            <div className="space-y-3">
              {(report.improvements || []).map((item, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 rounded-xl border border-orange-100 bg-orange-50 p-3"
                >
                  <div>
                    <p className="text-sm font-semibold text-orange-800">{item.title}</p>
                    <p className="mt-0.5 text-xs text-orange-600">{item.body}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="rounded-xl bg-white p-6 shadow">
        <h3 className="mb-4 font-bold text-gray-900">Recommendations for Next Week</h3>
        <div className="space-y-3">
          {(report.recommendations || []).map((rec, i) => (
            <div key={i} className="flex items-start gap-3 border-b border-gray-50 py-2 last:border-0">
              <span className="mt-0.5 shrink-0 text-sm font-bold text-indigo-500">{i + 1}.</span>
              <p className="text-sm leading-relaxed text-gray-700">{rec}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Analytics;
