# Execution Summary — MOBILE-8192

## Current State
- **Phase:** 3 (Code) — implementation done, validating
- **Branch:** `feature/mobile-8192-lifecycle-aware-scopes`
- **Last Action:** `:wegoauth` + `:hotels` test suites green; detekt running

## Q&A Log
- Q: Include `BaseAuthActivity.kt:85`? → A: (c) yes; Jira ticket comment + description updated.
- Q: `Authenticator.refreshToken` strategy? → A: (a) suspend fun.
- Q: `HotelPromoApp` → `rememberCoroutineScope()`? → A: yes.
- Q: Tests? → A: write tests; user runs smoke.
- Q (mid-coding): how to test `refreshToken` without mocking JDK `URL`? → A (self-resolved): `mockkConstructor<URL>` doesn't work on bootstrap classes (handler stays null). Switched to `MockWebServer` (already used in 3 other modules). Added `testImplementation libs.okhttp.mockwebserver` to wegoauth/build.gradle and added a default `tokenEndpoint: String = AuthConfig.tokenEndpoint` parameter to `refreshToken` so tests can point at the mock server. Backward-compatible (no callers today, default param keeps future call sites simple).

## Implementation Done
- `Authenticator.kt`: `refreshToken` → suspend fun with `withContext(Dispatchers.IO)`; new `tokenEndpoint` param with default; removed dead commented-out `fetchToken` block; dropped `GlobalScope`/`launch` imports.
- `BaseAuthActivity.kt`: `GlobalScope.launch` → `lifecycleScope.launch`; import swap.
- `HotelPromoApp.kt`: hoisted `rememberCoroutineScope()`; `scope.launch`; dropped `GlobalScope` import.
- `AuthenticatorTest.kt`: 2 new `runTest`-based tests using MockWebServer (200 → parsed TokenResponse, 401 → null).
- `wegoauth/build.gradle`: added `testImplementation libs.okhttp.mockwebserver`.

## Validation
- ✅ `:wegoauth:testPlaystoreDebugUnitTest --rerun-tasks` (full suite, BUILD SUCCESSFUL)
- ✅ `:hotels:testPlaystoreDebugUnitTest --rerun-tasks` (full suite, BUILD SUCCESSFUL)
- ✅ `./gradlew detekt` (BUILD SUCCESSFUL, CI-blocking gate clean)
- ⚠️ `:wegoauth:lintPlaystoreDebug` BUILD FAILED — but the 2 errors are in files I didn't touch (`AuthWebView.kt:85` `ContextCastToActivity`; `TravellerFormScreen.kt:583` `ViewModelConstructorInComposable`) and are pre-existing on `develop`. The wegoauth `lint.xml` baseline file is also stale (old AGP format) — independent of this task. My changes introduced zero lint issues.
- ✅ `:hotels:lintPlaystoreDebug` ran without flagging my changes.

## Next Steps
1. Confirm detekt/lint clean.
2. Phase 4: ticket.md + pr-description.md.
3. Code review (Phase 4h).
4. Commit (after user approval).

## Out-of-scope working-tree noise
- `hotelsv2/src/main/AndroidManifest.xml` was already modified before this session (Google Maps API key swap). Will be excluded from this commit.
