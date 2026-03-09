// content.js
console.log('FocusPilot content script loaded on:', window.location.href);

window.addEventListener('message', (event) => {
  if (event.source !== window) return;

  const message = event.data;
  if (!message || message.source !== 'focuspilot-web') return;

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
