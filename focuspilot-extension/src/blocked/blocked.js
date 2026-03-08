// src/blocked/blocked.js
// Update session time
setInterval(() => {
  chrome.storage.local.get(['sessionStartTime'], (result) => {
    if (result.sessionStartTime) {
      const elapsed = Math.floor((Date.now() - result.sessionStartTime) / 1000);
      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;
      document.getElementById('session-time').textContent = 
        `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }
  });
}, 1000);

// Update blocks prevented
chrome.storage.local.get(['blocksPrevented'], (result) => {
  document.getElementById('blocks-prevented').textContent = result.blocksPrevented || 0;
});

// Increment blocks prevented
chrome.storage.local.get(['blocksPrevented'], (result) => {
  const count = (result.blocksPrevented || 0) + 1;
  chrome.storage.local.set({ blocksPrevented: count });
});
