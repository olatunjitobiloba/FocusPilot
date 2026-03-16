import React, { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

function Navbar() {
  const location = useLocation();
  const activeTab = new URLSearchParams(location.search).get('tab');

  useEffect(() => {
    const token = localStorage.getItem('token');
    const refreshToken = localStorage.getItem('refresh_token');
    const userRaw = localStorage.getItem('user');
    const user = userRaw ? JSON.parse(userRaw) : null;
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

  const user = JSON.parse(localStorage.getItem('user') || '{}');

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
              🤖 Dashboard
            </Link>
            <Link
              to="/execution"
              className={`font-medium text-sm pb-1 transition ${getExecutionClass()}`}
            >
              ⚡ Actions
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
