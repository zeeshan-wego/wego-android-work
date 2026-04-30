# [MOBILE-8192] [Android] Replace GlobalScope.launch with lifecycle-aware scopes

**Jira:** https://wegomushi.atlassian.net/browse/MOBILE-8192

## Problem

Three production code sites in the auth and hotel-promo flows used `GlobalScope.launch`. Coroutines launched on `GlobalScope` outlive the host Activity / ViewModel / composition, leak resources, and can crash if the launched work touches UI state after destruction. The Wego Android best-practices guide explicitly forbids `GlobalScope`.

## Solution

Each site is replaced with the appropriate lifecycle-aware alternative:

- **Auth token refresh** — switched the dormant `refreshToken` API to a `suspend` function. Future callers will own the scope (the function had no production callers, so the signature change is safe).
- **Login/sign-up analytics** — uses `lifecycleScope` so analytics for an aborted login cancels with the screen.
- **Hotel-detail "promo copied" flash** — uses `rememberCoroutineScope()` so the 1-second visual flash cancels with the composition.

Stale `GlobalScope` and unused coroutine imports are removed. A small dead block of commented-out code in the same file is dropped to satisfy the "no `GlobalScope` references in the listed files" criterion.

## Benefits

- No dangling coroutines after Activity / composition teardown.
- No Crashlytics-class crashes from callbacks firing on destroyed UI.
- Codebase stays compliant with the Android best-practices rule against `GlobalScope`.

## Acceptance Criteria

- [x] No `GlobalScope` references remain in `Authenticator.kt`, `BaseAuthActivity.kt`, or `HotelPromoApp.kt`.
- [x] Unit tests cover the new `suspend` `refreshToken` (success path + non-200 error path).
- [x] Existing unit tests in the affected modules still pass.
- [x] Static analysis (`detekt`, CI-blocking) passes.
- [ ] Manual smoke verification by Zeeshan (auth screen + hotel-detail promo copy with rotation).
