# [UX Gap] No fallback UI when primary provider (Codex OAuth) hits monthly limit — user left without tool

## Summary
When Codex OAuth provider exhausts its monthly quota, OpenClaw UI becomes unresponsive with no configurable fallback mechanism. Users without a pre-configured backup provider are left stranded without their AI assistant.

**This is not just a bug — it's a UX gap:** OpenClaw doesn't handle the "user without backup plan loses their tool" scenario.

---

## Steps to Reproduce

1. **Setup:** Configure OpenClaw with Codex OAuth as primary provider
   ```bash
   openclaw auth login codex
   openclaw model set codex-model
   ```

2. **Use until limit:** Interact with OpenClaw until Codex monthly OAuth quota is exhausted

3. **Trigger failure:** Send a new message after quota exhaustion

4. **Observe behavior:**
   - UI becomes unresponsive or shows generic error
   - No prompt to configure alternative provider
   - No link to terminal commands for manual fallback
   - User must manually research and configure backup provider

**Actual Result:** UI dead-end, no guidance, user stranded

**Expected Result:** Emergency UI state with fallback-setup wizard or clear path to terminal commands

---

## Impact

- **Severity:** High (complete loss of functionality)
- **User Impact:** Users lose access to their AI assistant until next billing cycle or manual intervention
- **Support Burden:** Multiple duplicate issues from users hitting the same wall
- **Risk:** Users may abandon OpenClaw after first quota exhaustion

---

## Proposed Solution

### Emergency UI State When Primary Provider Is Exhausted

When API returns `429 Too Many Requests` or quota-exhausted error:

1. **Show prominent alert banner:**
   ```
   ⚠️ Your Codex monthly quota is exhausted.
   OpenClaw can continue with a backup provider.
   ```

2. **Present fallback options:**
   - **🔧 Setup Fallback Provider (Recommended)**
     - Launch wizard with pre-configured free providers (Qwen, Open-Meteo, etc.)
     - One-click OAuth flow for selected provider
     - Auto-configure as secondary provider
   
   - **💻 Show Terminal Commands**
     - Display exact commands to switch models manually:
       ```bash
       openclaw model set qwen-portal/coder-model
       openclaw auth login qwen-portal
       ```
   
   - **📚 Learn More**
     - Link to documentation on provider quotas and fallback strategies

3. **Persist configuration:**
   - Once fallback is configured, automatically switch when primary fails
   - Show notification: "Switched to Qwen (Codex quota exhausted)"

---

## Acceptance Criteria

- [ ] UI detects provider quota exhaustion (429 / specific error codes)
- [ ] Emergency state shows within 2 seconds of failed request
- [ ] Fallback wizard includes at least 2 pre-configured free providers
- [ ] Terminal commands are copy-paste ready
- [ ] After fallback setup, subsequent requests use backup provider automatically
- [ ] User can configure primary/secondary provider priority in settings
- [ ] Documentation updated with "What to do when quota exhausted" guide

---

## Real-World Example

**Date:** 2026-02-20  
**User:** Vassiliy Lakhonin  
**Scenario:** 
- Codex OAuth monthly limit exhausted
- No fallback configured
- Spent 30+ minutes researching alternative providers
- Manually configured Qwen OAuth via terminal
- No in-app guidance was available

**Workaround used:**
```bash
# Manual fallback setup (no UI assistance)
openclaw model set qwen-portal/coder-model
openclaw auth login qwen-portal
```

---

## Additional Context

- **OpenClaw Version:** 2026.2.19-2
- **OS:** macOS (Darwin 25.3.0, arm64)
- **Channel:** Webchat (also affects Telegram, WhatsApp, Discord)
- **Related:** This issue closes multiple duplicate complaints about "OpenClaw stopped working"

---

## Priority

**High** — This blocks core functionality and creates negative first-time experience for users who hit quotas unexpectedly.

---

## Labels Suggested

- `bug`
- `ux-gap`
- `high-priority`
- `oauth`
- `fallback`
- `error-handling`
