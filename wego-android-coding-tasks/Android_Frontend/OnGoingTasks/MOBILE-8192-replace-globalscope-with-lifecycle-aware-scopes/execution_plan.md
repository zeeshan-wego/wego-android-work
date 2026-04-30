# MOBILE-8192 — Execution Plan

**Branch:** `feature/mobile-8192-lifecycle-aware-scopes`
**Jira:** https://wegomushi.atlassian.net/browse/MOBILE-8192

## Summary

Replace the three remaining production `GlobalScope.launch` call sites in `wegoauth` and `hotels` with lifecycle-aware alternatives, drop the now-unused `GlobalScope` imports, and add unit tests for the converted `Authenticator.refreshToken` suspend signature.

## Approach and trade-offs

| Site | Approach | Why |
|---|---|---|
| `Authenticator.refreshToken` | Convert to `suspend fun refreshToken(refreshToken: String): TokenResponse?` with body wrapped in `withContext(Dispatchers.IO)`. | No production callers today, so a signature change is free. Suspend lets the future caller pick the scope (`viewModelScope` / `lifecycleScope`). The ticket's "inject via Dagger" suggestion is rejected: `Authenticator` is currently `new`-instantiated, so adopting Dagger here is out of scope. |
| `BaseAuthActivity.trackLoginSignup` | `lifecycleScope.launch(Dispatchers.Main)`. | `BaseAuthActivity : AppCompatActivity` already has `lifecycleScope`. Existing `try/catch(Throwable)` stays around the `launch`. |
| `wegoPromo` composable | `rememberCoroutineScope().launch { … }`. | Compose-idiomatic; cancels with the composition. |

**Behavior preservation:**
- `refreshToken` previously dispatched the callback on `Dispatchers.Main`. Removing the callback means the caller-of-the-future controls dispatching after `await()`-ing the suspend. Acceptable since there are no callers today.
- `trackLoginSignup` still runs analytics on `Dispatchers.Main`. If the activity is destroyed mid-tracking the work cancels — flagged as acceptable in `prompt-understanding.md` (analytics for an aborted login is uninteresting).
- `wegoPromo`'s 1-second visual flash is unaffected user-side; it now also cancels cleanly on composition exit.

## Files to change

### Implementation
1. **`wegoauth/src/main/java/com/wego/android/login/newlogin/Authenticator.kt`**
   - Replace the body of `refreshToken` (lines ~249–259) with a `suspend` version that uses `withContext(Dispatchers.IO)`.
   - Remove `import kotlinx.coroutines.GlobalScope`.
   - Keep `import kotlinx.coroutines.Dispatchers` and `import kotlinx.coroutines.withContext`.
   - Drop `import kotlinx.coroutines.launch` if unused (currently only used here).

   New shape:
   ```kotlin
   suspend fun refreshToken(refreshToken: String): TokenResponse? = withContext(Dispatchers.IO) {
       val url = URL(AuthConfig.tokenEndpoint)
       val params = "client_id=${AuthConfig.clientId}&refresh_token=$refreshToken&grant_type=refresh_token"
       postRequest(url, params)
   }
   ```

2. **`wegoauth/src/main/java/com/wego/android/login/base/BaseAuthActivity.kt`**
   - Replace `GlobalScope.launch(Dispatchers.Main)` (line ~85) with `lifecycleScope.launch(Dispatchers.Main)`.
   - Remove `import kotlinx.coroutines.GlobalScope`.
   - Add `import androidx.lifecycle.lifecycleScope`.

3. **`hotels/src/main/java/com/wego/android/features/hotelpromo/HotelPromoApp.kt`**
   - Inside the `wegoPromo` composable, hoist a scope: `val scope = rememberCoroutineScope()` (place near the existing `var promoCodeApplied by remember { … }` line).
   - Replace `GlobalScope.launch { … }` (line ~238) with `scope.launch { … }`.
   - Remove `import kotlinx.coroutines.GlobalScope`.
   - Add `import androidx.compose.runtime.rememberCoroutineScope`.

### Tests
4. **`wegoauth/src/test/java/com/wego/android/login/newlogin/AuthenticatorTest.kt`**
   - Add a `@Nested` group `RefreshToken` (matches Wego style guide) — actually, this file uses flat `@Test` methods, so add flat tests to match local style:
     - `refreshToken returns parsed TokenResponse on 200` — happy path with valid JSON body
     - `refreshToken returns null when server returns non-200` — 401 path
   - Pattern (matches existing `mockkConstructor` + `mockkStatic` usage in this file):
     - `mockkConstructor<URL>()` → `every { anyConstructed<URL>().openConnection() } returns mockHttpConn`
     - `mockHttpConn` is a `mockk<HttpURLConnection>(relaxed = true)` with stubbed `responseCode`, `inputStream`, `outputStream`
     - Use `kotlinx.coroutines.test.runTest { authenticator.refreshToken("rt") }` to drive the suspend
   - Reuse `mockkStatic(Base64::class)` setup already present in `setUp()`; add additional stubs only as needed.

### Docs
- No API spec / ERD / architecture docs are affected (pure coroutine-scope cleanup).
- Task folder docs (`raw_prompt.md`, `prompt-understanding.md`, this plan) are the source of truth for context.

## Test plan

```bash
# Module tests for the changed modules
./gradlew :wegoauth:testPlaystoreDebugUnitTest --rerun-tasks
./gradlew :hotels:testPlaystoreDebugUnitTest --rerun-tasks

# Verify nothing else regressed
./gradlew :wegoapk:testPlaystoreDebugUnitTest --rerun-tasks

# CI-blocking checks
./gradlew detekt
./gradlew lintDebug

# Smoke (manual, by user)
# 1. Auth: open login screen, complete a login, rotate device — confirm no leaks/crashes
# 2. Hotel promo: copy a promo code on hotel detail, rotate during the 1s flash — confirm no leaks
```

## Acceptance Criteria

- [ ] `grep -rn 'GlobalScope' wegoauth/src/main hotels/src/main` returns no live references in the three target files (only commented-out / dead code may remain in unrelated files).
- [ ] New unit tests for `Authenticator.refreshToken` (happy path + non-200) pass.
- [ ] Existing `AuthenticatorTest` cases (`getIsAuthenticating`, etc.) still pass.
- [ ] `:wegoauth` and `:hotels` `testPlaystoreDebugUnitTest` pass.
- [ ] `./gradlew detekt` passes (CI-blocking, `maxIssues=0`).
- [ ] User-run manual smoke: auth screen + hotel-detail promo copy with rotation, no crashes/leaks.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Breaking the `Authenticator` constructor or `logout`/`authenticate`/`getToken` while editing the file. | Only modify the `refreshToken` block and the imports — verify by re-running existing `AuthenticatorTest`. |
| `lifecycleScope` import collision in `BaseAuthActivity`. | Project already uses `androidx.lifecycle.lifecycleScope` elsewhere (verified via grep before commit). |
| Detekt complaint on long line / unused import after edits. | Run `./gradlew detekt` before committing. |
| `mockkConstructor<URL>()` flake when other tests in the same file create real URLs. | Wrap in `try/finally` with `unmockkConstructor<URL>()` per test, or rely on the existing `unmockkAll()` in `@After`. |

## Execution Tracking
- **Started:** 2026-04-28
- **Developer:** zeeshan@wego.com
- **Branch:** `feature/mobile-8192-lifecycle-aware-scopes`
- **Collaborators:** (none)
