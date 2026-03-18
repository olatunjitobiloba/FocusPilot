import React, { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

function BrainIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M9.5 5a3.5 3.5 0 0 0-3.5 3.5v.2a2.8 2.8 0 0 0-2 2.68A2.8 2.8 0 0 0 6 14.06V15a3 3 0 0 0 3 3h1V5H9.5ZM14.5 5H14v13h1a3 3 0 0 0 3-3v-.94a2.8 2.8 0 0 0 2-2.68 2.8 2.8 0 0 0-2-2.68v-.2A3.5 3.5 0 0 0 14.5 5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M10 8.2a2.2 2.2 0 0 1-2.2 2.2M10 12.4a2.2 2.2 0 0 1-2.2 2.2M14 8.2a2.2 2.2 0 0 0 2.2 2.2M14 12.4a2.2 2.2 0 0 0 2.2 2.2"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

function safeParseUser(raw: string | null) {
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function Navbar() {
  const location = useLocation();
  const activeTab = new URLSearchParams(location.search).get('tab');

  useEffect(() => {
    const token = localStorage.getItem('token');
    const refreshToken = localStorage.getItem('refresh_token');
    const userRaw = localStorage.getItem('user');
    const user = safeParseUser(userRaw);
    if (!token) return;

    window.postMessage(
      {
        source: 'focuspilot-web',
        action: 'syncToken',
        token,
        refreshToken,
        user,
      },
      '*'
    );
  }, [location.pathname]);

  const getDashboardClass = () =>
    location.pathname === '/dashboard' && activeTab !== 'sessions'
      ? 'text-green-600 border-b-2 border-green-600'
      : 'text-gray-600 hover:text-gray-900';

  const getBlocklistClass = () =>
    location.pathname === '/blocklist'
      ? 'text-green-600 border-b-2 border-green-600'
      : 'text-gray-600 hover:text-gray-900';

  const getSessionsClass = () =>
    location.pathname === '/dashboard' && activeTab === 'sessions'
      ? 'text-green-600 border-b-2 border-green-600'
      : 'text-gray-600 hover:text-gray-900';

  const getSettingsClass = () =>
    location.pathname === '/settings'
      ? 'text-green-600 border-b-2 border-green-600'
      : 'text-gray-600 hover:text-gray-900';

  const getAgentClass = () =>
    location.pathname === '/agent'
      ? 'text-green-600 border-b-2 border-green-600'
      : 'text-gray-600 hover:text-gray-900';

  const getAgentDashboardClass = () =>
    location.pathname === '/agent-dashboard'
      ? 'text-green-600 border-b-2 border-green-600'
      : 'text-gray-600 hover:text-gray-900';

  const getExecutionClass = () =>
    location.pathname === '/execution'
      ? 'text-green-600 border-b-2 border-green-600'
      : 'text-gray-600 hover:text-gray-900';

  const getDNAClass = () =>
    location.pathname === '/dna'
      ? 'text-green-600 border-b-2 border-green-600'
      : 'text-gray-600 hover:text-gray-900';

  const getAnalyticsClass = () =>
    location.pathname === '/analytics'
      ? 'text-green-600 border-b-2 border-green-600'
      : 'text-gray-600 hover:text-gray-900';

  const getInterventionsClass = () =>
    location.pathname === '/interventions'
      ? 'text-green-600 border-b-2 border-green-600'
      : 'text-gray-600 hover:text-gray-900';

  const user = safeParseUser(localStorage.getItem('user')) || {};

  return (
    <nav className="bg-white shadow sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <Link to="/dashboard" className="text-xl font-bold text-green-600">
            FocusPilot
          </Link>

          <div className="flex items-center gap-6">
            <Link
              to="/dashboard"
              className={`font-medium text-sm pb-1 transition ${getDashboardClass()}`}
            >
              Dashboard
            </Link>
            <Link
              to="/blocklist"
              className={`font-medium text-sm pb-1 transition ${getBlocklistClass()}`}
            >
              Blocklist
            </Link>
            <Link
              to="/dashboard?tab=sessions"
              className={`font-medium text-sm pb-1 transition ${getSessionsClass()}`}
            >
              Sessions
            </Link>
            <Link
              to="/settings"
              className={`font-medium text-sm pb-1 transition ${getSettingsClass()}`}
            >
              Settings
            </Link>
            <Link
              to="/agent"
              className={`font-medium text-sm pb-1 transition ${getAgentClass()}`}
            >
              Agent
            </Link>
            <Link
              to="/agent-dashboard"
              className={`font-medium text-sm pb-1 transition ${getAgentDashboardClass()}`}
            >
              Agent Dashboard
            </Link>
            <Link
              to="/execution"
              className={`font-medium text-sm pb-1 transition ${getExecutionClass()}`}
            >
              Actions
            </Link>
            <Link
              to="/dna"
              className={`font-medium text-sm pb-1 transition ${getDNAClass()}`}
            >
              DNA
            </Link>
            <Link
              to="/analytics"
              className={`font-medium text-sm pb-1 transition ${getAnalyticsClass()}`}
            >
              Analytics
            </Link>
            <Link
              to="/interventions"
              className={`font-medium text-sm pb-1 transition inline-flex items-center gap-1.5 ${getInterventionsClass()}`}
            >
              <BrainIcon className="h-4 w-4" />
              <span>Interventions</span>
            </Link>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600">{user.full_name}</span>
            <button
              onClick={() => {
                localStorage.clear();
                window.location.href = '/login';
              }}
              className="text-sm text-gray-500 hover:text-red-600 transition"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
