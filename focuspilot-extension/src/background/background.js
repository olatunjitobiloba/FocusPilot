// extension/src/background/background.js
const API_URL = 'https://OlatunjiTobi-focuspilot-agent.hf.space';
const DASHBOARD_URL_PATTERNS = [
  'http://localhost:3000/*',
  'https://focuspilot.vercel.app/*'
];

let activeSession = null;
let blockedDomains = [];

function notifyDashboardSessionEvent(action, sessionId = null) {
  chrome.tabs.query({ url: DASHBOARD_URL_PATTERNS }, (tabs) => {
    if (chrome.runtime.lastError || !tabs?.length) return;

    tabs.forEach((tab) => {
      if (!tab.id) return;
      chrome.tabs.sendMessage(
        tab.id,
        {
          action: 'focuspilotSessionSync',
          sessionAction: action,
          sessionId
        },
        () => {
          // Ignore expected failures when target page is not ready.
          void chrome.runtime.lastError;
        }
      );
    });
  });
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Background received message:', message);
  
  if (message.action === 'startSession') {
    console.log('Starting session with ID:', message.sessionId);
    startSession(message.sessionId, message.token, message.sessionStartTime).then(() => {
      console.log('✓ Session started successfully');
      // Set an alarm to auto-end the session when planned duration elapses
      const durationMins = message.sessionDurationMins || 25;
      chrome.alarms.create('autoEndSession', { delayInMinutes: durationMins });
      sendResponse({ success: true });
    }).catch((error) => {
      console.error('✗ Error starting session:', error);
      sendResponse({ success: false, error: error.message });
    });
    return true; // Keep channel open for async response
  } 
  
  else if (message.action === 'endSession') {
    endSession().then(() => {
      sendResponse({ success: true });
    }).catch((error) => {
      sendResponse({ success: false, error: error.message });
    });
    return true;
  }
  
  else if (message.action === 'getBlocklist') {
    getBlocklist().then((blocklist) => {
      sendResponse({ success: true, blocklist });
    }).catch((error) => {
      sendResponse({ success: false, error: error.message });
    });
    return true;
  }

  else if (message.action === 'refreshBlocklist') {
    if (!activeSession) {
      sendResponse({ success: true, skipped: true, reason: 'No active session' });
      return false;
    }

    refreshBlocklistRules(message.token).then((count) => {
      sendResponse({ success: true, blockedCount: count });
    }).catch((error) => {
      sendResponse({ success: false, error: error.message });
    });
    return true;
  }
});

// START SESSION
async function startSession(sessionId, tokenFromMessage, sessionStartTimeFromMessage) {
  console.log('Starting session:', sessionId);
  console.log('Token from message:', tokenFromMessage ? `${tokenFromMessage.substring(0, 20)}...` : 'null');
  
  // Use token from message (if from web page) or get from storage (if from popup)
  let token = tokenFromMessage || (await getToken());
  console.log('Final token to use:', token ? `${token.substring(0, 20)}...` : 'null');
  
  if (!token) {
    throw new Error('Not authenticated. Please log in.');
  }

  let resolvedSessionStartTime = Date.now();
  if (typeof sessionStartTimeFromMessage === 'number' && Number.isFinite(sessionStartTimeFromMessage)) {
    resolvedSessionStartTime = sessionStartTimeFromMessage;
  } else if (typeof sessionStartTimeFromMessage === 'string' && sessionStartTimeFromMessage.trim()) {
    const hasTimezone = /Z$|[+-]\d{2}:\d{2}$/.test(sessionStartTimeFromMessage);
    const normalized = hasTimezone ? sessionStartTimeFromMessage : `${sessionStartTimeFromMessage}Z`;
    const parsedStartTime = new Date(normalized).getTime();
    if (!Number.isNaN(parsedStartTime)) {
      resolvedSessionStartTime = parsedStartTime;
    }
  }
  
  try {
    activeSession = sessionId;

    // Reset session timers when starting a new session
    const now = resolvedSessionStartTime;
    await new Promise((resolve) => {
      chrome.storage.local.set(
        { 
          sessionStartTime: now,
          activeSessionId: sessionId,
          blocksPrevented: 0  // Reset blocks counter
        },
        resolve
      );
    });
    console.log('✓ Session timers reset. Start time:', now, 'Session ID:', sessionId);
    console.log('✓ Storing activeSessionId:', sessionId);
    notifyDashboardSessionEvent('startSession', sessionId);
    
    await refreshBlocklistRules(token);
    
    // Start activity monitoring
    startActivityMonitoring();
    
    // Show notification
    chrome.notifications.create({
      type: 'basic',
      iconUrl: chrome.runtime.getURL('assets/icon128.png'),
      title: 'FocusPilot Session Started',
      message: `Blocking ${blockedDomains.length} distracting sites`
    });
    
    console.log('Session started successfully');
  } catch (error) {
    activeSession = null;
    console.error('Error starting session:', error);
    throw error;
  }
}

async function refreshBlocklistRules(tokenFromMessage) {
  const token = tokenFromMessage || (await getToken());

  if (!token) {
    throw new Error('Not authenticated. Please log in.');
  }

  const response = await fetch(`${API_URL}/blocklist/`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });

  console.log('Blocklist response status:', response.status);
  if (!response.ok) {
    const errorText = await response.text();
    console.error('Blocklist API error response:', errorText);
    if (response.status === 401) {
      await new Promise((resolve) => {
        chrome.storage.local.remove(['token', 'user', 'activeSessionId', 'sessionStartTime', 'blocksPrevented'], resolve);
      });
      activeSession = null;
      blockedDomains = [];
      await removeBlockingRules();
      throw new Error('Authentication expired. Please log in again.');
    }
    throw new Error(`API error: ${response.status} - ${errorText}`);
  }

  const data = await response.json();
  blockedDomains = (data.blocklist || []).map((item) => item.domain);
  console.log('Blocklist fetched:', blockedDomains);

  await applyBlockingRules();
  return blockedDomains.length;
}

// END SESSION
async function endSession() {
  console.log('Ending session');

  // Clear auto-end alarm if it exists
  chrome.alarms.clear('autoEndSession');

  activeSession = null;
  blockedDomains = [];
  notifyDashboardSessionEvent('endSession');
  
  // Clear session timers from storage
  await new Promise((resolve) => {
    chrome.storage.local.remove(['sessionStartTime', 'activeSessionId', 'blocksPrevented'], resolve);
  });
  console.log('✓ Session timers cleared from storage');
  
  // Remove blocking rules
  await removeBlockingRules();
  
  // Stop activity monitoring
  stopActivityMonitoring();
  
  // Show notification
  chrome.notifications.create({
    type: 'basic',
    iconUrl: chrome.runtime.getURL('assets/icon128.png'),
    title: 'FocusPilot Session Ended',
    message: 'Great work! Session complete.'
  });
  
  console.log('Session ended successfully');
}

// ALARM: Auto-end session when planned duration elapses
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'autoEndSession') {
    if (!activeSession) return; // Already ended
    await autoEndSession();
  }
});

async function autoEndSession() {
  const sessionId = activeSession;
  if (!sessionId) return;

  const token = await getToken();
  if (token) {
    try {
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
    } catch (e) {
      console.error('Failed to call end session API during auto-end:', e);
    }
  }

  await endSession();

  // Notify popup if it is open
  chrome.runtime.sendMessage({ action: 'sessionAutoEnded' }).catch(() => {});

  chrome.notifications.create({
    type: 'basic',
    iconUrl: chrome.runtime.getURL('assets/icon128.png'),
    title: 'FocusPilot Session Complete',
    message: 'Your focus session has ended. Great work!'
  });
}

// APPLY BLOCKING RULES
async function applyBlockingRules() {
  if (blockedDomains.length === 0) {
    console.log('No domains to block');
    return;
  }

  const normalizeDomain = (domain) =>
    domain
      .replace(/^https?:\/\//, '')
      .replace(/^www\./, '')
      .split('/')[0]
      .trim();

  const normalizedDomains = blockedDomains
    .map(normalizeDomain)
    .filter(Boolean)
    .map((domain) => domain.toLowerCase());

  const uniqueDomains = [...new Set(normalizedDomains)];

  console.log('Normalized domains to block:', uniqueDomains);
  const rules = uniqueDomains.map((domain, index) => ({
    id: index + 1,
    priority: 1,
    action: {
      type: 'redirect',
      redirect: {
        url: chrome.runtime.getURL('src/blocked/blocked.html')
      }
    },
    condition: {
      urlFilter: `||${domain}^`,
      resourceTypes: ['main_frame']
    }
  }));
  
  console.log('Applying blocking rules:', rules);
  
  // Remove old rules first
  const existingRules = await chrome.declarativeNetRequest.getDynamicRules();
  const existingIds = existingRules.map(r => r.id);
  console.log('Removing existing rules:', existingIds);
  
  // Apply new rules
  try {
    await chrome.declarativeNetRequest.updateDynamicRules({
      removeRuleIds: existingIds,
      addRules: rules
    });
    console.log(`✓ Successfully applied ${rules.length} blocking rules`);
    
    // Verify rules were applied
    const verifyRules = await chrome.declarativeNetRequest.getDynamicRules();
    console.log('Active blocking rules:', verifyRules);
  } catch (error) {
    console.error('Failed to apply blocking rules:', error);
    throw error;
  }
}

// REMOVE BLOCKING RULES
async function removeBlockingRules() {
  const rules = await chrome.declarativeNetRequest.getDynamicRules();
  const ruleIds = rules.map(r => r.id);
  
  if (ruleIds.length > 0) {
    await chrome.declarativeNetRequest.updateDynamicRules({
      removeRuleIds: ruleIds
    });
    console.log('Blocking rules removed');
  }
}

// ACTIVITY MONITORING
let activityInterval;
let currentUrl = '';
let urlStartTime = Date.now();

function startActivityMonitoring() {
  console.log('Starting activity monitoring');
  
  // Track active tab
  chrome.tabs.onActivated.addListener(handleTabChange);
  chrome.tabs.onUpdated.addListener(handleTabUpdate);
  
  // Log activity every 30 seconds
  activityInterval = setInterval(logCurrentActivity, 30000);
}

function stopActivityMonitoring() {
  console.log('Stopping activity monitoring');
  
  chrome.tabs.onActivated.removeListener(handleTabChange);
  chrome.tabs.onUpdated.removeListener(handleTabUpdate);
  
  if (activityInterval) {
    clearInterval(activityInterval);
    activityInterval = null;
  }
}

function handleTabChange(activeInfo) {
  logCurrentActivity(); // Log previous activity
  
  chrome.tabs.get(activeInfo.tabId, (tab) => {
    if (chrome.runtime.lastError) {
      return;
    }

    if (!tab?.url) {
      return;
    }

    currentUrl = tab.url;
    urlStartTime = Date.now();
    console.log('Tab changed to:', currentUrl);
  });
}

function handleTabUpdate(tabId, changeInfo, tab) {
  if (changeInfo.url) {
    logCurrentActivity(); // Log previous activity
    currentUrl = changeInfo.url;
    urlStartTime = Date.now();
    console.log('Tab updated to:', currentUrl);
  }
}

async function logCurrentActivity() {
  if (!activeSession || !currentUrl) return;
  
  const duration = Math.floor((Date.now() - urlStartTime) / 1000);
  
  if (duration < 5) return; // Ignore very short visits (<5 seconds)
  
  try {
    const url = new URL(currentUrl);
    const domain = url.hostname;
    const token = await getToken();
    
    if (!token) return;
    
    console.log('Logging activity:', domain, duration, 'seconds');
    
    const response = await fetch(`${API_URL}/sessions/${activeSession}/activity`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        url: currentUrl,
        domain: domain,
        duration_seconds: duration
      })
    });
    
    if (!response.ok) {
      console.error('Failed to log activity:', response.status);
    } else {
      console.log('Activity logged successfully');
    }
    
  } catch (error) {
    console.error('Error logging activity:', error);
  }
  
  urlStartTime = Date.now();
}

// GET BLOCKLIST
async function getBlocklist() {
  const token = await getToken();
  
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetch(`${API_URL}/blocklist/`, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  
  const data = await response.json();
  return data.blocklist;
}

// HELPER: Get token from storage
function getToken() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['token'], (result) => {
      resolve(result.token || null);
    });
  });
}

// HELPER: Save token to storage
function saveToken(token) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ token }, () => {
      resolve();
    });
  });
}

// Initialize on install/update
chrome.runtime.onInstalled.addListener(async (details) => {
  console.log('FocusPilot extension installed/updated:', details?.reason || 'unknown');

  try {
    chrome.contextMenus.create({
      id: 'addToBlocklist',
      title: 'Add to FocusPilot Blocklist',
      contexts: ['page']
    });
  } catch (error) {
    console.log('Context menu already exists or could not be created:', error?.message || error);
  }
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'addToBlocklist') {
    if (!tab?.url) {
      console.warn('Context menu click has no tab URL. Skipping blocklist add.');
      return;
    }

    let domain = '';
    try {
      const url = new URL(tab.url);
      domain = url.hostname;
    } catch (error) {
      console.warn('Invalid tab URL for blocklist add:', tab.url);
      return;
    }
    
    const token = await getToken();
    
    if (!token) {
      chrome.notifications.create({
        type: 'basic',
        iconUrl: chrome.runtime.getURL('assets/icon128.png'),
        title: 'Not Logged In',
        message: 'Please log in to add sites to blocklist'
      });
      return;
    }
    
    try {
      const response = await fetch(`${API_URL}/blocklist/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ domain })
      });
      
      if (response.ok) {
        chrome.notifications.create({
          type: 'basic',
          iconUrl: chrome.runtime.getURL('assets/icon128.png'),
          title: 'Added to Blocklist',
          message: `${domain} will be blocked during focus sessions`
        });
        
        // If a session is active, refresh blocking rules to include new domain
        if (activeSession) {
          console.log('Active session detected. Refreshing blocking rules...');
          try {
            await refreshBlocklistRules(token);
            console.log('✓ Blocking rules refreshed with new domain');
          } catch (refreshError) {
            console.error('Failed to refresh blocking rules:', refreshError);
          }
        }
      }
    } catch (error) {
      console.error('Error adding to blocklist:', error);
    }
  }
});

console.log('FocusPilot background script loaded');
