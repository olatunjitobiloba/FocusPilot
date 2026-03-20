import React, { useEffect, useState } from 'react';
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
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  useEffect(() => {
    setIsMenuOpen(false);
  }, [location.pathname]);

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

  const user = safeParseUser(localStorage.getItem('user')) || {};

  const navLinkClasses = (isActive: boolean) =>
    `font-medium text-sm py-2 px-4 lg:px-0 lg:pb-1 block lg:inline transition ${
      isActive
        ? 'text-green-600 border-l-4 lg:border-l-0 lg:border-b-2 border-green-600 bg-green-50 lg:bg-transparent'
        : 'text-gray-600 hover:text-gray-900'
    }`;

  return (
    <nav className="bg-white shadow sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4">
        {/* Desktop and Mobile header row */}
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/dashboard" className="text-xl font-bold text-green-600 shrink-0">
            FocusPilot
          </Link>

          {/* Hamburger menu button - visible on mobile */}
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="lg:hidden p-2 hover:bg-gray-100 rounded-lg transition"
            aria-label="Toggle menu"
            aria-expanded={isMenuOpen}
          >
            <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={isMenuOpen ? 'M6 18L18 6M6 6l12 12' : 'M4 6h16M4 12h16M4 18h16'} />
            </svg>
          </button>

          {/* Right section - user info and logout */}
          <div className="hidden lg:flex items-center gap-3 ml-auto">
            <span className="text-sm text-gray-600 truncate max-w-[180px]">{user.full_name}</span>
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

        {/* Desktop Navigation - visible on lg and up */}
        <div className="hidden lg:flex items-center gap-4 border-t border-gray-100">
          <Link
            to="/dashboard"
            className={navLinkClasses(location.pathname === '/dashboard' && activeTab !== 'sessions')}
          >
            Dashboard
          </Link>
          <Link
            to="/blocklist"
            className={navLinkClasses(location.pathname === '/blocklist')}
          >
            Blocklist
          </Link>
          <Link
            to="/dashboard?tab=sessions"
            className={navLinkClasses(location.pathname === '/dashboard' && activeTab === 'sessions')}
          >
            Sessions
          </Link>
          <Link
            to="/settings"
            className={navLinkClasses(location.pathname === '/settings')}
          >
            Settings
          </Link>
          <Link
            to="/agent"
            className={navLinkClasses(location.pathname === '/agent')}
          >
            Agent
          </Link>
          <Link
            to="/agent-dashboard"
            className={navLinkClasses(location.pathname === '/agent-dashboard')}
          >
            Agent Dashboard
          </Link>
          <Link
            to="/execution"
            className={navLinkClasses(location.pathname === '/execution')}
          >
            Actions
          </Link>
          <Link
            to="/dna"
            className={navLinkClasses(location.pathname === '/dna')}
          >
            DNA
          </Link>
          <Link
            to="/analytics"
            className={navLinkClasses(location.pathname === '/analytics')}
          >
            Analytics
          </Link>
          <Link
            to="/interventions"
            className={`${navLinkClasses(location.pathname === '/interventions')} inline-flex items-center gap-1.5`}
          >
            <BrainIcon className="h-4 w-4" />
            <span>Interventions</span>
          </Link>
        </div>

        {/* Mobile Navigation - visible on small screens */}
        {isMenuOpen && (
          <div className="lg:hidden border-t border-gray-100 py-2">
            <Link
              to="/dashboard"
              className={navLinkClasses(location.pathname === '/dashboard' && activeTab !== 'sessions')}
            >
              Dashboard
            </Link>
            <Link
              to="/blocklist"
              className={navLinkClasses(location.pathname === '/blocklist')}
            >
              Blocklist
            </Link>
            <Link
              to="/dashboard?tab=sessions"
              className={navLinkClasses(location.pathname === '/dashboard' && activeTab === 'sessions')}
            >
              Sessions
            </Link>
            <Link
              to="/settings"
              className={navLinkClasses(location.pathname === '/settings')}
            >
              Settings
            </Link>
            <Link
              to="/agent"
              className={navLinkClasses(location.pathname === '/agent')}
            >
              Agent
            </Link>
            <Link
              to="/agent-dashboard"
              className={navLinkClasses(location.pathname === '/agent-dashboard')}
            >
              Agent Dashboard
            </Link>
            <Link
              to="/execution"
              className={navLinkClasses(location.pathname === '/execution')}
            >
              Actions
            </Link>
            <Link
              to="/dna"
              className={navLinkClasses(location.pathname === '/dna')}
            >
              DNA
            </Link>
            <Link
              to="/analytics"
              className={navLinkClasses(location.pathname === '/analytics')}
            >
              Analytics
            </Link>
            <Link
              to="/interventions"
              className={`${navLinkClasses(location.pathname === '/interventions')} inline-flex items-center gap-1.5`}
            >
              <BrainIcon className="h-4 w-4" />
              <span>Interventions</span>
            </Link>

            {/* Mobile user info and logout */}
            <div className="flex flex-col gap-3 border-t border-gray-100 mt-3 pt-3">
              <span className="text-sm text-gray-600 px-4">{user.full_name}</span>
              <button
                onClick={() => {
                  localStorage.clear();
                  window.location.href = '/login';
                }}
                className="text-sm text-gray-500 hover:text-red-600 transition px-4 py-2 text-left"
              >
                Logout
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}

export default Navbar;
