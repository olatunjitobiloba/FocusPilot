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

async function loadSessionState() {
  try {
    const { token } = await getStorage(['token']);
    if (!token) {
      setSessionButtons(false);
      return;
    }

    const response = await fetch(`${API_URL}/sessions/active`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      setSessionButtons(false);
      return;
    }

    const data = await response.json();
    if (data?.active && data?.session?.id) {
      await setStorage({
        activeSessionId: data.session.id,
        sessionStartTime: new Date(data.session.start_time).getTime()
      });
      setSessionButtons(true);
    } else {
      await removeStorage(['activeSessionId', 'sessionStartTime']);
      setSessionButtons(false);
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
      document.getElementById('focusTime').textContent =
        `${Math.floor(focusMinutes / 60)}h ${focusMinutes % 60}m`;
    }

    if (weeklyResponse.ok) {
      const weekly = await weeklyResponse.json();
      document.getElementById('streak').textContent = `${weekly.current_streak || 0} days`;
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
    const sessionId = data?.session?.id;

    if (!sessionId) {
      throw new Error('Session ID missing from server response');
    }

    chrome.runtime.sendMessage({ action: 'startSession', sessionId, token }, async (runtimeResponse) => {
      if (runtimeResponse && runtimeResponse.success) {
        await setStorage({
          activeSessionId: sessionId,
          sessionStartTime: Date.now(),
          blocksPrevented: 0
        });
        setSessionButtons(true);
        loadStats();
      } else {
        alert(runtimeResponse?.error || 'Failed to start extension blocking');
      }
    });
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

    chrome.runtime.sendMessage({ action: 'endSession' }, async () => {
      await removeStorage(['activeSessionId', 'sessionStartTime']);
      setSessionButtons(false);
      loadStats();
    });
  } catch (error) {
    console.error('Failed to end session:', error);
    alert('Could not end session. Please try again.');
  }
}
