// content.js
console.log('FocusPilot content script loaded on:', window.location.href);

const LISTENER_FLAG = '__focuspilotMessageListenerAttached';

function isExtensionContextValid() {
  try {
    return Boolean(chrome?.runtime?.id);
  } catch (error) {
    return false;
  }
}

function safeSetStorage(data, onSuccess) {
  if (!isExtensionContextValid()) {
    return;
  }

  try {
    chrome.storage.local.set(data, () => {
      if (chrome.runtime.lastError) {
        if (!chrome.runtime.lastError.message?.includes('Extension context invalidated')) {
          console.warn('FocusPilot: Storage write failed:', chrome.runtime.lastError.message);
        }
        return;
      }
      if (typeof onSuccess === 'function') onSuccess();
    });
  } catch (error) {
    if (!String(error?.message || error).includes('Extension context invalidated')) {
      console.warn('FocusPilot: Storage write exception:', error);
    }
  }
}

function safeSendMessage(payload) {
  if (!isExtensionContextValid()) {
    return;
  }

  try {
    chrome.runtime.sendMessage(payload, (response) => {
      if (chrome.runtime.lastError) {
        if (!chrome.runtime.lastError.message?.includes('Extension context invalidated')) {
          console.warn('FocusPilot: Error sending message:', chrome.runtime.lastError.message);
        }
      } else {
        console.log('FocusPilot: Background response:', response);
      }
    });
  } catch (error) {
    if (!String(error?.message || error).includes('Extension context invalidated')) {
      console.warn('FocusPilot: sendMessage exception:', error);
    }
  }
}

function getStorageLocal(keys) {
  return new Promise((resolve) => {
    if (!isExtensionContextValid()) {
      resolve({});
      return;
    }

    try {
      chrome.storage.local.get(keys, (result) => {
        if (chrome.runtime.lastError) {
          if (!chrome.runtime.lastError.message?.includes('Extension context invalidated')) {
            console.warn('FocusPilot: Storage read failed:', chrome.runtime.lastError.message);
          }
          resolve({});
          return;
        }
        resolve(result || {});
      });
    } catch (error) {
      if (!String(error?.message || error).includes('Extension context invalidated')) {
        console.warn('FocusPilot: Storage read exception:', error);
      }
      resolve({});
    }
  });
}

async function checkIfBlocked() {
  const storage = await getStorageLocal([
    'focusflow_blocked',
    'focusflow_domains',
    'focusflow_unblock_at'
  ]);

  if (!storage.focusflow_blocked) return;

  if (storage.focusflow_unblock_at) {
    const unblockAt = new Date(storage.focusflow_unblock_at);
    if (new Date() >= unblockAt) {
      safeSetStorage({ focusflow_blocked: false });
      return;
    }
  }

  const currentDomain = window.location.hostname.replace(/^www\./, '').toLowerCase();
  const blockedDomains = (storage.focusflow_domains || [])
    .map((domain) => String(domain || '').replace(/^www\./, '').toLowerCase())
    .filter(Boolean);

  if (blockedDomains.some((domain) => currentDomain.includes(domain))) {
    showBlockPage();
  }
}

function showBlockPage() {
  if (!document.body) return;

  document.body.innerHTML = `
    <div style="
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      background: #1a1a2e;
      color: white;
      font-family: -apple-system, sans-serif;
      text-align: center;
      padding: 40px;
    ">
      <h1 style="font-size: 32px; font-weight: 700; margin-bottom: 12px;">
        Focus Mode Active
      </h1>
      <p style="font-size: 18px; color: #a0aec0; max-width: 400px; line-height: 1.6;">
        FocusFlow has blocked this site to help you stay on track.
        Your agent detected high procrastination risk.
      </p>
      <div style="
        margin-top: 32px;
        padding: 16px 24px;
        background: #2d3748;
        border-radius: 12px;
        font-size: 14px;
        color: #68d391;
      ">
        Return to your work and the block will lift automatically.
      </div>
    </div>
  `;
}

function handleWindowMessage(event) {
  if (event.source !== window) return;

  if (!isExtensionContextValid()) return;

  const message = event.data;
  if (!message || message.source !== 'focuspilot-web') return;

  // Handle token sync
  if (message.action === 'syncToken' && message.token) {
    console.log('FocusPilot: Syncing token to extension storage');
    const dataToStore = { token: message.token };
    if (message.apiUrl) {
      dataToStore.api_url = message.apiUrl;
    }
    if (message.refreshToken) {
      dataToStore.refresh_token = message.refreshToken;
    }
    if (message.user) {
      dataToStore.user = message.user;
    }

    safeSetStorage(dataToStore, () => {
      console.log('FocusPilot: Token saved to extension storage');
      safeSendMessage({ action: 'refreshRemoteBlockState' });
    });
    return;
  }

  if (
    message.action !== 'startSession' &&
    message.action !== 'endSession' &&
    message.action !== 'refreshBlocklist' &&
    message.action !== 'notifyBreakStarted' &&
    message.action !== 'notifyBreakEnded'
  ) return;

  console.log('FocusPilot: Forwarding message to background:', message.action, message.sessionId);
  console.log('FocusPilot: Token present?', !!message.token, message.token ? `Length: ${message.token.length}` : '');
  safeSendMessage({
    action: message.action,
    sessionId: message.sessionId,
    token: message.token,
    sessionStartTime: message.sessionStartTime,
    sessionDurationMins: message.sessionDurationMins
  });
}

function handleRuntimeMessage(message, sender, sendResponse) {
  if (message?.action === 'focuspilotRequestTokenSync') {
    try {
      const token = localStorage.getItem('token');
      const refreshToken = localStorage.getItem('refresh_token');
      const userRaw = localStorage.getItem('user');

      if (!token && !refreshToken) {
        sendResponse?.({ success: false, reason: 'No token in page localStorage' });
        return false;
      }

      const dataToStore = {};
      if (token) dataToStore.token = token;
      if (refreshToken) dataToStore.refresh_token = refreshToken;
      if (userRaw) {
        try {
          dataToStore.user = JSON.parse(userRaw);
        } catch {
          // Ignore malformed user JSON and continue syncing tokens.
        }
      }

      safeSetStorage(dataToStore, () => {
        console.log('FocusPilot: Token sync requested by popup and completed');
        sendResponse?.({ success: true });
      });
      return true;
    } catch (error) {
      sendResponse?.({ success: false, error: String(error) });
      return false;
    }
  }

  if (!message || message.action !== 'focuspilotSessionSync') return false;

  const bridgedAction =
    message.sessionAction === 'endSession' ? 'endSession' : 'startSession';

  window.postMessage(
    {
      source: 'focuspilot-extension',
      action: bridgedAction,
      sessionId: message.sessionId || null,
    },
    '*'
  );

  return false;
}

if (!window[LISTENER_FLAG]) {
  window[LISTENER_FLAG] = true;
  window.addEventListener('message', handleWindowMessage);
  chrome.runtime.onMessage.addListener(handleRuntimeMessage);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      checkIfBlocked().catch((error) => {
        console.warn('FocusPilot: Block check failed:', error);
      });
    }, { once: true });
  } else {
    checkIfBlocked().catch((error) => {
      console.warn('FocusPilot: Block check failed:', error);
    });
  }
}
