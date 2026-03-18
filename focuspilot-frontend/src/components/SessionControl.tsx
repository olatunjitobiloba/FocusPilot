import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api, settingsAPI } from '../api/client';
import AppIcon from './AppIcon';

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
  const [isBreakRunning, setIsBreakRunning] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0); // seconds
  const [breakElapsed, setBreakElapsed] = useState(0); // seconds
  const [sessionDurationMins, setSessionDurationMins] = useState(25);
  const [breakDurationMins, setBreakDurationMins] = useState(5);
  const [selectedCycles, setSelectedCycles] = useState(2);
  const [targetCycles, setTargetCycles] = useState(1);
  const [completedCycles, setCompletedCycles] = useState(0);
  const [isCyclePlanActive, setIsCyclePlanActive] = useState(false);
  const [sessionStartTimeMs, setSessionStartTimeMs] = useState<number | null>(null);
  const [breakStartTimeMs, setBreakStartTimeMs] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastAction, setLastAction] = useState<'start' | 'end' | null>(null);
  const [error, setError] = useState('');
  const [orphanedSession, setOrphanedSession] = useState<ActiveSession | null>(null);
  const [showOrphanOptions, setShowOrphanOptions] = useState(false);
  const [hasActiveSessionConflict, setHasActiveSessionConflict] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const breakIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const autoEndingRef = useRef(false);
  const isBreakRunningRef = useRef(false);
  const breakNotificationSentRef = useRef(false);
  const completedCyclesRef = useRef(0);
  const targetCyclesRef = useRef(1);
  const isCyclePlanActiveRef = useRef(false);

  const clampCycles = (value: number) => {
    if (!Number.isFinite(value)) return 1;
    return Math.min(8, Math.max(1, Math.round(value)));
  };

  const stopBreakPhase = useCallback(() => {
    isBreakRunningRef.current = false;
    setIsBreakRunning(false);
    setBreakElapsed(0);
    setBreakStartTimeMs(null);
  }, []);

  const completeCyclePlan = useCallback(() => {
    console.log(`[Cycle Debug] Cycle plan completed`);
    isCyclePlanActiveRef.current = false;
    completedCyclesRef.current = 0;
    targetCyclesRef.current = 1;
    setIsCyclePlanActive(false);
    setCompletedCycles(0);
    setTargetCycles(1);
    stopBreakPhase();
  }, [stopBreakPhase]);

  const startBreakPhase = useCallback(() => {
    console.log(`[Cycle Debug] Break phase started`);
    isBreakRunningRef.current = true;
    breakNotificationSentRef.current = false;
    setIsBreakRunning(true);
    setBreakElapsed(0);
    setBreakStartTimeMs(Date.now());
  }, []);

  const advanceCycleAfterFocusEnd = useCallback((source: 'dashboard' | 'extension') => {
    if (!isCyclePlanActiveRef.current || isBreakRunningRef.current) {
      return;
    }

    const nextCompleted = completedCyclesRef.current + 1;
    completedCyclesRef.current = nextCompleted;
    setCompletedCycles(nextCompleted);

    console.log(`[Cycle Debug] Focus session ended (${source}). Completed: ${nextCompleted}, Target: ${targetCyclesRef.current}`);

    if (nextCompleted < targetCyclesRef.current) {
      console.log(`[Cycle Debug] Starting break phase (${nextCompleted}/${targetCyclesRef.current})`);
      startBreakPhase();
      return;
    }

    console.log(`[Cycle Debug] All cycles completed. Ending cycle plan.`);
    completeCyclePlan();
  }, [completeCyclePlan, startBreakPhase]);

  useEffect(() => {
    completedCyclesRef.current = completedCycles;
  }, [completedCycles]);

  useEffect(() => {
    targetCyclesRef.current = targetCycles;
  }, [targetCycles]);

  useEffect(() => {
    isCyclePlanActiveRef.current = isCyclePlanActive;
  }, [isCyclePlanActive]);

  const loadDurations = useCallback(async () => {
    try {
      const response = await settingsAPI.get();
      const configuredSessionDuration = Number(response.data?.session_duration_mins);
      const configuredBreakDuration = Number(response.data?.break_duration_mins);
      const safeSessionDuration = Number.isFinite(configuredSessionDuration) && configuredSessionDuration > 0
        ? configuredSessionDuration
        : 25;
      const safeBreakDuration = Number.isFinite(configuredBreakDuration) && configuredBreakDuration > 0
        ? configuredBreakDuration
        : 5;

      setSessionDurationMins(safeSessionDuration);
      setBreakDurationMins(safeBreakDuration);
      return {
        sessionDurationMins: safeSessionDuration,
        breakDurationMins: safeBreakDuration,
      };
    } catch {
      setSessionDurationMins(25);
      setBreakDurationMins(5);
      return {
        sessionDurationMins: 25,
        breakDurationMins: 5,
      };
    }
  }, []);

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
        await loadDurations();
        await loadActiveSession();
      } catch (err) {
        setOrphanedSession(null);
        setShowOrphanOptions(false);
        setHasActiveSessionConflict(false);
      }
    };

    checkForActiveSession();
  }, [loadActiveSession, loadDurations]);

  // Listen for session events from extension (via postMessage)
  useEffect(() => {
    const handleExtensionMessage = (event: MessageEvent) => {
      if (event.source !== window) return;
      const { source, action } = event.data;

      if (source === 'focuspilot-extension') {
        if (action === 'endSession') {
          // Apply end-state instantly for snappy UX, then verify with backend.
          setIsRunning(false);
          setSessionId(null);
          setElapsed(0);
          setSessionStartTimeMs(null);
          setOrphanedSession(null);
          setShowOrphanOptions(false);
          setHasActiveSessionConflict(false);
          autoEndingRef.current = false;
          onSessionEnd();

          advanceCycleAfterFocusEnd('extension');

          setTimeout(() => {
            void loadActiveSession().catch(() => {
              // Ignore transient backend errors during post-end reconciliation.
            });
          }, 300);
          return;
        }

        if (action === 'startSession') {
          setTimeout(() => {
            void loadActiveSession().catch(() => {
              // Ignore transient backend errors while syncing external session start.
            });
          }, 100);
        }
      }
    };

    window.addEventListener('message', handleExtensionMessage);
    return () => window.removeEventListener('message', handleExtensionMessage);
  }, [advanceCycleAfterFocusEnd, loadActiveSession, onSessionEnd]);

  const notifyExtension = useCallback((
    action: 'startSession' | 'endSession' | 'notifyBreakStarted' | 'notifyBreakEnded',
    currentSessionId?: string,
    sessionStartTime?: string,
    plannedDurationMins?: number
  ) => {
    const token = localStorage.getItem('token');
    console.log('Notifying extension:', action, 'Token present?', !!token, token ? `Length: ${token.length}` : 'NO TOKEN');
    window.postMessage(
      {
        source: 'focuspilot-web',
        action,
        sessionId: currentSessionId,
        sessionStartTime,
        sessionDurationMins: plannedDurationMins,
        token,
      },
      '*'
    );
  }, []);

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

  // Break timer tick
  useEffect(() => {
    if (isBreakRunning) {
      const startMs = breakStartTimeMs ?? (Date.now() - breakElapsed * 1000);
      breakIntervalRef.current = setInterval(() => {
        setBreakElapsed(Math.max(0, Math.floor((Date.now() - startMs) / 1000)));
      }, 1000);
    } else {
      if (breakIntervalRef.current) clearInterval(breakIntervalRef.current);
    }

    return () => {
      if (breakIntervalRef.current) clearInterval(breakIntervalRef.current);
    };
  }, [breakElapsed, breakStartTimeMs, isBreakRunning]);

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
    }, 10000);

    return () => clearInterval(resync);
  }, [isRunning, sessionId, onSessionEnd]);

  useEffect(() => {
    if (!isRunning) {
      autoEndingRef.current = false;
    }
  }, [isRunning]);

  // Detect sessions started externally (e.g., extension) while dashboard is idle
  useEffect(() => {
    if (isRunning) return;

    const detectExternalStart = setInterval(async () => {
      try {
        await loadActiveSession();
      } catch {
        // ignore transient errors and keep polling
      }
    }, 15000);

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
      const durations = await loadDurations();

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
      notifyExtension('startSession', activeSession.id, activeSession.start_time, durations.sessionDurationMins);
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

  const startFocusSession = useCallback(async () => {
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
      const durations = await loadDurations();
      const res = await api.post('/sessions/start', { planned_duration: durations.sessionDurationMins });
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
      autoEndingRef.current = false;
      notifyExtension('startSession', session.id, session.start_time, durations.sessionDurationMins);
      console.log(`[Cycle Debug] Focus session started (ID: ${session.id})`);
      return true;
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
      return false;
    } finally {
      setLoading(false);
      setLastAction(null);
    }
  }, [
    hasActiveSessionConflict,
    isRunning,
    loadActiveSession,
    loadDurations,
    notifyExtension,
    orphanedSession,
    sessionId,
    sessionStartTimeMs,
    showOrphanOptions,
    elapsed,
  ]);

  const handleStart = async () => {
    completeCyclePlan();
    const cycles = clampCycles(selectedCycles);
    targetCyclesRef.current = cycles;
    completedCyclesRef.current = 0;
    isCyclePlanActiveRef.current = true;
    setTargetCycles(cycles);
    setCompletedCycles(0);
    setIsCyclePlanActive(true);
    console.log(`[Cycle Debug] Starting cycle plan with ${cycles} cycles`);

    const started = await startFocusSession();
    if (!started) {
      completeCyclePlan();
    }
  };

  const handleEnd = useCallback(async (advanceCycle = false) => {
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

      if (advanceCycle) {
        advanceCycleAfterFocusEnd('dashboard');
      } else {
        console.log(`[Cycle Debug] Manual end or cycle plan inactive. Ending.`);
        completeCyclePlan();
      }
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
      void loadActiveSession().catch(() => {
        // Avoid uncaught promise rejections when backend is temporarily unavailable.
      });
    }
  }, [
    completeCyclePlan,
    elapsed,
    advanceCycleAfterFocusEnd,
    loadActiveSession,
    notifyExtension,
    onSessionEnd,
    sessionId,
    sessionStartTimeMs,
  ]);

  const handleStopCyclePlan = () => {
    completeCyclePlan();
    setError('');
  };

  const startNextFocusAfterBreak = useCallback(async () => {
    if (!isCyclePlanActiveRef.current) {
      stopBreakPhase();
      return;
    }

    if (completedCyclesRef.current >= targetCyclesRef.current) {
      completeCyclePlan();
      return;
    }

    console.log(`[Cycle Debug] Break ended. Starting next focus session.`);
    stopBreakPhase();
    notifyExtension('notifyBreakEnded');
    const started = await startFocusSession();
    if (!started) {
      completeCyclePlan();
    }
  }, [completeCyclePlan, notifyExtension, startFocusSession, stopBreakPhase]);

  useEffect(() => {
    if (!isRunning || !sessionId || loading) return;
    if (elapsed < sessionDurationMins * 60) return;
    if (autoEndingRef.current) return;

    console.log(`[Cycle Debug] Focus session duration (${sessionDurationMins} min) reached. Auto-ending...`);
    autoEndingRef.current = true;
    handleEnd(true);
  }, [elapsed, handleEnd, isRunning, loading, sessionDurationMins, sessionId]);

  useEffect(() => {
    if (!isBreakRunning || !isCyclePlanActive || loading) return;
    if (breakElapsed < breakDurationMins * 60) return;

    console.log(`[Cycle Debug] Break duration (${breakDurationMins} min) reached. Auto-ending break...`);
    void startNextFocusAfterBreak();
  }, [breakDurationMins, breakElapsed, isBreakRunning, isCyclePlanActive, loading, startNextFocusAfterBreak]);

  useEffect(() => {
    if (!isBreakRunning || !isCyclePlanActive) return;
    if (breakNotificationSentRef.current) return;

    console.log(`[Cycle Debug] Break started - sending notification`);
    breakNotificationSentRef.current = true;
    notifyExtension('notifyBreakStarted');
  }, [isBreakRunning, isCyclePlanActive, notifyExtension]);

  const displayedElapsed = isBreakRunning ? breakElapsed : elapsed;
  const phaseLabel = isBreakRunning ? 'Break Time' : (isRunning ? 'Session Active' : 'Focus Session');
  const phaseSubLabel = isBreakRunning
    ? 'Blocked sites are temporarily unblocked.'
    : (isRunning ? 'Stay focused. Agent is watching.' : 'Start a cycle plan to begin tracking');

  return (
    <div className={`rounded-2xl p-6 shadow-sm border-2 transition-all ${
      isRunning
        ? 'bg-green-50 border-green-300'
        : isBreakRunning
          ? 'bg-green-50 border-green-200'
        : 'bg-white border-gray-100'
    }`}>

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-bold text-gray-800">
            {phaseLabel}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {phaseSubLabel}
          </p>
        </div>
        {(isRunning || isBreakRunning) && (
          <span className="flex items-center gap-1 text-xs bg-green-100 text-green-600 font-semibold px-3 py-1 rounded-full animate-pulse">
            ● LIVE
          </span>
        )}
      </div>

      {/* Orphaned Session Alert */}
      {(showOrphanOptions || hasActiveSessionConflict) && !isRunning && (
        <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4 mb-4">
          <p className="text-sm font-semibold text-yellow-800 mb-3 flex items-center gap-2">
            <AppIcon name="warning" className="text-yellow-700" size={16} />
            Active Session Found
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
          isRunning ? 'text-green-600' : isBreakRunning ? 'text-green-500' : 'text-gray-300'
        }`}>
          {formatTime(displayedElapsed)}
        </p>
        {(isRunning || isBreakRunning) && (
          <p className={`text-xs mt-2 ${isBreakRunning ? 'text-green-500' : 'text-green-500'}`}>
            {Math.floor(displayedElapsed / 60)} minute{Math.floor(displayedElapsed / 60) !== 1 ? 's' : ''}
            {isBreakRunning ? ' on break' : ' focused'}
          </p>
        )}
      </div>

      {/* Cycle Controls */}
      {!isRunning && !isBreakRunning && (
        <div className="mb-4 rounded-xl border border-gray-200 bg-gray-50 p-4">
          <label htmlFor="cycle-count" className="block text-sm font-semibold text-gray-700 mb-2">
            How many focus cycles do you want?
          </label>
          <div className="flex items-center gap-3">
            <input
              id="cycle-count"
              type="number"
              min={1}
              max={8}
              value={selectedCycles}
              onChange={(e) => setSelectedCycles(clampCycles(Number(e.target.value)))}
              className="w-24 rounded-lg border border-gray-300 px-3 py-2 text-gray-700 focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <p className="text-xs text-gray-500">
              1 cycle = {sessionDurationMins} min focus + {breakDurationMins} min break
            </p>
          </div>
        </div>
      )}

      {isCyclePlanActive && (
        <div className="mb-4 rounded-xl border border-green-200 bg-green-50 px-4 py-3">
          <p className="text-sm font-semibold text-green-700">
            Cycle progress: {Math.min(completedCycles + (isRunning ? 1 : 0), targetCycles)} / {targetCycles}
          </p>
          <p className="text-xs text-green-600 mt-1">
            {isBreakRunning ? 'Break in progress. Next focus session will start automatically.' : 'Focus is active. Break starts automatically when this session ends.'}
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-2 rounded-lg mb-4">
          {error}
        </div>
      )}

      {/* Action Button */}
      {!isRunning && !isBreakRunning ? (
        <button
          onClick={handleStart}
          disabled={loading}
          className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white font-bold py-4 rounded-xl text-lg transition-all shadow-md hover:shadow-lg active:scale-95"
        >
          {loading ? (lastAction === 'end' ? 'Ending...' : 'Starting...') : `Start ${clampCycles(selectedCycles)} Focus Cycle${clampCycles(selectedCycles) > 1 ? 's' : ''}`}
        </button>
      ) : isRunning ? (
        <button
          onClick={() => {
            void handleEnd(false);
          }}
          disabled={loading}
          className="w-full bg-red-500 hover:bg-red-600 disabled:bg-gray-300 text-white font-bold py-4 rounded-xl text-lg transition-all shadow-md hover:shadow-lg active:scale-95"
        >
          {loading ? (lastAction === 'start' ? 'Starting...' : 'Ending...') : 'End Session'}
        </button>
      ) : (
        <button
          onClick={handleStopCyclePlan}
          disabled={loading}
          className="w-full bg-red-500 hover:bg-red-600 disabled:bg-gray-300 text-white font-bold py-4 rounded-xl text-lg transition-all shadow-md hover:shadow-lg active:scale-95"
        >
          Stop Cycle Plan
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
