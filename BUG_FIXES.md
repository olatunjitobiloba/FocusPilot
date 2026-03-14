# BUG_FIXES.md

## Day 7 Bug Fixes

### Known Issues to Check:

1. CORS errors in browser?
   - Fix: Verify CORS middleware in main.py allows your Vercel URL
   - Code: allow_origins=["https://focuspilot.vercel.app", "http://localhost:3000"]

2. Token expiry not handled?
   - Fix: Add 401 interceptor in frontend api/client.ts
   - Code: Redirect to /login on 401 response

3. Active session not clearing after end?
   - Fix: Verify end_session updates end_time in database
   - Test: Check Supabase table directly after ending session

4. Stats returning 0 when data exists?
   - Fix: Check date comparison in stats queries
   - Issue: UTC vs local time mismatch

5. Suggestions empty even after seeding?
   - Fix: Run seed script with correct USER_ID
   - Verify: Check browsing_activity table in Supabase

6. Extension not blocking sites?
   - Fix: Check declarativeNetRequest rules are applied
   - Debug: chrome://extensions → FocusPilot → Service Worker → Console

7. Favicon not loading in blocklist?
   - Fix: This is expected for some domains, onError handler hides it
   - No fix needed
