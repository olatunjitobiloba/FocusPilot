// content.js
console.log('FocusPilot content script loaded on:', window.location.href);

window.addEventListener('message', (event) => {
  if (event.source !== window) return;

  const message = event.data;
  if (!message || message.source !== 'focuspilot-web') return;

  // Handle token sync
  if (message.action === 'syncToken' && message.token) {
    console.log('FocusPilot: Syncing token to extension storage');
    chrome.storage.local.set({ token: message.token }, () => {
      console.log('FocusPilot: Token saved to extension storage');
    });
    return;
  }

  if (message.action !== 'startSession' && message.action !== 'endSession') return;

  console.log('FocusPilot: Forwarding message to background:', message.action, message.sessionId);
  console.log('FocusPilot: Token present?', !!message.token, message.token ? `Length: ${message.token.length}` : '');
  chrome.runtime.sendMessage({
    action: message.action,
    sessionId: message.sessionId,
    token: message.token
  }, (response) => {
    if (chrome.runtime.lastError) {
      console.error('FocusPilot: Error sending message:', chrome.runtime.lastError);
    } else {
      console.log('FocusPilot: Background response:', response);
    }
  });
});

window.addEventListener('message', (event) => {
	if (event.source !== window) return;

	const message = event.data;
	if (!message || message.source !== 'focuspilot-web') return;

	if (message.action !== 'startSession' && message.action !== 'endSession') return;

		chrome.runtime.sendMessage({
			action: message.action,
		sessionId: message.sessionId,
		token: message.token
		});
	});
