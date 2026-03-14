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

function handleWindowMessage(event) {
  if (event.source !== window) return;

  if (!isExtensionContextValid()) return;

  const message = event.data;
  if (!message || message.source !== 'focuspilot-web') return;

  // Handle token sync
  if (message.action === 'syncToken' && message.token) {
    console.log('FocusPilot: Syncing token to extension storage');
    const dataToStore = { token: message.token };
    if (message.refreshToken) {
      dataToStore.refresh_token = message.refreshToken;
    }
    if (message.user) {
      dataToStore.user = message.user;
    }

    safeSetStorage(dataToStore, () => {
      console.log('FocusPilot: Token saved to extension storage');
    });
    return;
  }

  if (
    message.action !== 'startSession' &&
    message.action !== 'endSession' &&
    message.action !== 'refreshBlocklist'
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
}
