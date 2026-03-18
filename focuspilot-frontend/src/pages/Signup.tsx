// src/pages/Signup.tsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../api/client';

declare global {
  interface Window {
    chrome?: {
      storage?: {
        local: {
          set: (items: Record<string, any>, callback?: () => void) => void;
        };
      };
    };
  }
}

function Signup() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await authAPI.signup(email, password, fullName);
      localStorage.setItem('token', response.data.access_token);
      if (response.data.refresh_token) {
        localStorage.setItem('refresh_token', response.data.refresh_token);
      }
      localStorage.setItem('user', JSON.stringify(response.data.user));

      const extensionChrome = window.chrome;
      if (extensionChrome?.storage?.local) {
        extensionChrome.storage.local.set({
          token: response.data.access_token,
          refresh_token: response.data.refresh_token,
          user: response.data.user,
        });
      }

      window.postMessage({
        source: 'focuspilot-web',
        action: 'syncToken',
        token: response.data.access_token,
        refreshToken: response.data.refresh_token,
        user: response.data.user,
      }, '*');
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden bg-slate-950 flex items-center justify-center px-4 py-8">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-32 -left-20 h-80 w-80 rounded-full bg-cyan-300/25 blur-3xl" />
        <div className="absolute bottom-0 -right-12 h-80 w-80 rounded-full bg-emerald-300/20 blur-3xl" />
      </div>

      <div className="relative w-full max-w-md rounded-2xl border border-white/10 bg-slate-900/85 shadow-2xl backdrop-blur p-8">
        <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/90 text-center mb-3">
          FocusPilot Access
        </p>
        <h1
          className="text-3xl font-black text-center mb-6 text-white"
          style={{ fontFamily: "'Space Grotesk', 'Sora', sans-serif" }}
        >
          Create Account
        </h1>
        
        {error && (
          <div className="bg-red-500/15 border border-red-400/50 text-red-200 px-4 py-3 rounded-lg mb-4 text-sm">
            <strong>Signup error:</strong> {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="full-name" className="block text-slate-300 mb-2 text-sm">Full Name</label>
            <input
              id="full-name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-slate-950/70 border border-white/15 text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-300/80"
              placeholder="Alex Johnson"
              required
              disabled={loading}
            />
          </div>

          <div className="mb-4">
            <label htmlFor="email" className="block text-slate-300 mb-2 text-sm">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-slate-950/70 border border-white/15 text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-300/80"
              placeholder="test@example.com"
              required
              disabled={loading}
            />
          </div>

          <div className="mb-6">
            <label htmlFor="password" className="block text-slate-300 mb-2 text-sm">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-slate-950/70 border border-white/15 text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-300/80"
              required
              minLength={6}
              placeholder="At least 6 characters"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-lg font-semibold bg-cyan-300 text-slate-900 hover:bg-cyan-200 disabled:bg-slate-600 disabled:text-slate-300 disabled:cursor-not-allowed transition"
          >
            {loading ? 'Creating Account...' : 'Sign Up'}
          </button>
        </form>

        <p className="text-center mt-5 text-slate-400 text-sm">
          Already have an account?{' '}
          <a href="/login" className="text-cyan-200 hover:text-cyan-100 underline-offset-4 hover:underline">
            Log In
          </a>
        </p>
      </div>
    </div>
  );
}

export default Signup;
