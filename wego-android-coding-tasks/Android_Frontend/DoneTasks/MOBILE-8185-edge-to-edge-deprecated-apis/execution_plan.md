# Execution Plan — MOBILE-8185: Edge-to-Edge Deprecated API Fix (Scope B)

**Jira Ticket:** https://wegomushi.atlassian.net/browse/MOBILE-8185
**Branch:** `bug/MOBILE-8185-edge-to-edge-deprecated-apis`
**Target release:** after v7.48 (v7.49 or later)

## Execution Tracking

- **Started:** 2026-04-23
- **Developer:** muthuraman@wego.com
- **Branch:** `bug/MOBILE-8185-edge-to-edge-deprecated-apis`
- **Collaborators:** (none yet)

## Summary

Guard every Wego invocation of the deprecated `Window.setStatusBarColor` / `setNavigationBarColor` APIs with an SDK check (`Build.VERSION.SDK_INT < Build.VERSION_CODES.VANILLA_ICE_CREAM`, i.e. `< 35`). Preserves pre-Android-15 behavior exactly; skips the now-deprecated call on Android 15+ where the OS ignores it.

## Context

Play Console flagged v7.47.0 (release 1274701401) under "Your app uses deprecated APIs or parameters for edge-to-edge". On API 35+ the OS forces edge-to-edge and these setters are silent no-ops; on API ≤34 they still paint the bars.

APK dex disassembly on v7.47 shows **40 containing classes** invoke one of these APIs (54 unique call sites, 56 raw invocations). Of those, **34 are Wego classes** and 6 are library classes (Material `BottomSheetDialog`, `MaterialDatePicker`, `EdgeToEdgeUtils`, AndroidX `EdgeToEdgeApi23/26/29`, Places `AutocompleteImplFragment`). Play Console listed 10 entries due to sampling/dedupe — decoded from the v7.47 release R8 mapping: `ji.e.onCreate` = `BottomSheetDialog.onCreate` (library), `jp.d.invoke` = `BOWAppKt$$ExternalSyntheticLambda2.invoke` (our Compose `setContent` → `BOWRoomSelectionAppV3$lambda$13$...`).

Scope B chosen — fix all 34 Wego classes so the warning doesn't resurface on later scans that sample different sites. Library-origin entries tracked separately.

---

## Fix pattern

```kotlin
if (Build.VERSION.SDK_INT < Build.VERSION_CODES.VANILLA_ICE_CREAM) {  // < 35
    window.statusBarColor = color
}
```

`Build.VERSION_CODES.VANILLA_ICE_CREAM` is API 35 (Android 15). Already used once in this codebase (`SprinklrChatActivity.kt:83`) — no new project constant needed.

---

## Approach — minimize new abstraction

Two change types, keeping the existing code style (`WegoUIUtils.kt` already hosts `Activity` extension helpers for bar color).

### A. Guard inside existing shared helpers (5 sites, covers ~20 callers)

| # | File | Method | Line(s) |
|---|------|--------|---------|
| 1 | `libbase/src/main/java/com/wego/android/util/WegoUIUtils.kt` | `setStatusBarTransparent` | 30 |
| 2 | `libbase/src/main/java/com/wego/android/util/WegoUIUtils.kt` | `setStatusBarColorIcons` | 55, 59 |
| 3 | `libbase/src/main/java/com/wego/android/util/WegoUIUtils.kt` | `setStatusBarColorAndAppearance` | 84 |
| 4 | `wegoauth/src/main/java/com/wego/android/login/utils/WegoAuthUtils.kt` | `setSystemBarTransparent` | 24 |
| 5 | `wegoauth/src/main/java/com/wego/android/login/utils/WegoAuthUtils.kt` | `setSystemBarTransparentBlack` | 32 |

### B. Add two compat extension helpers + migrate ~18 direct call sites

Append to `WegoUIUtils.kt`:
```kotlin
fun Activity.setStatusBarColorCompat(@ColorInt color: Int) {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.VANILLA_ICE_CREAM) {
        window.statusBarColor = color
    }
}

fun Activity.setNavigationBarColorCompat(@ColorInt color: Int) {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.VANILLA_ICE_CREAM) {
        window.navigationBarColor = color
    }
}
```

Direct callers to migrate:

| Module   | File                                                                     | Line(s)       | Current pattern                            |
| -------- | ------------------------------------------------------------------------ | ------------- | ------------------------------------------ |
| hotelsv2 | `features/hoteldetails/HotelDetailsActivity.kt`                          | 103           | `window.statusBarColor =`                  |
| hotelsv2 | `features/hotelsearchresults/HotelSearchResultActivityV2.kt`             | 79            | `window.statusBarColor =`                  |
| hotelsv2 | `features/hotelsearchresults/HotelSearchResultActivityV4.kt`             | 79            | `window.statusBarColor =`                  |
| hotelsv2 | `features/hotelrooms/HotelRoomsActivity.java`                            | 28            | `getWindow().setStatusBarColor(…)`         |
| hotelsv2 | `activities/HotelChooseLocationActivity.java`                            | 174           | `getWindow().setStatusBarColor(…)`         |
| hotels   | `features/hoteldetails/HotelDetailsActivity.kt`                          | 113           | `window.statusBarColor =`                  |
| hotels   | `features/hotelimagegallery/HotelDetailsGalleryGridActivity.kt`          | 104           | `window.statusBarColor =`                  |
| hotels   | `features/hotelrooms/HotelRoomsActivity.java`                            | 27            | `getWindow().setStatusBarColor(…)`         |
| hotels   | `features/hotelsearch/HotelSearchActivity.java`                          | 61            | `getWindow().setStatusBarColor(…)`         |
| hotels   | `features/hotelsearchresults/HotelSearchResultActivity.java`             | 75            | `getWindow().setStatusBarColor(…)`         |
| hotels   | `activities/HotelChooseLocationActivity.java`                            | 212           | `getWindow().setStatusBarColor(…)`         |
| hotels   | `bow/ui/roomselection/BOWRoomSelectionApp.kt`                            | 62            | `window.statusBarColor =` (Compose lambda) |
| flights  | `features/flightsearch/FlightSearchActivity.java`                        | 113           | `getWindow().setStatusBarColor(…)`         |
| flights  | `features/flightsearchresults/FlightSearchResultActivity.java`           | 132           | `getWindow().setStatusBarColor(…)`         |
| flights  | `features/flightchoosepassengers/ChoosePassengersBottomSheetFragment.kt` | 212           | `window.navigationBarColor =`              |
| homebase | `miniapp/MiniAppFragment.kt`                                             | 303, 305, 726 | `activity?.window?.statusBarColor =`       |
| homebase | `miniapp/bowflights/BoWFlightAddonMiniAppFragment.kt`                    | 439, 441, 784 | `activity?.window?.statusBarColor =`       |
| libbase  | `util/WegoUIUtilLib.java`                                                | 1116          | `window.setNavigationBarColor(…)`          |

Java files (`*.java`) call the helper via its synthetic `WegoUIUtilsKt.setStatusBarColorCompat(this, color)` form — matches existing Java interop pattern (e.g., `PaymentTypesActivity.java:34`).

---

## Tests (fresh — none exist today)

### New test file: `libbase/src/test/java/com/wego/android/util/WegoUIUtilsTest.kt`

Covers:
- `setStatusBarColorCompat` × 2 (SDK 34 assigns, SDK 35 skips)
- `setNavigationBarColorCompat` × 2 (SDK 34 assigns, SDK 35 skips)
- `setStatusBarColorIcons` × 2 (SDK guard behavior)
- `setStatusBarTransparent` × 2 (SDK guard behavior)
- `setStatusBarColorAndAppearance` × 2 (status color gated; `WindowInsetsControllerCompat.isAppearanceLightStatusBars` still called on all SDK versions)

### New test file: `wegoauth/src/test/java/com/wego/android/login/utils/WegoAuthUtilsTest.kt`

Covers:
- `setSystemBarTransparent` × 2 (SDK guard behavior)
- `setSystemBarTransparentBlack` × 2 (SDK guard behavior)

### Pattern (MockK + JUnit4)

```kotlin
@Test
fun `given SDK 34 when setStatusBarColorCompat then assigns color`() {
    mockkStatic(Build.VERSION::class)
    every { Build.VERSION.SDK_INT } returns 34
    activity.setStatusBarColorCompat(Color.RED)
    verify { window.statusBarColor = Color.RED }
}

@Test
fun `given SDK 35 when setStatusBarColorCompat then skips assignment`() {
    every { Build.VERSION.SDK_INT } returns 35
    activity.setStatusBarColorCompat(Color.RED)
    verify(exactly = 0) { window.statusBarColor = any() }
}
```

Use `mockkStatic(Build.VERSION::class)` + `unmockkAll()` in `@After`. No `kotlinx-coroutines-test` needed (libbase doesn't have it per memory).

---

## Documentation updates

**None required.** This is a behavior-preserving compliance fix with no API surface change, no DB change, no config change. Existing design docs remain accurate.

---

## Out of scope (separate tickets)

- Library bumps to clear `MaterialDatePicker.onStart`, `BottomSheetDialog.onCreate`, AndroidX `EdgeToEdgeApi23/26/29.setUp`, `EdgeToEdgeUtils.applyEdgeToEdge`, Places `AutocompleteImplFragment.onViewCreated`. Requires `com.google.android.material` + `androidx.activity` version bumps with their own blast-radius validation.
- Full migration to `ActivityCompat.enableEdgeToEdge()` + proper `WindowInsetsCompat` handling throughout. Architectural change. Not required by this warning.
- Refactoring unrelated code in touched files.

---

## Verification

1. **Build passes**
   ```
   ./gradlew :wegoapk:assemblePlaystoreDebug
   ```
2. **Unit tests pass**
   ```
   ./gradlew :libbase:testPlaystoreDebugUnitTest --tests "com.wego.android.util.WegoUIUtilsTest"
   ./gradlew :wegoauth:testPlaystoreDebugUnitTest --tests "com.wego.android.login.utils.WegoAuthUtilsTest"
   ```
3. **Detekt clean** (strict, `maxIssues=0`)
   ```
   ./gradlew detekt
   ```
4. **Device smoke test on Android 15+ emulator** (no visual regression from a missed call site)
   - Build + install via multi-APK flow:
     ```
     ./gradlew :wegoapk:assemblePlaystoreDebug
     android run \
       --apks=wegoapk/build/outputs/apk/playstore/debug/wegoapk-playstore-debug.apk,\
   home/build/outputs/apk/playstore/debug/home-playstore-debug.apk,\
   flexibleairlines/build/outputs/apk/playstore/debug/flexibleairlines-playstore-debug.apk \
       --device=<emulator-id>
     ```
   - Screens to check: Home, Flight search + results, Hotel details (hotels + hotelsv2), Hotel search results, Hotel rooms, Login/auth, Offers, Stories, MiniApp.
5. **Device smoke test on Android 14 emulator** — bar colors still tint correctly on pre-15 (no regression from wrongly-guarded site).
6. **Grep verification** — confirm zero direct `window.statusBarColor =` / `setStatusBarColor(` / `window.navigationBarColor =` / `setNavigationBarColor(` remain outside `WegoUIUtils.kt` / `WegoAuthUtils.kt` / compat helpers:
   ```
   grep -rn --include='*.kt' --include='*.java' \
     'window\.statusBarColor\s*=\|setStatusBarColor(\|window\.navigationBarColor\s*=\|setNavigationBarColor(' \
     | grep -v 'WegoUIUtils\.kt\|WegoAuthUtils\.kt\|setStatusBarColorCompat\|setNavigationBarColorCompat'
   ```
   Expected: empty.
7. **APK dex re-verification** (optional) — re-run dex scan from investigation; expected: only `androidx.*` / `com.google.*` library entries remain.

---

## Acceptance Criteria

- [ ] Build passes: `./gradlew :wegoapk:assemblePlaystoreDebug`
- [ ] `WegoUIUtilsTest` passes with full SDK<35 / SDK≥35 coverage
- [ ] `WegoAuthUtilsTest` passes with full SDK<35 / SDK≥35 coverage
- [ ] `./gradlew detekt` clean
- [ ] Android 15+ smoke test: no visual regression
- [ ] Android 14 smoke test: no regression on pre-15 bar-color behavior
- [ ] Grep verification: empty result
- [ ] (Optional) Dex re-scan: zero Wego invocations remain

---

## Files to change

### Modified (20)

Production code:
- `libbase/src/main/java/com/wego/android/util/WegoUIUtils.kt` — guard 3 helpers + add 2 new compat helpers
- `libbase/src/main/java/com/wego/android/util/WegoUIUtilLib.java` — guard line 1116
- `wegoauth/src/main/java/com/wego/android/login/utils/WegoAuthUtils.kt` — guard 2 helpers
- `hotels/src/main/java/com/wego/android/features/hoteldetails/HotelDetailsActivity.kt`
- `hotels/src/main/java/com/wego/android/features/hotelimagegallery/HotelDetailsGalleryGridActivity.kt`
- `hotels/src/main/java/com/wego/android/features/hotelrooms/HotelRoomsActivity.java`
- `hotels/src/main/java/com/wego/android/features/hotelsearch/HotelSearchActivity.java`
- `hotels/src/main/java/com/wego/android/features/hotelsearchresults/HotelSearchResultActivity.java`
- `hotels/src/main/java/com/wego/android/activities/HotelChooseLocationActivity.java`
- `hotels/src/main/java/com/wego/android/bow/ui/roomselection/BOWRoomSelectionApp.kt`
- `hotelsv2/src/main/java/com/wego/android/hotelfeaturesv2/features/hoteldetails/HotelDetailsActivity.kt`
- `hotelsv2/src/main/java/com/wego/android/hotelfeaturesv2/features/hotelsearchresults/HotelSearchResultActivityV2.kt`
- `hotelsv2/src/main/java/com/wego/android/hotelfeaturesv2/features/hotelsearchresults/HotelSearchResultActivityV4.kt`
- `hotelsv2/src/main/java/com/wego/android/hotelfeaturesv2/features/hotelrooms/HotelRoomsActivity.java`
- `hotelsv2/src/main/java/com/wego/android/hotelfeaturesv2/activities/HotelChooseLocationActivity.java`
- `flights/src/main/java/com/wego/android/features/flightsearch/FlightSearchActivity.java`
- `flights/src/main/java/com/wego/android/features/flightsearchresults/FlightSearchResultActivity.java`
- `flights/src/main/java/com/wego/android/features/flightchoosepassengers/ChoosePassengersBottomSheetFragment.kt`
- `homebase/src/main/java/com/wego/android/homebase/miniapp/MiniAppFragment.kt`
- `homebase/src/main/java/com/wego/android/homebase/miniapp/bowflights/BoWFlightAddonMiniAppFragment.kt`

### Created (2)

- `libbase/src/test/java/com/wego/android/util/WegoUIUtilsTest.kt`
- `wegoauth/src/test/java/com/wego/android/login/utils/WegoAuthUtilsTest.kt`

### Net diff

~60 production lines (most are 1-line edits per site) + ~120 test lines.

---

## Change Log

| Date | Person | Change |
|---|---|---|
| 2026-04-23 | muthuraman@wego.com | Initial plan imported from pre-approved `~/.claude/plans/delegated-percolating-cray.md`. Branch renamed `fix/` → `bug/` per convention. Version target updated to "after v7.48". |
