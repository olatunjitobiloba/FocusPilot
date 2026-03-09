import React, { useState, useEffect, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import { useLocation, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import SessionControl from '../components/SessionControl';
import Navbar from '../components/Navbar';

interface Stats {
  todayHours: number;
  todaySessions: number;
  streak: number;
  totalHours: number;
  totalSessions: number;
  avgScore: number;
  avgMinPerSession: number;
}

interface WeeklyData {
  day: string;
  hours: number;
}

interface Session {
  id: string;
  date: string;
  duration: number;
  score: number;
  distractions: number;
  start_time: string;
  end_time?: string;
  duration_minutes?: number;
  focus_score?: number;
  distraction_count?: number;
}

interface DistractionData {
  name: string;
  value: number;
}

interface Recommendation {
  title: string;
  message: string;
  priority?: 'high' | 'medium' | 'low';
}

const COLORS = ['#16a34a', '#22c55e', '#4ade80', '#86efac'];
const DASHBOARD_CACHE_KEY = 'focuspilot_dashboard_cache_v1';

// ── SMALL COMPONENTS ──────────────────────────────────────────────
function StatCard({ icon, label, value, sub }: { icon: string; label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 flex flex-col gap-1">
      <span className="text-2xl">{icon}</span>
      <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-gray-800">{value}</p>
      {sub && <p className="text-xs text-gray-400">{sub}</p>}
    </div>
  );
}

function SessionCard({ session }: { session: Session }) {
  const perfect = session.distractions === 0;
  return (
    <div className="flex items-center justify-between bg-white rounded-xl px-5 py-4 shadow-sm border border-gray-100">
      <div>
        <p className="text-sm font-semibold text-gray-700">{session.date}</p>
        <p className="text-xs text-gray-400 mt-0.5">
          {session.duration > 0 ? `${session.duration} min` : '< 1 min'}
          {session.score > 0 && ` · Score ${session.score}/10`}
        </p>
      </div>
      <span
        className={`text-xs font-semibold px-3 py-1 rounded-full ${
          perfect ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-500'
        }`}
      >
        {perfect ? 'Perfect' : `${session.distractions} distractions`}
      </span>
    </div>
  );
}

// ── MAIN DASHBOARD ────────────────────────────────────────────────
export default function Dashboard() {
  const location = useLocation();
  const [activeTab, setActiveTab] = useState<'overview' | 'sessions' | 'insights'>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [weeklyData, setWeeklyData] = useState<WeeklyData[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [distractionData, setDistractionData] = useState<DistractionData[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [error, setError] = useState<string>('');
  const navigate = useNavigate();

  useEffect(() => {
    const tab = new URLSearchParams(location.search).get('tab');
    if (tab === 'sessions' || tab === 'insights' || tab === 'overview') {
      setActiveTab(tab);
      return;
    }
    setActiveTab('overview');
  }, [location.search]);

  const loadDashboardData = useCallback(async (isInitialLoad = false) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        navigate('/login');
        return;
      }

      setError('');

      if (isInitialLoad) {
        setLoading(true);
      } else {
        setIsRefreshing(true);
      }

      // Fetch primary dashboard data in parallel (fast path)
      const [statsRes, weeklyRes, sessionsRes, distractionsRes, recommendationsRes] = await Promise.allSettled([
        api.get('/stats/daily'),
        api.get('/stats/weekly'),
        api.get('/sessions/history'),
        api.get('/analytics/distractions'),
        api.get('/recommendations/')
      ]);

      const extractError = (result: PromiseSettledResult<any>) =>
        result.status === 'rejected' ? result.reason : null;

      const firstAuthError = [statsRes, weeklyRes, sessionsRes, distractionsRes, recommendationsRes]
        .map(extractError)
        .find((err: any) => err?.response?.status === 401);

      if (firstAuthError) {
        throw firstAuthError;
      }

      // Transform stats
      const dailyStats = statsRes.status === 'fulfilled'
        ? statsRes.value.data
        : { total_focus_minutes: 0, sessions_count: 0 };
      const weekly = weeklyRes.status === 'fulfilled'
        ? weeklyRes.value.data
        : { current_streak: 0, daily_breakdown: {} };

      setStats({
        todayHours: dailyStats.total_focus_minutes / 60,
        todaySessions: dailyStats.sessions_count || 0,
        streak: weekly.current_streak || 0,
        totalHours: 0,
        totalSessions: 0,
        avgScore: 0,
        avgMinPerSession: 0,
      });

      // Process weekly data
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const weeklyChartData = days.map((day, idx) => {
        const date = new Date();
        date.setDate(date.getDate() - (date.getDay() - idx));
        const dateStr = date.toISOString().split('T')[0];
        const dayData = weekly.daily_breakdown?.[dateStr] || { minutes: 0 };
        return {
          day,
          hours: parseFloat((dayData.minutes / 60).toFixed(1))
        };
      });
      setWeeklyData(weeklyChartData);

      // Transform sessions
      let formattedSessions: Session[] = [];

      if (sessionsRes.status === 'fulfilled' && sessionsRes.value.data.sessions) {
        formattedSessions = sessionsRes.value.data.sessions.map((s: any) => ({
          id: s.id,
          date: new Date(s.start_time).toLocaleString(),
          duration: s.duration_minutes || 0,
          score: s.focus_score || 0,
          distractions: s.distraction_count || 0,
          start_time: s.start_time,
          end_time: s.end_time,
          duration_minutes: s.duration_minutes,
          focus_score: s.focus_score,
          distraction_count: s.distraction_count,
        }));
      }

      const topDistractions = (distractionsRes.status === 'fulfilled' && Array.isArray(distractionsRes.value.data?.top_distractions))
        ? distractionsRes.value.data.top_distractions
        : [];

      const computedDistractionData: DistractionData[] = topDistractions
        .slice(0, 5)
        .map((item: any) => ({
          name: item.domain,
          value: Number(item.total_minutes || 0),
        }))
        .filter((item: DistractionData) => item.value > 0);

      const fetchedRecommendations: Recommendation[] = (recommendationsRes.status === 'fulfilled' && Array.isArray(recommendationsRes.value.data?.recommendations))
        ? recommendationsRes.value.data.recommendations.map((r: any) => ({
            title: r.title,
            message: r.message,
            priority: r.priority,
          }))
        : [];

      setSessions(formattedSessions);
      setDistractionData(computedDistractionData);
      setRecommendations(fetchedRecommendations);

      // Cache lightweight dashboard payload for faster subsequent loads
      try {
        localStorage.setItem(
          DASHBOARD_CACHE_KEY,
          JSON.stringify({
            stats: {
              todayHours: dailyStats.total_focus_minutes / 60,
              todaySessions: dailyStats.sessions_count || 0,
              streak: weekly.current_streak || 0,
              totalHours: 0,
              totalSessions: 0,
              avgScore: 0,
              avgMinPerSession: 0,
            },
            weeklyData: days.map((day, idx) => {
              const date = new Date();
              date.setDate(date.getDate() - (date.getDay() - idx));
              const dateStr = date.toISOString().split('T')[0];
              const dayData = weekly.daily_breakdown?.[dateStr] || { minutes: 0 };
              return {
                day,
                hours: parseFloat((dayData.minutes / 60).toFixed(1))
              };
            }),
            sessions: formattedSessions,
            distractionData: computedDistractionData,
            recommendations: fetchedRecommendations
          })
        );
      } catch (cacheErr) {
        console.warn('Could not cache dashboard data:', cacheErr);
      }

      // Load heavy summary endpoint after first render (slow path)
      api.get('/sessions/summary')
        .then((summaryRes) => {
          const summary = summaryRes.data;
          setStats((prev) => {
            if (!prev) return prev;
            return {
              ...prev,
              totalHours: summary.total_hours || 0,
              totalSessions: summary.total_sessions || 0,
              avgScore: summary.avg_focus_score || 0,
              avgMinPerSession: summary.avg_session_minutes || 0,
            };
          });
        })
        .catch((summaryErr) => {
          console.warn('Could not load session summary:', summaryErr);
        });

    } catch (error) {
      console.error('Error loading dashboard:', error);
      const errorMessage = (error as any).response?.data?.detail || (error as any).message || 'Failed to load dashboard data';
      setError(errorMessage);
      if ((error as any).response?.status === 401) {
        localStorage.clear();
        navigate('/login');
      }
    } finally {
      if (isInitialLoad) {
        setLoading(false);
      }
      setIsRefreshing(false);
    }
  }, [navigate]);

  useEffect(() => {
    const cached = localStorage.getItem(DASHBOARD_CACHE_KEY);
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        if (parsed?.stats) setStats(parsed.stats);
        if (Array.isArray(parsed?.weeklyData)) setWeeklyData(parsed.weeklyData);
        if (Array.isArray(parsed?.sessions)) setSessions(parsed.sessions);
        if (Array.isArray(parsed?.distractionData)) setDistractionData(parsed.distractionData);
        if (Array.isArray(parsed?.recommendations)) setRecommendations(parsed.recommendations);
        setLoading(false);
        loadDashboardData(false);
        return;
      } catch {
        localStorage.removeItem(DASHBOARD_CACHE_KEY);
      }
    }

    loadDashboardData(true);
  }, [loadDashboardData]);

  // Sync token to extension on mount
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      console.log('Dashboard: Syncing token to extension');
      window.postMessage({
        source: 'focuspilot-web',
        action: 'syncToken',
        token
      }, '*');
    }
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 font-medium">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">

        {/* ── TABS ── */}
        <div className="flex gap-2 mb-8 bg-white rounded-xl p-1 shadow-sm border border-gray-100 w-fit">
          {(['overview', 'insights'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-2 rounded-lg text-sm font-semibold capitalize transition-all ${
                activeTab === tab
                  ? 'bg-green-600 text-white shadow'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab === 'overview' ? 'Overview' : 'Insights'}
            </button>
          ))}
        </div>

        {/* ── OVERVIEW TAB ── */}
        {activeTab === 'overview' && (
          <div className="flex flex-col gap-8">

            {/* Session Control */}
            <SessionControl onSessionEnd={() => {
              loadDashboardData(false);
            }} />

            {isRefreshing && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
                <p className="text-sm">Refreshing dashboard data...</p>
              </div>
            )}

            {!stats && !error && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
                <p className="text-sm">Loading dashboard data...</p>
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                <p className="text-sm font-semibold mb-1">Error loading dashboard</p>
                <p className="text-xs">{error}</p>
                <button
                  onClick={() => {
                    setError('');
                    loadDashboardData(true);
                  }}
                  className="mt-2 text-xs bg-red-100 hover:bg-red-200 text-red-700 px-3 py-1 rounded font-medium"
                >
                  Retry
                </button>
              </div>
            )}

            {stats && (
              <>
            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <StatCard
                icon="TF"
                label="Today's Focus"
                value={`${stats.todayHours.toFixed(1)}h`}
                sub={`${stats.todaySessions} sessions`}
              />
              <StatCard
                icon="ST"
                label="Streak"
                value={`${stats.streak} days`}
                sub="Keep it going!"
              />
              <StatCard
                icon="TT"
                label="Total Focus"
                value={`${stats.totalHours.toFixed(1)}h`}
                sub={`${stats.totalSessions} sessions`}
              />
              <StatCard
                icon="SC"
                label="Avg Score"
                value={`${stats.avgScore.toFixed(1)}/10`}
                sub={`${stats.avgMinPerSession.toFixed(1)} min/session`}
              />
            </div>

            {/* Charts Row */}
            <div className="grid md:grid-cols-2 gap-6">
              {/* Weekly Bar Chart */}
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <h2 className="text-base font-bold text-gray-700 mb-4">Weekly Focus Time</h2>
                {weeklyData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={weeklyData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} unit="h" />
                      <Tooltip formatter={(v) => [`${v}h`, 'Focus Time']} />
                      <Bar dataKey="hours" fill="#16a34a" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-48 text-gray-400">
                    <p className="text-sm">No weekly data yet</p>
                  </div>
                )}
              </div>

              {/* Distractions Pie Chart */}
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <h2 className="text-base font-bold text-gray-700 mb-4">Top Distractions</h2>
                {distractionData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={distractionData}
                        cx="50%"
                        cy="50%"
                        outerRadius={70}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                      >
                        {distractionData.map((_, i) => (
                          <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v) => [`${v} min`, 'Time spent']} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-gray-400">
                    <p className="text-sm font-medium">No distractions tracked yet!</p>
                    <p className="text-xs mt-1">Start a focus session to see data</p>
                  </div>
                )}
              </div>
            </div>
              </>
            )}
          </div>
        )}

        {/* ── SESSIONS TAB ── */}
        {activeTab === 'sessions' && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-700">Recent Sessions</h2>
              <span className="text-xs text-gray-400">{sessions.length} sessions total</span>
            </div>
            {sessions.length > 0 ? (
              sessions.map((s, i) => <SessionCard key={i} session={s} />)
            ) : (
              <div className="bg-white rounded-2xl p-8 text-center border border-gray-100">
                <p className="text-gray-600 font-medium">No sessions yet</p>
                <p className="text-sm text-gray-400 mt-1">Start a focus session to get started!</p>
              </div>
            )}
          </div>
        )}

        {/* ── INSIGHTS TAB ── */}
        {activeTab === 'insights' && (
          <div className="flex flex-col gap-4">
            <h2 className="text-lg font-bold text-gray-700">Recommendations</h2>
            {recommendations.length > 0 ? (
              recommendations.map((r, i) => (
                <div
                  key={i}
                  className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex gap-4 items-start"
                >
                  <div>
                    <p className="font-bold text-gray-800 mb-1">{r.title}</p>
                    <p className="text-sm text-gray-500">{r.message}</p>
                  </div>
                </div>
              ))
            ) : (
              <div className="bg-white rounded-2xl p-8 text-center border border-gray-100">
                <p className="text-gray-600 font-medium">No recommendations yet</p>
                <p className="text-sm text-gray-400 mt-1">Complete a few sessions to get AI suggestions</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}