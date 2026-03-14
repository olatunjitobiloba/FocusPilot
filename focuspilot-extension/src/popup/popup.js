// popup.js
const API_URL = "https://OlatunjiTobi-focuspilot-agent.hf.space";

// DOM elements
const authView = document.getElementById('authView');
const dashboardView = document.getElementById('dashboardView');
const loginBtn = document.getElementById('loginBtn');
const signupBtn = document.getElementById('signupBtn');
const startSessionBtn = document.getElementById('startSessionBtn');
const endSessionBtn = document.getElementById('endSessionBtn');
const logoutBtn = document.getElementById('logoutBtn');

// Timer state
let timerInterval = null;
let timerAnimationFrame = null;
let timerResyncInterval = null;
let authResetInProgress = false;
let refreshInProgress = null;
let sessionAutoEndInProgress = false;
let sessionStartInProgress = false;
let sessionStateRequestCounter = 0;

async function requestTokenSyncFromActiveTab() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const activeTab = tabs?.[0];
      if (!activeTab?.id) {
        resolve(false);
        return;
      }

      chrome.tabs.sendMessage(activeTab.id, { action: 'focuspilotRequestTokenSync' }, (response) => {
        if (chrome.runtime.lastError) {
          resolve(false);
          return;
        }

        resolve(Boolean(response?.success));
      });
    });
  });
}

function showAuth() {
  authView.style.display = 'block';
  dashboardView.classList.remove('active');
}

async function showDashboard(user) {
  authView.style.display = 'none';
  dashboardView.classList.add('active');
  hydrateDashboardFromCache();
  loadStats();
  await loadUserSettings();
  await loadSessionState();
}

async function loadUserSettings() {
  try {
    const response = await fetchWithAuth(`${API_URL}/settings`);
    if (response && response.ok) {
      const settings = await response.json();
      await setStorage({ userSettings: settings });
      return settings;
    }
  } catch (error) {
    console.error('Failed to load user settings:', error);
  }
  return null;
}

function setSessionButtons(isActive) {
  startSessionBtn.style.display = isActive ? 'none' : 'block';
  endSessionBtn.style.display = isActive ? 'block' : 'none';
}

function getStorage(keys) {
  return new Promise((resolve) => {
    chrome.storage.local.get(keys, (result) => resolve(result));
  });
}

async function initializeAuthState() {
  const initial = await getStorage(['token', 'refresh_token', 'user', 'activeSessionId', 'sessionStartTime']);
  if (initial.token || initial.refresh_token) {
    await showDashboard(initial.user);
    return;
  }

  await requestTokenSyncFromActiveTab();

  const afterSync = await getStorage(['token', 'refresh_token', 'user', 'activeSessionId', 'sessionStartTime']);
  if (afterSync.token || afterSync.refresh_token || afterSync.activeSessionId || afterSync.sessionStartTime) {
    await showDashboard(afterSync.user);
    return;
  }

  showAuth();
}

initializeAuthState();

function setStorage(items) {
  return new Promise((resolve) => {
    chrome.storage.local.set(items, () => resolve());
  });
}

function removeStorage(keys) {
  return new Promise((resolve) => {
    chrome.storage.local.remove(keys, () => resolve());
  });
}

function isUnauthorizedStatus(status) {
  return status === 401 || status === 403;
}

async function handleAuthExpired() {
  if (authResetInProgress) return;
  authResetInProgress = true;

  const { activeSessionId, sessionStartTime } = await getStorage(['activeSessionId', 'sessionStartTime']);
  const hasActiveSession = Boolean(activeSessionId || sessionStartTime);

  // During an already-running session, keep dashboard mode and timer state even if token sync lags.
  if (hasActiveSession) {
    await removeStorage([
      'token',
      'refresh_token',
      'user',
      'cachedDailyFocusMinutes',
      'cachedStreak'
    ]);
    setSessionButtons(true);
    authResetInProgress = false;
    return;
  }

  // Attempt to recover auth from the currently active FocusPilot tab
  // before switching the popup back to login/signup.
  await requestTokenSyncFromActiveTab();
  const recovered = await getStorage(['token', 'refresh_token', 'user']);
  if (recovered.token || recovered.refresh_token) {
    await showDashboard(recovered.user);
    authResetInProgress = false;
    return;
  }

  await removeStorage([
    'token',
    'refresh_token',
    'user',
    'activeSessionId',
    'sessionStartTime',
    'blocksPrevented',
    'cachedDailyFocusMinutes',
    'cachedStreak'
  ]);

  setSessionButtons(false);
  stopPopupTimer();
  showAuth();
  authResetInProgress = false;
}

async function refreshAccessToken() {
  const { refresh_token } = await getStorage(['refresh_token']);
  if (!refresh_token) return null;

  if (!refreshInProgress) {
    refreshInProgress = fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ refresh_token })
    })
      .then(async (response) => {
        if (!response.ok) {
          return null;
        }

        const data = await response.json();
        const newToken = data?.access_token;
        const newRefreshToken = data?.refresh_token;
        const user = data?.user;

        if (!newToken) {
          return null;
        }

        const storagePayload = { token: newToken };
        if (newRefreshToken) storagePayload.refresh_token = newRefreshToken;
        if (user) storagePayload.user = user;
        await setStorage(storagePayload);

        return newToken;
      })
      .catch(() => null)
      .finally(() => {
        refreshInProgress = null;
      });
  }

  return refreshInProgress;
}

async function fetchWithAuth(url, options = {}, allowRefresh = true) {
  const { token } = await getStorage(['token']);
  let accessToken = token;

  if (!accessToken) {
    accessToken = await refreshAccessToken();
  }

  if (!accessToken) {
    await handleAuthExpired();
    return null;
  }

  const headers = {
    ...(options.headers || {}),
    'Authorization': `Bearer ${accessToken}`,
  };

  let response = await fetch(url, {
    ...options,
    headers,
  });

  if (allowRefresh && isUnauthorizedStatus(response.status)) {
    const refreshedToken = await refreshAccessToken();
    if (!refreshedToken) {
      await handleAuthExpired();
      return response;
    }

    response = await fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {}),
        'Authorization': `Bearer ${refreshedToken}`,
      },
    });
  }

  if (isUnauthorizedStatus(response.status)) {
    await handleAuthExpired();
  }

  return response;
}

function parseSessionStartTimeToMillis(startTime) {
  if (!startTime) return Date.now();

  const hasTimezone = /Z$|[+-]\d{2}:\d{2}$/.test(startTime);
  const normalized = hasTimezone ? startTime : `${startTime}Z`;
  const parsed = new Date(normalized).getTime();

  return Number.isNaN(parsed) ? Date.now() : parsed;
}

function isActiveSessionExistsError(rawValue, status) {
  if (status === 409) return true;
  const normalized = String(rawValue || '').toLowerCase();
  return normalized.includes('active session already exists');
}

function formatFocusMinutes(totalMinutes) {
  const safeMinutes = Math.max(0, Math.round(totalMinutes || 0));
  return `${Math.floor(safeMinutes / 60)}h ${safeMinutes % 60}m`;
}

async function hydrateDashboardFromCache() {
  try {
    const {
      cachedDailyFocusMinutes,
      cachedStreak,
      activeSessionId,
      sessionStartTime,
    } = await getStorage([
      'cachedDailyFocusMinutes',
      'cachedStreak',
      'activeSessionId',
      'sessionStartTime',
    ]);

    if (typeof cachedDailyFocusMinutes === 'number') {
      document.getElementById('focusTime').textContent = formatFocusMinutes(cachedDailyFocusMinutes);
    }

    if (typeof cachedStreak === 'number') {
      document.getElementById('streak').textContent = `${cachedStreak} days`;
    }

    if (activeSessionId && sessionStartTime) {
      const { sessionDurationMins } = await getStorage(['sessionDurationMins']);
      setSessionButtons(true);
      startPopupTimer(sessionStartTime, sessionDurationMins);
    }
  } catch (error) {
    console.error('Failed to hydrate popup from cache:', error);
  }
}

function startPopupTimer(sessionStartTime, durationMins) {
  const timerSection = document.getElementById('sessionTimerSection');
  const timerDisplay = document.getElementById('sessionTimer');

  if (timerSection) timerSection.classList.add('active');

  // Clear any existing intervals/frames
  if (timerInterval) clearInterval(timerInterval);
  if (timerAnimationFrame) cancelAnimationFrame(timerAnimationFrame);
  sessionAutoEndInProgress = false;

  // Update immediately
  const updateTimer = () => {
    if (!timerDisplay) return;
    const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);

    // Auto-end session when planned duration is reached
    if (durationMins && elapsed >= durationMins * 60 && !sessionAutoEndInProgress) {
      sessionAutoEndInProgress = true;
      endSession();
      return;
    }

    const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const seconds = (elapsed % 60).toString().padStart(2, '0');
    timerDisplay.textContent = `${minutes}:${seconds}`;
    
    timerAnimationFrame = requestAnimationFrame(updateTimer);
  };

  updateTimer();
}

function stopPopupTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  if (timerAnimationFrame) {
    cancelAnimationFrame(timerAnimationFrame);
    timerAnimationFrame = null;
  }
  if (timerResyncInterval) {
    clearInterval(timerResyncInterval);
    timerResyncInterval = null;
  }
  sessionAutoEndInProgress = false;
  const timerSection = document.getElementById('sessionTimerSection');
  if (timerSection) timerSection.classList.remove('active');
}

async function loadSessionState() {
  const requestId = ++sessionStateRequestCounter;

  try {
    const response = await fetchWithAuth(`${API_URL}/sessions/active`);

    if (!response) {
      if (requestId !== sessionStateRequestCounter || sessionStartInProgress) {
        return;
      }

      const { activeSessionId, sessionStartTime, sessionDurationMins } = await getStorage([
        'activeSessionId',
        'sessionStartTime',
        'sessionDurationMins'
      ]);

      if (activeSessionId && sessionStartTime) {
        setSessionButtons(true);
        startPopupTimer(sessionStartTime, sessionDurationMins);
      } else {
        setSessionButtons(false);
        stopPopupTimer();
      }
      return;
    }

    if (!response.ok) {
      if (requestId !== sessionStateRequestCounter || sessionStartInProgress) {
        return;
      }

      const { activeSessionId, sessionStartTime, sessionDurationMins } = await getStorage([
        'activeSessionId',
        'sessionStartTime',
        'sessionDurationMins'
      ]);

      if (activeSessionId && sessionStartTime) {
        setSessionButtons(true);
        startPopupTimer(sessionStartTime, sessionDurationMins);
      } else {
        setSessionButtons(false);
        stopPopupTimer();
      }
      return;
    }

    const data = await response.json();
    if (requestId !== sessionStateRequestCounter) {
      return;
    }

    if (data?.active && data?.session?.id) {
      const parsedSessionStartTime = parseSessionStartTimeToMillis(data.session.start_time);
      const { sessionDurationMins } = await getStorage(['sessionDurationMins']);
      await setStorage({
        activeSessionId: data.session.id,
        sessionStartTime: parsedSessionStartTime
      });
      setSessionButtons(true);
      startPopupTimer(parsedSessionStartTime, sessionDurationMins);
    } else {
      const {
        activeSessionId: localActiveSessionId,
        sessionStartTime: localSessionStartTime,
        userSettings,
      } = await getStorage(['activeSessionId', 'sessionStartTime', 'userSettings']);

      if (
        requestId !== sessionStateRequestCounter ||
        sessionStartInProgress ||
        localActiveSessionId ||
        localSessionStartTime
      ) {
        return;
      }

      await removeStorage(['activeSessionId', 'sessionStartTime']);
      setSessionButtons(false);
      stopPopupTimer();

      // Auto-start session if the setting is enabled
      if (userSettings?.auto_start_sessions) {
        await startSession();
      }
    }
  } catch (error) {
    console.error('Failed to load session state:', error);
    if (requestId !== sessionStateRequestCounter || sessionStartInProgress) {
      return;
    }

    const { activeSessionId, sessionStartTime, sessionDurationMins } = await getStorage([
      'activeSessionId',
      'sessionStartTime',
      'sessionDurationMins'
    ]);

    if (activeSessionId && sessionStartTime) {
      setSessionButtons(true);
      startPopupTimer(sessionStartTime, sessionDurationMins);
      return;
    }

    setSessionButtons(false);
    stopPopupTimer();
  }
}

// Login button
loginBtn.addEventListener('click', () => {
  chrome.tabs.create({ url: 'https://focuspilot.vercel.app/login' });
});

// Signup button
signupBtn.addEventListener('click', () => {
  chrome.tabs.create({ url: 'https://focuspilot.vercel.app/signup' });
});

// Start session
startSessionBtn.addEventListener('click', () => {
  startSession();
});

// End session
endSessionBtn.addEventListener('click', () => {
  endSession();
});

// Logout
logoutBtn.addEventListener('click', () => {
  chrome.storage.local.remove(['token', 'refresh_token', 'user', 'activeSessionId', 'sessionStartTime', 'blocksPrevented'], () => {
    showAuth();
  });
});

// Load stats
async function loadStats() {
  try {
    const [dailyResponse, weeklyResponse] = await Promise.all([
      fetchWithAuth(`${API_URL}/stats/daily`),
      fetchWithAuth(`${API_URL}/stats/weekly`)
    ]);

    if (!dailyResponse || !weeklyResponse) {
      return;
    }

    if (isUnauthorizedStatus(dailyResponse.status) || isUnauthorizedStatus(weeklyResponse.status)) {
      await handleAuthExpired();
      return;
    }

    if (dailyResponse.ok) {
      const stats = await dailyResponse.json();
      const focusMinutes = stats.total_focus_minutes || 0;
      document.getElementById('focusTime').textContent = formatFocusMinutes(focusMinutes);
      await setStorage({ cachedDailyFocusMinutes: focusMinutes });
    }

    if (weeklyResponse.ok) {
      const weekly = await weeklyResponse.json();
      const currentStreak = weekly.current_streak || 0;
      document.getElementById('streak').textContent = `${currentStreak} days`;
      await setStorage({ cachedStreak: currentStreak });
    }
  } catch (error) {
    console.error('Failed to load stats:', error);
  }
}

async function startSession() {
  if (sessionStartInProgress) return;
  sessionStartInProgress = true;
  if (startSessionBtn) startSessionBtn.disabled = true;

  try {
    const response = await fetchWithAuth(`${API_URL}/sessions/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ planned_duration: (await getStorage(['userSettings'])).userSettings?.session_duration_mins || 25 })
    });

    if (!response) {
      alert('Please log in first.');
      return;
    }

    if (!response.ok) {
      if (isUnauthorizedStatus(response.status)) {
        await handleAuthExpired();
        alert('Session expired. Please log in again.');
        return;
      }
      const errorText = await response.text();
      if (isActiveSessionExistsError(errorText, response.status)) {
        // A session already exists (often from auto-start). Sync popup UI instead of showing a false failure.
        await loadSessionState();
        return;
      }
      throw new Error(errorText || 'Failed to start session');
    }

    const data = await response.json();
    const session = data?.session;
    const sessionId = session?.id;

    if (!sessionId) {
      throw new Error('Session ID missing from server response');
    }

    const parsedSessionStartTime = parseSessionStartTimeToMillis(session?.start_time);
    let { token: latestToken } = await getStorage(['token']);
    if (!latestToken) {
      latestToken = await refreshAccessToken();
    }

    // Notify dashboard immediately
    window.top?.postMessage({
      source: 'focuspilot-extension',
      action: 'startSession'
    }, '*');

    const { userSettings: settingsForSession } = await getStorage(['userSettings']);
    const durationMins = settingsForSession?.session_duration_mins || 25;
    await setStorage({ sessionDurationMins: durationMins });

    await setStorage({
      activeSessionId: sessionId,
      sessionStartTime: parsedSessionStartTime,
      blocksPrevented: 0
    });
    setSessionButtons(true);
    startPopupTimer(parsedSessionStartTime, durationMins);
    loadStats();

    chrome.runtime.sendMessage(
      { action: 'startSession', sessionId, token: latestToken, sessionStartTime: parsedSessionStartTime, sessionDurationMins: durationMins },
      async (runtimeResponse) => {
      if (runtimeResponse && runtimeResponse.success) {
        return;
      } else {
        const runtimeError = chrome.runtime.lastError?.message;
        const reason = runtimeResponse?.error || runtimeError || 'Unknown error';
        const { activeSessionId: currentActiveSessionId } = await getStorage(['activeSessionId']);

        if (
          currentActiveSessionId &&
          typeof reason === 'string' &&
          reason.toLowerCase().includes('not authenticated')
        ) {
          // Session start succeeded and UI is active; ignore auth-race warning from background.
          return;
        }

        console.error('Background startSession failed:', reason);
        alert(`Session started, but blocking could not be enabled: ${reason}`);
      }
      }
    );
  } catch (error) {
    if (isActiveSessionExistsError(error?.message, undefined)) {
      await loadSessionState();
      return;
    }

    console.error('Failed to start session:', error);
    alert('Could not start session. Please try again.');
  } finally {
    sessionStartInProgress = false;
    if (startSessionBtn) startSessionBtn.disabled = false;
  }
}

async function endSession() {
  try {
    const { activeSessionId } = await getStorage(['activeSessionId']);

    // Optimistic UI update for instant feedback
    window.top?.postMessage({
      source: 'focuspilot-extension',
      action: 'endSession'
    }, '*');

    chrome.runtime.sendMessage({ action: 'endSession' }, async () => {
      await removeStorage(['activeSessionId', 'sessionStartTime']);
      setSessionButtons(false);
      stopPopupTimer();
    });

    let sessionId = activeSessionId;

    if (!sessionId) {
      const activeResponse = await fetchWithAuth(`${API_URL}/sessions/active`);
      if (!activeResponse) {
        alert('Please log in first.');
        return;
      }
      if (isUnauthorizedStatus(activeResponse.status)) {
        await handleAuthExpired();
        alert('Session expired. Please log in again.');
        return;
      }
      if (activeResponse.ok) {
        const activeData = await activeResponse.json();
        sessionId = activeData?.session?.id;
      }
    }

    if (sessionId) {
      const endResponse = await fetchWithAuth(`${API_URL}/sessions/end`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          focus_score: 8,
          distraction_count: 0
        })
      });

      if (!endResponse) {
        alert('Please log in first.');
        return;
      }

      if (isUnauthorizedStatus(endResponse.status)) {
        await handleAuthExpired();
        alert('Session expired. Please log in again.');
        return;
      }
    }

    loadStats();
  } catch (error) {
    console.error('Failed to end session:', error);
    alert('Could not end session. Please try again.');
  }
}

// Handle auto-end notification from background alarm
chrome.runtime.onMessage.addListener((message) => {
  if (message.action === 'sessionAutoEnded') {
    stopPopupTimer();
    setSessionButtons(false);
    loadStats();
  }
});
