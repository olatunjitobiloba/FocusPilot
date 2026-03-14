# E2E_TEST_CHECKLIST.md

## Test Environment
- Backend: https://OlatunjiTobi-focuspilot-agent.hf.space
- Frontend: https://focuspilot.vercel.app
- Browser: Chrome (latest)
- Extension: Loaded as unpacked

---

## FLOW 1: New User Onboarding
- [ ] 1. Visit https://focuspilot.vercel.app
- [ ] 2. See landing page with hero section
- [ ] 3. Click "Start Free Trial"
- [ ] 4. Redirected to /signup
- [ ] 5. Fill in name, email, password
- [ ] 6. Click "Sign Up"
- [ ] 7. Redirected to /dashboard
- [ ] 8. Dashboard loads with zero stats (new user)
- [ ] 9. See "No sessions yet" in session history
- [ ] 10. Navbar shows correct username

**RESULT: ✅ PASS / ❌ FAIL**
Notes: _______________

---

## FLOW 2: Focus Session
- [ ] 1. Open Chrome extension popup
- [ ] 2. See "Log In" button (not yet logged in via extension)
- [ ] 3. Click "Log In" → opens https://focuspilot.vercel.app/login in new tab
- [ ] 4. Log in via dashboard
- [ ] 5. Go back to extension popup
- [ ] 6. Refresh popup — should now show main section
- [ ] 7. Click "Start Session"
- [ ] 8. Timer starts counting up
- [ ] 9. Try to visit youtube.com → see blocked page
- [ ] 10. Blocked page shows session timer
- [ ] 11. Return to extension → click "End Session"
- [ ] 12. Enter focus score (e.g., 8)
- [ ] 13. Session ends, timer resets
- [ ] 14. Refresh dashboard → see session in history

**RESULT: ✅ PASS / ❌ FAIL**
Notes: _______________

---

## FLOW 3: Blocklist Management
- [ ] 1. Visit https://focuspilot.vercel.app/blocklist
- [ ] 2. Click "AI Suggestions" tab
- [ ] 3. See suggestion cards (if data exists)
- [ ] 4. Click "Block This Site" on one suggestion
- [ ] 5. Success message appears
- [ ] 6. Switch to "Blocked Sites" tab
- [ ] 7. See newly blocked site in list
- [ ] 8. Click trash icon on a site
- [ ] 9. Confirmation dialog appears
- [ ] 10. Confirm → site removed from list
- [ ] 11. Click "+ Add Site"
- [ ] 12. Modal opens with quick-add buttons
- [ ] 13. Click "youtube" quick-add
- [ ] 14. Modal closes, site added to list

**RESULT: ✅ PASS / ❌ FAIL**
Notes: _______________

---

## FLOW 4: Dashboard Analytics
- [ ] 1. Visit https://focuspilot.vercel.app/dashboard
- [ ] 2. Stats cards show correct values
- [ ] 3. Weekly chart renders (may be empty for new user)
- [ ] 4. Distractions chart renders
- [ ] 5. Session history shows recent sessions
- [ ] 6. Recommendations section shows suggestions
- [ ] 7. All numbers are non-negative
- [ ] 8. No console errors in browser DevTools

**RESULT: ✅ PASS / ❌ FAIL**
Notes: _______________

---

## FLOW 5: Authentication Edge Cases
- [ ] 1. Log out from navbar
- [ ] 2. Try to visit https://focuspilot.vercel.app/dashboard directly
- [ ] 3. Redirected to https://focuspilot.vercel.app/login (protected route works)
- [ ] 4. Log in with wrong password
- [ ] 5. See error message "Invalid credentials"
- [ ] 6. Log in with correct credentials
- [ ] 7. Redirected to /dashboard
- [ ] 8. Refresh page — still logged in (token persists)
- [ ] 9. Open new tab — still logged in

**RESULT: ✅ PASS / ❌ FAIL**
Notes: _______________

---

## FLOW 6: API Health Check
- [ ] 1. Visit https://OlatunjiTobi-focuspilot-agent.hf.space/health
- [ ] 2. See {"status": "healthy"}
- [ ] 3. Visit https://OlatunjiTobi-focuspilot-agent.hf.space/health/detailed
- [ ] 4. All checks show "healthy"
- [ ] 5. Visit https://OlatunjiTobi-focuspilot-agent.hf.space/docs
- [ ] 6. Swagger UI loads with all endpoints
- [ ] 7. Test an endpoint directly from Swagger

**RESULT: ✅ PASS / ❌ FAIL**
Notes: _______________
