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

// Check if user is logged in
chrome.storage.local.get(['token', 'user'], (result) => {
  if (result.token) {
    showDashboard(result.user);
  } else {
    showAuth();
  }
});

function showAuth() {
  authView.style.display = 'block';
  dashboardView.classList.remove('active');
}

function showDashboard(user) {
  authView.style.display = 'none';
  dashboardView.classList.add('active');
  hydrateDashboardFromCache();
  loadStats();
  loadSessionState();
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

function parseSessionStartTimeToMillis(startTime) {
  if (!startTime) return Date.now();

  const hasTimezone = /Z$|[+-]\d{2}:\d{2}$/.test(startTime);
  const normalized = hasTimezone ? startTime : `${startTime}Z`;
  const parsed = new Date(normalized).getTime();

  return Number.isNaN(parsed) ? Date.now() : parsed;
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
      setSessionButtons(true);
      startPopupTimer(sessionStartTime);
    }
  } catch (error) {
    console.error('Failed to hydrate popup from cache:', error);
  }
}

function startPopupTimer(sessionStartTime) {
  const timerSection = document.getElementById('sessionTimerSection');
  const timerDisplay = document.getElementById('sessionTimer');

  if (timerSection) timerSection.classList.add('active');

  // Clear any existing intervals/frames
  if (timerInterval) clearInterval(timerInterval);
  if (timerAnimationFrame) cancelAnimationFrame(timerAnimationFrame);

  // Update immediately
  const updateTimer = () => {
    if (!timerDisplay) return;
    const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
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
  const timerSection = document.getElementById('sessionTimerSection');
  if (timerSection) timerSection.classList.remove('active');
}

async function loadSessionState() {
  try {
    const { token } = await getStorage(['token']);
    if (!token) {
      setSessionButtons(false);
      stopPopupTimer();
      return;
    }

    const response = await fetch(`${API_URL}/sessions/active`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      setSessionButtons(false);
      stopPopupTimer();
      return;
    }

    const data = await response.json();
    if (data?.active && data?.session?.id) {
      const parsedSessionStartTime = parseSessionStartTimeToMillis(data.session.start_time);
      await setStorage({
        activeSessionId: data.session.id,
        sessionStartTime: parsedSessionStartTime
      });
      setSessionButtons(true);
      startPopupTimer(parsedSessionStartTime);
    } else {
      await removeStorage(['activeSessionId', 'sessionStartTime']);
      setSessionButtons(false);
      stopPopupTimer();
    }
  } catch (error) {
    console.error('Failed to load session state:', error);
    setSessionButtons(false);
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
  chrome.storage.local.remove(['token', 'user'], () => {
    showAuth();
  });
});

// Load stats
async function loadStats() {
  try {
    const { token } = await getStorage(['token']);
    const [dailyResponse, weeklyResponse] = await Promise.all([
      fetch(`${API_URL}/stats/daily`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }),
      fetch(`${API_URL}/stats/weekly`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
    ]);

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
  try {
    const { token } = await getStorage(['token']);
    if (!token) {
      alert('Please log in first.');
      return;
    }

    const response = await fetch(`${API_URL}/sessions/start`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ planned_duration: 25 })
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || 'Failed to start session');
    }

    const data = await response.json();
    const session = data?.session;
    const sessionId = session?.id;

    if (!sessionId) {
      throw new Error('Session ID missing from server response');
    }

    const parsedSessionStartTime = parseSessionStartTimeToMillis(session?.start_time);

    // Notify dashboard immediately
    window.top?.postMessage({
      source: 'focuspilot-extension',
      action: 'startSession'
    }, '*');

    chrome.runtime.sendMessage(
      { action: 'startSession', sessionId, token, sessionStartTime: parsedSessionStartTime },
      async (runtimeResponse) => {
      if (runtimeResponse && runtimeResponse.success) {
        await setStorage({
          activeSessionId: sessionId,
          sessionStartTime: parsedSessionStartTime,
          blocksPrevented: 0
        });
        setSessionButtons(true);
        startPopupTimer(parsedSessionStartTime);
        loadStats();
      } else {
        alert(runtimeResponse?.error || 'Failed to start extension blocking');
      }
      }
    );
  } catch (error) {
    console.error('Failed to start session:', error);
    alert('Could not start session. Please try again.');
  }
}

async function endSession() {
  try {
    const { token, activeSessionId } = await getStorage(['token', 'activeSessionId']);
    if (!token) {
      alert('Please log in first.');
      return;
    }

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
      const activeResponse = await fetch(`${API_URL}/sessions/active`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (activeResponse.ok) {
        const activeData = await activeResponse.json();
        sessionId = activeData?.session?.id;
      }
    }

    if (sessionId) {
      await fetch(`${API_URL}/sessions/end`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          focus_score: 8,
          distraction_count: 0
        })
      });
    }

    loadStats();
  } catch (error) {
    console.error('Failed to end session:', error);
    alert('Could not end session. Please try again.');
  }
}
