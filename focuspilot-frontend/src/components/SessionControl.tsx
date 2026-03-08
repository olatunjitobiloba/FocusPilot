import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';

interface SessionControlProps {
  onSessionEnd: () => void; // callback to refresh dashboard stats
}

export default function SessionControl({ onSessionEnd }: SessionControlProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0); // seconds
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const notifyExtension = (action: 'startSession' | 'endSession', currentSessionId?: string) => {
    const token = localStorage.getItem('token');
    window.postMessage(
      {
        source: 'focuspilot-web',
        action,
        sessionId: currentSessionId,
        token,
      },
      '*'
    );
  };

  // Timer tick
  useEffect(() => {
    if (isRunning) {
      intervalRef.current = setInterval(() => {
        setElapsed(prev => prev + 1);
      }, 1000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isRunning]);

  // Format seconds → HH:MM:SS
  const formatTime = (secs: number) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  const handleStart = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/sessions/start', { planned_duration: 25 });
      const session = res.data?.session;
      if (!session?.id) {
        throw new Error('Failed to start session');
      }

      setSessionId(session.id);
      setElapsed(0);
      setIsRunning(true);
      notifyExtension('startSession', session.id);
    } catch (err: any) {
      console.error('Session start error:', err);
      setError(err.response?.data?.detail || err.message || 'Could not start session. Check your connection.');
    } finally {
      setLoading(false);
    }
  };

  const handleEnd = async () => {
    if (!sessionId) return;
    setLoading(true);
    setError('');
    try {
      await api.post('/sessions/end', {
        session_id: sessionId,
        focus_score: 8,
        distraction_count: 0
      });
      setIsRunning(false);
      setSessionId(null);
      setElapsed(0);
      notifyExtension('endSession', sessionId);
      onSessionEnd(); // refresh dashboard
    } catch (err: any) {
      console.error('Session end error:', err);
      setError(err.response?.data?.detail || err.message || 'Could not end session. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`rounded-2xl p-6 shadow-sm border-2 transition-all ${
      isRunning
        ? 'bg-green-50 border-green-300'
        : 'bg-white border-gray-100'
    }`}>

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-bold text-gray-800">
            {isRunning ? 'Session Active' : 'Focus Session'}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {isRunning ? 'Stay focused. Agent is watching.' : 'Start a session to begin tracking'}
          </p>
        </div>
        {isRunning && (
          <span className="flex items-center gap-1 text-xs bg-green-100 text-green-600 font-semibold px-3 py-1 rounded-full animate-pulse">
            ● LIVE
          </span>
        )}
      </div>

      {/* Timer Display */}
      <div className={`text-center py-6 rounded-xl mb-4 ${
        isRunning ? 'bg-green-100' : 'bg-gray-50'
      }`}>
        <p className={`text-5xl font-mono font-bold tracking-widest ${
          isRunning ? 'text-green-600' : 'text-gray-300'
        }`}>
          {formatTime(elapsed)}
        </p>
        {isRunning && (
          <p className="text-xs text-green-500 mt-2">
            {Math.floor(elapsed / 60)} minute{Math.floor(elapsed / 60) !== 1 ? 's' : ''} focused
          </p>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-2 rounded-lg mb-4">
          {error}
        </div>
      )}

      {/* Action Button */}
      {!isRunning ? (
        <button
          onClick={handleStart}
          disabled={loading}
          className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white font-bold py-4 rounded-xl text-lg transition-all shadow-md hover:shadow-lg active:scale-95"
        >
          {loading ? 'Starting...' : 'Start Focus Session'}
        </button>
      ) : (
        <button
          onClick={handleEnd}
          disabled={loading}
          className="w-full bg-red-500 hover:bg-red-600 disabled:bg-gray-300 text-white font-bold py-4 rounded-xl text-lg transition-all shadow-md hover:shadow-lg active:scale-95"
        >
          {loading ? 'Ending...' : 'End Session'}
        </button>
      )}

      {/* Session ID (debug info) */}
      {sessionId && (
        <p className="text-center text-xs text-gray-300 mt-3 font-mono">
          ID: {sessionId.slice(0, 8)}...
        </p>
      )}
    </div>
  );
}
