# [MOBILE-8185] Guard deprecated setStatusBarColor/setNavigationBarColor for Android 15+

**Jira:** https://wegomushi.atlassian.net/browse/MOBILE-8185

## Problem

Play Console flagged v7.47.0 under "Your app uses deprecated APIs or parameters for edge-to-edge". On Android 15+ (API 35), `android.view.Window.setStatusBarColor` and `setNavigationBarColor` are silent no-ops — the OS forces edge-to-edge display and ignores these calls. The app renders correctly regardless (layouts already use `fitsSystemWindows` and `WindowInsetsCompat`), but Play Console wants the dead calls removed. Dex analysis found 34 Wego classes making these calls; Play Console sampled 10 of them this cycle.

## Solution

Added two compat helper extensions in `libbase` — `Activity.setStatusBarColorCompat(Int)` and `Activity.setNavigationBarColorCompat(Int)` — that guard the assignment with `if (Build.VERSION.SDK_INT < Build.VERSION_CODES.VANILLA_ICE_CREAM)` (API 35 check). Migrated 18 direct call sites to use the new helpers. Guarded 5 shared helpers (3 in `libbase`, 2 in `wegoauth`) that serve ~20 downstream callers. Pre-Android-15 behavior (status/nav bar tinting) is unchanged; Android 15+ skips the deprecated call. All 22 files touched compile, pass detekt (strict), and unit tests (15 new, all pass).

## Benefits

- Clears Play Console advisory on the v7.49 release
- No behavioral change to users on any SDK version
- Prevents the warning from resurging on future scans of other call sites
- Establishes pattern for future deprecation migrations

## Acceptance Criteria

- [x] Build passes: `./gradlew :wegoapk:assemblePlaystoreDebug`
- [x] Unit tests: 11 in `WegoUIUtilsTest`, 4 in `WegoAuthUtilsTest` (Robolectric, 100% pass)
- [x] Detekt clean (strict mode, `maxIssues=0`)
- [x] Grep verification: zero unguarded `window.statusBarColor =` / `setStatusBarColor(...)` / nav equivalents in Wego code
- [ ] Android 14 device smoke test: bar colors still tint correctly (pre-15 regression guard)
- [ ] Android 15+ device smoke test: no visual regression on Home, Flights, Hotels, Login, Offers, Stories, MiniApp screens
- [ ] (Optional) APK dex re-scan: zero Wego classes remain as invokers

## Out of Scope

Library-origin calls (`MaterialDatePicker.onStart`, `BottomSheetDialog.onCreate`, AndroidX `EdgeToEdgeApi23/26/29`, Places `AutocompleteImplFragment`) are tracked separately — they require dependency version bumps, not code changes.
