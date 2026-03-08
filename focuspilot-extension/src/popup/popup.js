// popup.js
const API_URL = "https://OlatunjiTobi-focusflow-agent.hf.space";

// DOM elements
const authView = document.getElementById('authView');
const dashboardView = document.getElementById('dashboardView');
const loginBtn = document.getElementById('loginBtn');
const signupBtn = document.getElementById('signupBtn');
const startSessionBtn = document.getElementById('startSessionBtn');
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
  chrome.runtime.sendMessage({ action: 'startSession' }, (response) => {
    if (response && response.success) {
      alert('Focus session started!');
    }
  });
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
    const { token } = await chrome.storage.local.get(['token']);
    
    const response = await fetch(`${API_URL}/stats/daily`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (response.ok) {
      const stats = await response.json();
      document.getElementById('focusTime').textContent = 
        `${Math.floor(stats.focus_minutes / 60)}h ${stats.focus_minutes % 60}m`;
      document.getElementById('streak').textContent = 
        `${stats.streak} days`;
    }
  } catch (error) {
    console.error('Failed to load stats:', error);
  }
}
