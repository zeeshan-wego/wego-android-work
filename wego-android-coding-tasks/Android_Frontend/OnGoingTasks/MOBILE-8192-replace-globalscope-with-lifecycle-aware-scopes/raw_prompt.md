# [Android] Replace GlobalScope.launch with lifecycle-aware scopes

**Jira Ticket:** https://wegomushi.atlassian.net/browse/MOBILE-8192
**Type:** Task
**Status:** In Progress
**Assignee:** Zeeshan Arif (zeeshan@wego.com)

## Problem

`GlobalScope.launch` outlives the host Activity / ViewModel, leading to crashes when callbacks fire after destruction and leaking work that should have been cancelled.

## Locations

- `wegoauth/src/main/java/com/wego/android/login/newlogin/Authenticator.kt:250` — `refreshToken`
- `wegoauth/src/main/java/com/wego/android/login/base/BaseAuthActivity.kt:85` — `trackLoginSignup`
- `hotels/src/main/java/com/wego/android/features/hotelpromo/HotelPromoApp.kt:238` — `wegoPromo` composable

## Fix

- `Authenticator.refreshToken` → convert to `suspend fun` (no production callers today; future callers own the scope).
- `BaseAuthActivity.trackLoginSignup` → `lifecycleScope.launch(Dispatchers.Main)`.
- `wegoPromo` composable → `rememberCoroutineScope().launch { … }`.
- Remove now-unused `GlobalScope` / `Dispatchers` imports.

## Acceptance Criteria

- No `GlobalScope` references remain in the listed files.
- Unit tests added for `Authenticator.refreshToken` covering the new suspend signature.
- Manual verification: rotate device during promo copy + smoke-test the auth screen, confirm no leaked work.

---
*Fetched from Jira on 2026-04-28. Scope clarified same day to add `BaseAuthActivity.kt:85` (see Jira comment).*
