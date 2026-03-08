// extension/src/background/background.js
const API_URL = 'https://OlatunjiTobi-focusflow-agent.hf.space';

let activeSession = null;
let blockedDomains = [];

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Message received:', message);
  
  if (message.action === 'startSession') {
    startSession(message.sessionId, message.token).then(() => {
      sendResponse({ success: true });
    }).catch((error) => {
      console.error('Error starting session:', error);
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
});

// START SESSION
async function startSession(sessionId, tokenFromMessage) {
  console.log('Starting session:', sessionId);
  activeSession = sessionId;
  
  // Use token from message (if from web page) or get from storage (if from popup)
  let token = tokenFromMessage || (await getToken());
  
  if (!token) {
    throw new Error('Not authenticated. Please log in.');
  }
  
  try {
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
    blockedDomains = data.blocklist.map(item => item.domain);
    
    console.log('Blocklist fetched:', blockedDomains);
    
    // Apply blocking rules
    await applyBlockingRules();
    
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
    console.error('Error starting session:', error);
    throw error;
  }
}

// END SESSION
async function endSession() {
  console.log('Ending session');
  
  activeSession = null;
  blockedDomains = [];
  
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
    .filter(Boolean);

  // Create blocking rules for each domain
  const rules = normalizedDomains.map((domain, index) => ({
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
  
  // Apply new rules
  await chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: existingIds,
    addRules: rules
  });
  
  console.log('Blocking rules applied');
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
    if (tab.url) {
      currentUrl = tab.url;
      urlStartTime = Date.now();
      console.log('Tab changed to:', currentUrl);
    }
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

// Initialize on install
chrome.runtime.onInstalled.addListener(() => {
  console.log('FocusPilot extension installed');
  
  // Create context menu item
  chrome.contextMenus.create({
    id: 'addToBlocklist',
    title: 'Add to FocusPilot Blocklist',
    contexts: ['page']
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'addToBlocklist') {
    const url = new URL(tab.url);
    const domain = url.hostname;
    
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
      }
    } catch (error) {
      console.error('Error adding to blocklist:', error);
    }
  }
});

console.log('FocusPilot background script loaded');
