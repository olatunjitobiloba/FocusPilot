// src/blocked/blocked.js

// Update session time - only if a session is actually active
setInterval(() => {
  chrome.storage.local.get(['sessionStartTime', 'activeSessionId'], (result) => {
    if (result.sessionStartTime && result.activeSessionId) {
      const now = Date.now();
      const elapsed = Math.floor((now - result.sessionStartTime) / 1000);
      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;
      console.log(`Session timer: ${minutes}:${String(seconds).padStart(2, '0')} (elapsed: ${elapsed}s from ${result.sessionStartTime})`);
      document.getElementById('session-time').textContent = 
        `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    } else {
      console.log('No active session found');
      document.getElementById('session-time').textContent = '00:00';
    }
  });
}, 1000);

// Update blocks prevented on page load
chrome.storage.local.get(['blocksPrevented'], (result) => {
  const count = result.blocksPrevented || 0;
  console.log('Blocks prevented:', count);
  document.getElementById('blocks-prevented').textContent = count;
});

// Increment blocks prevented each time this page loads
chrome.storage.local.get(['blocksPrevented'], (result) => {
  const count = (result.blocksPrevented || 0) + 1;
  chrome.storage.local.set({ blocksPrevented: count });
  console.log('Incremented blocks prevented to:', count);
});
