// content.js
console.log('FocusPilot content script loaded on:', window.location.href);

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
