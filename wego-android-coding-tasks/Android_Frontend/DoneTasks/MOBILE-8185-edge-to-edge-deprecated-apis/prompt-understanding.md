# MOBILE-8185: Migrate away from deprecated edge-to-edge APIs (Android 15+)

**Jira Ticket:** https://wegomushi.atlassian.net/browse/MOBILE-8185

## What we're building (product level)

Stop calling `android.view.Window.setStatusBarColor` / `setNavigationBarColor` on Android 15+ (API 35+) devices, where these APIs are no-ops, while preserving the exact same bar-tinting behavior on Android 14 and older (API ≤ 34) devices. This clears the "deprecated APIs for edge-to-edge" advisory in Play Console in the release **after v7.48** (target: v7.49 or later).

## Why now

Play Console advisory on v7.47.0 → dead bytecode in every cold-launch path. Not a crash, not visual damage on 15+ (our layouts already use `fitsSystemWindows` / `WindowInsetsCompat`), but we should clean up before Google tightens the enforcement or the warning escalates.

## Decisions already made (from investigation)

| Decision        | Choice                                                          | Rationale                                                                                                                                                                                            |
| --------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Scope           | **Scope B** — all 34 Wego classes                               | Play Console sampled 10; fixing only those leaves 27 ticking timers. Cheap marginal cost since most funnel through 3 shared helpers.                                                                 |
| Library bumps   | **Separate ticket**                                             | 3 of the 10 Play Console entries are in `Material` / `AndroidX` / `Places` libraries — needs dependency version bumps with its own blast-radius review.                                              |
| Tests           | **Yes — fresh unit tests for every modified helper**            | No tests exist today for `WegoUIUtils.kt` or `WegoAuthUtils.kt`. Cover both SDK <35 (call made) and SDK ≥35 (call skipped) for every modified path.                                                  |
| Pattern         | **Guard with `Build.VERSION_CODES.VANILLA_ICE_CREAM` (API 35)** | Already used once at `SprinklrChatActivity.kt:83`. No new project constant needed.                                                                                                                   |
| New abstraction | **2 compat extensions in `WegoUIUtils.kt`**                     | Consistent with file's existing extension style. Collapses ~18 direct call sites into one-liner compat calls. Not a new "pattern" — just another extension alongside `setStatusBarColorIcons` et al. |

## Scope — quantified

| Category | Count | Files |
|---|---|---|
| **Modified — shared helpers** | 5 sites, 2 files | `WegoUIUtils.kt` (3 helpers), `WegoAuthUtils.kt` (2 helpers) |
| **New helpers added** | 2 | `WegoUIUtils.kt` — `setStatusBarColorCompat`, `setNavigationBarColorCompat` |
| **Modified — direct call sites** | ~18 sites, ~18 files | hotels, hotelsv2, flights, homebase, libbase modules |
| **New test files** | 2 | `WegoUIUtilsTest.kt`, `WegoAuthUtilsTest.kt` |

**Total:** ~21 production files touched, 2 test files created, ~60 production lines + ~120 test lines.

## Not in scope (explicit)

- Library dependency bumps — tracked separately for `com.google.android.material` and `androidx.activity`
- Full `ActivityCompat.enableEdgeToEdge()` + proper `WindowInsetsCompat` migration — architectural change beyond this warning
- Refactoring unrelated code in the touched files

## Acceptance Criteria

- [ ] Build passes: `./gradlew :wegoapk:assemblePlaystoreDebug`
- [ ] Unit tests pass for `WegoUIUtilsTest` and `WegoAuthUtilsTest`
- [ ] `./gradlew detekt` clean (strict mode, `maxIssues=0`)
- [ ] Android 15+ device: no visual regression (Home, Flights, Hotels, Login, Offers, Stories, MiniApp)
- [ ] Android 14 device: bar colors still tint correctly (no regression from a wrongly-guarded site)
- [ ] Grep verification: zero direct `window.statusBarColor =` / `setStatusBarColor(` / navigation equivalents remain outside the compat helpers
- [ ] Optional: APK dex re-scan confirms only `androidx.*` / `com.google.*` library entries remain as invokers

## Applicable Rules

Based on the task content, these coding rules from `docs/ai-rules/` apply:

| Rule                          | Why it applies                                                                                                                                                      |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **critical-thinking.md**      | Always-apply. Question patterns before touching 21 files across 6 modules.                                                                                          |
| **android-best-practices.md** | SDK version gating, API deprecation handling, extension function patterns — core Android-specific work.                                                             |
| **detekt-compliance.md**      | Project runs detekt in strict mode (`maxIssues=0`). Max line length 120, max method 60 lines, max class 600 lines. New helpers must conform.                        |
| **coderabbit-compliance.md**  | CodeRabbit auto-reviews every PR — fix must pass with zero critical/major issues. Relevant to helper design, test coverage completeness, and SDK-guard consistency. |
| **code-review.md**            | Applied in Phase 4 before commit.                                                                                                                                   |

**Note:** `mvvm-rules.md` not listed — no ViewModel/architectural changes in this task. `ui-component-validation.md` not listed — no new UI components (bar tint is window-level chrome). `performance-optimization.md` not listed — guard is an if-branch; no perf implications.

## Risks

| Risk                                                                             | Likelihood | Mitigation                                                                                                                      |
| -------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Missed call site → warning resurfaces on next release                            | Low        | Dex re-scan after implementation verifies every Wego invocation is gated                                                        |
| Wrong guard polarity (`>=` instead of `<`) → regression on pre-15                | Low        | Unit tests cover both branches explicitly                                                                                       |
| Java interop breakage in Kotlin compat helpers                                   | Medium     | Java files already call `WegoUIUtilsKt.setStatusBarColorIcons(this, ...)` — same static-accessor pattern for new compat helpers |
| Compose lambda (`BOWRoomSelectionApp.kt`) guards incorrectly inside `SideEffect` | Low        | One-site targeted edit; verified against current file line 62 in plan                                                           |
| Detekt complaints on new helpers                                                 | Low        | Helpers are 3-line; line length + method size well within limits                                                                |

## Out-of-Band Context

- **Branch naming:** per memory `feedback_branch_naming.md` → `bug/` for bugs, `feature/` for tasks, never `fix/` or `chore/`. This task is categorized as a bug (Play Console flagged), so branch = `bug/MOBILE-8185-edge-to-edge-deprecated-apis`
- **Commit convention:** prefixed with module scope, e.g. `fix(libbase): guard setStatusBarColor on Android 15+`
- **PR title:** no conventional-commit prefixes; clean human-readable title
- **DFM build commands** already documented in memory — use `./gradlew :wegoapk:assemblePlaystoreDebug` + `android run --apks=base,home,flexibleairlines`
- **Pre-approved implementation plan:** `~/.claude/plans/delegated-percolating-cray.md` — can be carried over as starting point for `execution_plan.md`
