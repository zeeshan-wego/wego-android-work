# MOBILE-8192 — Replace GlobalScope.launch with lifecycle-aware scopes

**Jira:** https://wegomushi.atlassian.net/browse/MOBILE-8192

## What

Three production call sites use `GlobalScope.launch`, which detaches the coroutine from any host lifecycle. When the host (Activity / ViewModel / composition) is destroyed, the launched work keeps running, can leak resources, and can crash if it touches UI state after teardown. The Wego Android best-practices doc explicitly forbids `GlobalScope` (`docs/ai-rules/android-best-practices.md`).

## Why now

- The codebase forbids `GlobalScope` per the Concurrency rules — these three call sites are the remaining production violations (a fourth occurrence in `HotelPromoBottomBar.kt:89` is already commented out).
- Two of the three sites are in active flows (auth refresh, login analytics, hotel-detail promo copy) and any one of them can produce a crash on rotation or destruction.

## Per-location fix

| File | Construct | Fix | Reason |
|---|---|---|---|
| `wegoauth/.../Authenticator.kt:250` `refreshToken` | Plain class, not Dagger-managed; **zero production callers** today | Convert to `suspend fun refreshToken(refreshToken: String): TokenResponse?` | Cleanest. No callers means no migration burden. Future callers own the scope (`viewModelScope` / `lifecycleScope`). |
| `wegoauth/.../BaseAuthActivity.kt:85` `trackLoginSignup` | `AppCompatActivity` subclass | `lifecycleScope.launch(Dispatchers.Main)` | The base type provides `lifecycleScope`. Existing try/catch around the call stays. |
| `hotels/.../HotelPromoApp.kt:238` `wegoPromo` Composable | Drives a 1-second visual flash for "promo copied" state | `rememberCoroutineScope().launch { … }` | Compose-idiomatic; cancels with the composition. |

In all three files, the `kotlinx.coroutines.GlobalScope` import (and any now-unused `Dispatchers` import) gets removed.

## Out of scope (deliberately)

- Refactoring `Authenticator` into Dagger DI — too large for this ticket; the suspend-fun route avoids the question entirely.
- The commented-out `GlobalScope.launch` in `HotelPromoBottomBar.kt:89` — leave alone (separate cleanup if at all).
- Changing call sites of `Authenticator` (`logout`, `authenticate`, `getToken`, etc.) — none of those use `GlobalScope`.

## Acceptance Criteria

- `grep -rn 'GlobalScope' wegoauth/src/main hotels/src/main` returns no matches in the three target files (only comments / dead code may remain elsewhere).
- New unit tests in `wegoauth/src/test/.../newlogin/AuthenticatorTest.kt` cover the new `suspend` signature of `refreshToken` (success path + non-200 / error path), using `runTest` and a `MockWebServer`.
- Existing tests in `AuthenticatorTest.kt` still pass.
- Detekt (CI-blocking, `maxIssues=0`) passes.
- Manual smoke verification by Zeeshan: auth screen and hotel-detail promo copy.

## Risks

- Touching `Authenticator` could break the auth flow even if `refreshToken` itself has no callers — the refactor must not affect the `Authenticator()` constructor or the `logout` / `authenticate` / `getToken` methods.
- `BaseAuthActivity.trackLoginSignup` runs analytics fire-and-forget. Switching to `lifecycleScope` means analytics for a login event will be cancelled if the user immediately closes the screen. This is acceptable (analytics for an aborted login is uninteresting), but worth flagging.
- `rememberCoroutineScope` recomposes correctly across config changes — no behavior change from the user's perspective expected.

## Applicable Rules

- `docs/ai-rules/android-best-practices.md` — **always-apply.** Concurrency section: `viewModelScope` / `viewLifecycleOwner.lifecycleScope`, no `GlobalScope`, structured concurrency, no `Thread.sleep`. Memory-leak section: nullify view bindings, no Activity refs in ViewModels.
- `docs/ai-rules/mvvm-rules.md` — **always-apply.** ViewModels MUST use `viewModelScope`; this task doesn't touch a ViewModel but reinforces why we don't reach for `GlobalScope`.
- `docs/ai-rules/critical-thinking.md` — **always-apply.** Used during this phase to question the ticket's "inject via Dagger" suggestion vs. the simpler `suspend` conversion.
- `docs/ai-rules/detekt-compliance.md` — Detekt is CI-blocking with `maxIssues=0`. Max line 120, max method 60, max class 600. Ensure the changes don't tip any file over.
- `docs/ai-rules/coderabbit-compliance.md` — CodeRabbit reviews PRs; code must pass with zero critical/major issues.
