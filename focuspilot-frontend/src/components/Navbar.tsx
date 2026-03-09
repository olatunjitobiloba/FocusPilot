import React from 'react';
import { Link, useLocation } from 'react-router-dom';

function Navbar() {
  const location = useLocation();
  const activeTab = new URLSearchParams(location.search).get('tab');

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

  const user = JSON.parse(localStorage.getItem('user') || '{}');

  return (
    <nav className="bg-white shadow sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <Link to="/dashboard" className="text-xl font-bold text-green-600">
            FocusFlow
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
