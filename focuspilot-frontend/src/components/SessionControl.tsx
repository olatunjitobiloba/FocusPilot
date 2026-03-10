import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api/client';

interface SessionControlProps {
  onSessionEnd: () => void; // callback to refresh dashboard stats
}

interface ActiveSession {
  id: string;
  start_time: string;
  elapsed_seconds?: number;
  elapsed_minutes?: number;
}

function parseSessionStartTimeToMillis(startTime: string): number {
  if (!startTime) return NaN;

  // If timestamp has no timezone marker, treat it as UTC to match backend logic.
  const hasTimezone = /Z$|[+-]\d{2}:\d{2}$/.test(startTime);
  const normalized = hasTimezone ? startTime : `${startTime}Z`;

  return new Date(normalized).getTime();
}

export default function SessionControl({ onSessionEnd }: SessionControlProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0); // seconds
  const [sessionStartTimeMs, setSessionStartTimeMs] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastAction, setLastAction] = useState<'start' | 'end' | null>(null);
  const [error, setError] = useState('');
  const [orphanedSession, setOrphanedSession] = useState<ActiveSession | null>(null);
  const [showOrphanOptions, setShowOrphanOptions] = useState(false);
  const [hasActiveSessionConflict, setHasActiveSessionConflict] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const loadActiveSession = useCallback(async () => {
    const response = await api.get('/sessions/active');
    if (response.data?.active && response.data?.session?.id) {
      const activeSession = response.data.session as ActiveSession;
      const backendElapsedSeconds = typeof activeSession.elapsed_seconds === 'number'
        ? Math.max(0, activeSession.elapsed_seconds)
        : Math.max(0, (activeSession.elapsed_minutes || 0) * 60);

      const parsedStartMs = parseSessionStartTimeToMillis(activeSession.start_time);
      const effectiveStartMs = Number.isNaN(parsedStartMs)
        ? Date.now() - backendElapsedSeconds * 1000
        : parsedStartMs;

      setSessionId(activeSession.id);
      setSessionStartTimeMs(effectiveStartMs);
      setElapsed(backendElapsedSeconds);
      setIsRunning(true);
      setOrphanedSession(activeSession);
      setShowOrphanOptions(true);
      setHasActiveSessionConflict(true);
      return true;
    }

    setIsRunning(false);
    setSessionId(null);
    setElapsed(0);
    setSessionStartTimeMs(null);
    setOrphanedSession(null);
    setShowOrphanOptions(false);
    setHasActiveSessionConflict(false);
    return false;
  }, []);

  const getActiveSessionOrThrow = useCallback(async (): Promise<ActiveSession> => {
    const response = await api.get('/sessions/active');
    if (response.data?.active && response.data?.session?.id) {
      return response.data.session as ActiveSession;
    }
    throw new Error('No active session found');
  }, []);

  // Check for orphaned session on mount
  useEffect(() => {
    const checkForActiveSession = async () => {
      try {
        await loadActiveSession();
      } catch (err) {
        setOrphanedSession(null);
        setShowOrphanOptions(false);
        setHasActiveSessionConflict(false);
      }
    };

    checkForActiveSession();
  }, [loadActiveSession]);

  // Listen for session events from extension (via postMessage)
  useEffect(() => {
    const handleExtensionMessage = (event: MessageEvent) => {
      if (event.source !== window) return;
      const { source, action } = event.data;

      if (source === 'focuspilot-extension') {
        if (action === 'startSession' || action === 'endSession') {
          setTimeout(() => loadActiveSession(), 100);
        }
      }
    };

    window.addEventListener('message', handleExtensionMessage);
    return () => window.removeEventListener('message', handleExtensionMessage);
  }, [loadActiveSession]);

  const notifyExtension = (
    action: 'startSession' | 'endSession',
    currentSessionId?: string,
    sessionStartTime?: string
  ) => {
    const token = localStorage.getItem('token');
    console.log('Notifying extension:', action, 'Token present?', !!token, token ? `Length: ${token.length}` : 'NO TOKEN');
    window.postMessage(
      {
        source: 'focuspilot-web',
        action,
        sessionId: currentSessionId,
        sessionStartTime,
        token,
      },
      '*'
    );
  };

  // Timer tick (timestamp-based to avoid drift)
  useEffect(() => {
    if (isRunning) {
      const startMs = sessionStartTimeMs ?? (Date.now() - elapsed * 1000);
      intervalRef.current = setInterval(() => {
        setElapsed(Math.max(0, Math.floor((Date.now() - startMs) / 1000)));
      }, 1000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isRunning, sessionStartTimeMs, elapsed]);

  // Silent server resync every 10s while running (keeps parity with extension timer)
  useEffect(() => {
    if (!isRunning || !sessionId) return;

    const resync = setInterval(async () => {
      try {
        const response = await api.get('/sessions/active');
        const activeSession = response.data?.active ? response.data?.session as ActiveSession : null;

        if (!activeSession?.id) {
          setIsRunning(false);
          setSessionId(null);
          setElapsed(0);
          setSessionStartTimeMs(null);
          setOrphanedSession(null);
          setShowOrphanOptions(false);
          setHasActiveSessionConflict(false);
          onSessionEnd();
          return;
        }

        const backendElapsedSeconds = typeof activeSession.elapsed_seconds === 'number'
          ? Math.max(0, activeSession.elapsed_seconds)
          : Math.max(0, (activeSession.elapsed_minutes || 0) * 60);

        const parsedStartMs = parseSessionStartTimeToMillis(activeSession.start_time);
        const effectiveStartMs = Number.isNaN(parsedStartMs)
          ? Date.now() - backendElapsedSeconds * 1000
          : parsedStartMs;

        if (activeSession.id !== sessionId) {
          setSessionId(activeSession.id);
          setIsRunning(true);
        }

        setSessionStartTimeMs(effectiveStartMs);

        setElapsed((prev) => {
          if (Math.abs(prev - backendElapsedSeconds) <= 1) return prev;
          return backendElapsedSeconds;
        });
      } catch {
        // Keep local timer running even if a resync call fails.
      }
    }, 1000);

    return () => clearInterval(resync);
  }, [isRunning, sessionId, onSessionEnd]);

  // Detect sessions started externally (e.g., extension) while dashboard is idle
  useEffect(() => {
    if (isRunning) return;

    const detectExternalStart = setInterval(async () => {
      try {
        await loadActiveSession();
      } catch {
        // ignore transient errors and keep polling
      }
    }, 1000);

    return () => clearInterval(detectExternalStart);
  }, [isRunning, loadActiveSession]);

  // Format seconds → HH:MM:SS
  const formatTime = (secs: number) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  const handleResumeOrphanedSession = async () => {
    setLoading(true);
    setError('');
    try {
      const activeSession = orphanedSession ?? await getActiveSessionOrThrow();

      const backendElapsedSeconds = typeof activeSession.elapsed_seconds === 'number'
        ? Math.max(0, activeSession.elapsed_seconds)
        : Math.max(0, (activeSession.elapsed_minutes || 0) * 60);

      const startTimeMs = parseSessionStartTimeToMillis(activeSession.start_time);
      const calculatedFromStartSeconds = Number.isNaN(startTimeMs)
        ? 0
        : Math.max(0, Math.floor((Date.now() - startTimeMs) / 1000));

      // Backend is the source of truth; fallback to client-side calc only when backend value is missing/zero.
      const resumeElapsedSeconds = backendElapsedSeconds > 0
        ? backendElapsedSeconds
        : calculatedFromStartSeconds;

      const resumeStartMs = Number.isNaN(startTimeMs)
        ? Date.now() - resumeElapsedSeconds * 1000
        : startTimeMs;

      setSessionId(activeSession.id);
      setElapsed(resumeElapsedSeconds);
      setSessionStartTimeMs(resumeStartMs);
      setIsRunning(true);
      setOrphanedSession(activeSession);
      setShowOrphanOptions(false);
      setHasActiveSessionConflict(false);
      notifyExtension('startSession', activeSession.id, activeSession.start_time);
    } catch (err: any) {
      console.error('Error resuming session:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to resume session');
    } finally {
      setLoading(false);
    }
  };

  const handleCleanupOrphanedSession = async () => {
    setLoading(true);
    setError('');
    try {
      if (orphanedSession?.id) {
        await api.post('/sessions/end', {
          session_id: orphanedSession.id,
          focus_score: 0,
          distraction_count: 0
        });
      } else {
        try {
          await api.post('/sessions/cleanup-active');
        } catch (cleanupActiveErr: any) {
          if (cleanupActiveErr?.response?.status === 404) {
            await api.post('/sessions/cleanup/orphaned');
          } else {
            throw cleanupActiveErr;
          }
        }
      }

      setOrphanedSession(null);
      setShowOrphanOptions(false);
      setHasActiveSessionConflict(false);
      notifyExtension('endSession', orphanedSession?.id);
      onSessionEnd();

      try {
        await loadActiveSession();
      } catch {
        setOrphanedSession(null);
        setShowOrphanOptions(false);
        setHasActiveSessionConflict(false);
      }
    } catch (err: any) {
      console.error('Error cleaning up session:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to clean up session');
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    const previousState = {
      isRunning,
      sessionId,
      elapsed,
      sessionStartTimeMs,
      orphanedSession,
      showOrphanOptions,
      hasActiveSessionConflict,
    };

    setLastAction('start');
    setLoading(true);
    setError('');

    setIsRunning(true);
    setElapsed(0);
    setSessionStartTimeMs(Date.now());
    setOrphanedSession(null);
    setShowOrphanOptions(false);
    setHasActiveSessionConflict(false);

    try {
      const res = await api.post('/sessions/start', { planned_duration: 25 });
      const session = res.data?.session;
      if (!session?.id) {
        throw new Error('Failed to start session');
      }

      setSessionId(session.id);
  const parsedStartMs = parseSessionStartTimeToMillis(session.start_time);
  setSessionStartTimeMs(Number.isNaN(parsedStartMs) ? Date.now() : parsedStartMs);
  setElapsed(0);
      setIsRunning(true);
      setOrphanedSession(null);
      setShowOrphanOptions(false);
      setHasActiveSessionConflict(false);
      notifyExtension('startSession', session.id, session.start_time);
    } catch (err: any) {
      setIsRunning(previousState.isRunning);
      setSessionId(previousState.sessionId);
      setElapsed(previousState.elapsed);
      setSessionStartTimeMs(previousState.sessionStartTimeMs);
      setOrphanedSession(previousState.orphanedSession);
      setShowOrphanOptions(previousState.showOrphanOptions);
      setHasActiveSessionConflict(previousState.hasActiveSessionConflict);

      console.error('Session start error:', err);
      const detail = err.response?.data?.detail || err.message || 'Could not start session. Check your connection.';
      if (typeof detail === 'string' && detail.toLowerCase().includes('active session already exists')) {
        setHasActiveSessionConflict(true);
        setShowOrphanOptions(true);
        try {
          const found = await loadActiveSession();
          if (found) {
            setError('You already have an active session. Resume it or end it below.');
          } else {
            setError('You already have an active session. Click Resume Session or End & Cleanup below.');
          }
        } catch {
          setError('You already have an active session. Click Resume Session or End & Cleanup below.');
        }
      } else {
        setError(detail);
      }
    } finally {
      setLoading(false);
      setLastAction(null);
    }
  };

  const handleEnd = async () => {
    const endingSessionId = sessionId;
    if (!endingSessionId) return;

    const previousElapsed = elapsed;
    const previousSessionStartTimeMs = sessionStartTimeMs;

    setLastAction('end');
    setLoading(true);
    setError('');

    setIsRunning(false);
    setSessionId(null);
    setElapsed(0);
    setSessionStartTimeMs(null);
    setOrphanedSession(null);
    setShowOrphanOptions(false);
    setHasActiveSessionConflict(false);

    try {
      await api.post('/sessions/end', {
        session_id: endingSessionId,
        focus_score: 8,
        distraction_count: 0
      });
      notifyExtension('endSession', endingSessionId);
      onSessionEnd(); // refresh dashboard
    } catch (err: any) {
      setIsRunning(true);
      setSessionId(endingSessionId);
      setElapsed(previousElapsed);
      setSessionStartTimeMs(previousSessionStartTimeMs);

      console.error('Session end error:', err);
      setError(err.response?.data?.detail || err.message || 'Could not end session. Try again.');
    } finally {
      setLoading(false);
      setLastAction(null);
      loadActiveSession();
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

      {/* Orphaned Session Alert */}
      {(showOrphanOptions || hasActiveSessionConflict) && !isRunning && (
        <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4 mb-4">
          <p className="text-sm font-semibold text-yellow-800 mb-3">
            ⚠ Active Session Found
          </p>
          <p className="text-xs text-yellow-700 mb-4">
            {orphanedSession
              ? `You have an active session from ${formatTime((orphanedSession.elapsed_minutes || 0) * 60)} ago. Would you like to continue or end it?`
              : 'You already have an active session. Would you like to continue it or end and clean it up?'}
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleResumeOrphanedSession}
              disabled={loading}
              className="flex-1 bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-300 text-white font-semibold py-2 rounded-lg text-sm transition-all"
            >
              {loading ? 'Loading...' : 'Resume Session'}
            </button>
            <button
              onClick={handleCleanupOrphanedSession}
              disabled={loading}
              className="flex-1 bg-red-500 hover:bg-red-600 disabled:bg-gray-300 text-white font-semibold py-2 rounded-lg text-sm transition-all"
            >
              {loading ? 'Cleaning...' : 'End & Cleanup'}
            </button>
          </div>
        </div>
      )}

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
          {loading ? (lastAction === 'end' ? 'Ending...' : 'Starting...') : 'Start Focus Session'}
        </button>
      ) : (
        <button
          onClick={handleEnd}
          disabled={loading}
          className="w-full bg-red-500 hover:bg-red-600 disabled:bg-gray-300 text-white font-bold py-4 rounded-xl text-lg transition-all shadow-md hover:shadow-lg active:scale-95"
        >
          {loading ? (lastAction === 'start' ? 'Starting...' : 'Ending...') : 'End Session'}
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
