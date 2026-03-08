// src/pages/Login.tsx
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
      runtime?: {
        sendMessage: (message: any) => void;
      };
    };
  }
}

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    console.log('Attempting login with:', email); // DEBUG

    try {
      const response = await authAPI.login(email, password);
      
      console.log('Login response:', response.data); // DEBUG
      
      // Save token to localStorage
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      
      // IMPORTANT: Also save to Chrome extension storage (if extension exists)
      if (typeof window.chrome !== 'undefined' && window.chrome?.storage) {
        window.chrome!.storage!.local.set({ 
          token: response.data.access_token,
          user: response.data.user
        }, () => {
          console.log('Token saved to extension storage');
        });
      }
      
      console.log('Navigating to dashboard...'); // DEBUG
      
      // Navigate to dashboard
      navigate('/dashboard');
      
    } catch (err: any) {
      console.error('Login error:', err); // DEBUG
      
      // Handle different error types
      if (err.response) {
        // Server responded with error
        console.error('Server error:', err.response.data);
        setError(err.response.data.detail || 'Login failed');
      } else if (err.request) {
        // Request made but no response
        console.error('No response from server');
        setError('Cannot reach server. Check your connection.');
      } else {
        // Something else went wrong
        console.error('Error:', err.message);
        setError('An unexpected error occurred');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center px-4">
      <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full">
        <h1 className="text-3xl font-bold text-center mb-6">Welcome Back</h1>
        
        {/* Show error message */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            <strong>Error:</strong> {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-gray-700 mb-2">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              required
              disabled={loading}
              placeholder="test@example.com"
            />
          </div>

          <div className="mb-6">
            <label className="block text-gray-700 mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              required
              disabled={loading}
              placeholder="password123"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading ? 'Logging In...' : 'Log In'}
          </button>
        </form>

        <p className="text-center mt-4 text-gray-600">
          Don't have an account?{' '}
          <a href="/signup" className="text-green-600 hover:underline">
            Sign Up
          </a>
        </p>
        
        {/* Debug info (remove in production) */}
        <div className="mt-4 p-4 bg-gray-100 rounded text-xs">
          <strong>Debug Info:</strong><br/>
          API URL: {process.env.REACT_APP_API_URL || 'Not set'}<br/>
          Status: {loading ? 'Loading...' : 'Ready'}
        </div>
      </div>
    </div>
  );
}

export default Login;
