# [Android] GMA SDK Implementation Audit & Fix

**Jira Ticket:** https://wegomushi.atlassian.net/browse/MOBILE-8155
**Type:** Task
**Priority:** Standard

## Description

Google's Ad Manager support has confirmed that the majority of Wego's app ad requests are not being recognized as valid GMA SDK traffic, causing them to be ineligible for AdX bidding. An initial AI-assisted code review has identified likely gaps on Android. This ticket covers a full audit and remediation.

**Reference:** [#adops-x-engineering Slack thread](https://wego.slack.com/archives/C057E40SRFB/p1771396636064519)

**Background:** Ad Manager reports show nearly 99.9% of app ad requests lack the `google_sdk_version` signal and are classified as "blank" SDK traffic. Google's support has identified multi-calling (parallel native + leaderboard requests) and inconsistent SDK initialization as primary contributors.

## Audit Checklist

### SDK Initialization & Version
- Confirm GMA SDK is initialized **once at app startup**, before any ad request is made
- Upgrade to the **latest Google Mobile Ads SDK version** (currently outdated per code review)
- Confirm no other mediation adapters are present (e.g. AppLovin MAX, ironSource)

### Rendering Path
- Verify all ads are rendered via **GMA SDK ad views** — no WebView, custom HTML, or wrapped rendering paths
- Confirm the majority of requests report `Rendering SDK = GMA` in Ad Manager

### Request & Fallback Logic
- Ensure **only one ad request is active per placement** at any time
- Confirm no parallel native + leaderboard calls are fired simultaneously
- Verify fallback (native → leaderboard) fires **only after a confirmed no-fill callback**
- Add a **300–800ms guard delay** before triggering the leaderboard fallback request
- Remove any aggressive retry loops or rapid refresh for the same slot

### Consent & Signals
- Confirm user consent (UMP) is **fully resolved before the first ad request**
- Verify ad requests include required signals: `google_sdk_version`, bundle ID, device info
- Confirm no ad requests are dispatched while consent state is still pending/unknown

### Validation
- Test using **Google test ad unit IDs** to confirm clean SDK recognition in Ad Manager logs
- Review logs to confirm no duplicate or rapid-fire requests per impression opportunity

## Expected Outcome
Ad requests correctly identified as GMA SDK traffic, eligible for AdX bidding, with `google_sdk_version` signal present.

---
*Fetched from Jira on 2026-03-27*
