# MOBILE-8155: GMA SDK Implementation Audit & Fix

**Jira:** https://wegomushi.atlassian.net/browse/MOBILE-8155

## Problem

Google Ad Manager reports show ~99.9% of Wego's Android app ad requests lack the `google_sdk_version` signal, making them ineligible for AdX bidding. Google support identified two root causes:

1. **Missing SDK initialization** — `MobileAds.initialize()` is never called anywhere in the app. The SDK auto-initializes on first `loadAd()` but this doesn't reliably attach the `google_sdk_version` signal.
2. **Multi-calling** — FLUID→BANNER fallback fires immediately in `onAdFailedToLoad()` with no delay, causing rapid-fire requests that Google flags as multi-calling.

## What Needs to Change

### 1. Add `MobileAds.initialize()` (The Missing Handshake)
- Call `MobileAds.initialize()` once at app startup in `AdsManager` constructor
- Must run on a **background thread** (Google's recommendation)
- No custom queue needed — SDK internally queues ad requests made before init completes
- `AdsManager` constructor is called once (guarded by `instance == null` in `init()`)
- `WegoMainApplication.onCreate()` already calls `AdsManager.init(this)` at line 67

### 2. Add 500ms Delay Before FLUID→BANNER Fallback
- **Do NOT serialize** parallel ad loads — Google supports and expects parallel loading
- Only add a `Handler.postDelayed(500)` before the FLUID→BANNER retry within each slot's `onAdFailedToLoad()`
- Applies to 3 flows:
  - `flightsLoadDFPNativeAd` — 3 slots (lines 175-180)
  - `hotelsLoadDFPNativeAd` — 3 slots (lines 343-348)
  - `perLegFlightsLoadDFPNativeAd` — N slots (lines 110-111)
- Home ads use BANNER only (no fallback) — add TODO comment only

### 3. SDK Version Upgrade (24.6.0 → 24.9.0)
- Safe patch upgrade (bug fixes only)
- Skip 25.x — breaking changes: removed deprecated callbacks, UMP SDK bumped to 4.0.0, requires compileSdk 35
- 25.x upgrade should be a separate ticket

## Out of Scope (Separate Ticket)

### Consent Gating (`canRequestAds()`)
- Google recommends checking `canRequestAds()` before loading ads
- **Not safe to add in this ticket** because:
  - UMP is behind Remote Config flag `a_enable_ump_google_consent`
  - `canRequestAds()` returns false until `requestConsentInfoUpdate()` is called
  - If flag is OFF → all ads break → revenue drops to zero
- Needs coordination with adops team, separate ticket

## Audit Results (Verified)

| Checklist Item | Status | Notes |
|---|---|---|
| SDK init at startup | **MISSING** | Never called — fix in this ticket |
| Latest SDK version | **OUTDATED** | 24.6.0 → 24.9.0 |
| No mediation adapters | **PASS** | Clean GMA-only setup |
| All ads via GMA ad views | **PASS** | `AdManagerAdView` throughout |
| No WebView/custom rendering | **PASS** | Only `GenzoDemographicUtil` accesses internal WebView for analytics |
| One request per placement | **PASS** | Each slot fires one request; parallel across slots is fine |
| FLUID→BANNER delay | **MISSING** | Fires instantly — fix in this ticket |
| No retry loops | **PASS** | Single FLUID→BANNER retry, then stops |
| UMP implemented | **PASS** | In `HomeBaseActivity`, behind Remote Config flag |
| Ads gated on consent | **SKIPPED** | Separate ticket — not safe here |

## Expected Outcome
- `google_sdk_version` signal present on all ad requests
- Ad requests eligible for AdX bidding
- No rapid-fire multi-calling flagged by Google

## Applicable Rules
- `coding-conventions.md` — Detekt compliance, max line length 120, max class 600 lines
- AdsManager.java is 547 lines — changes must stay under 600

---
*Created: 2026-03-27*