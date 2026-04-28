# MOBILE-8185 Guard deprecated setStatusBarColor/setNavigationBarColor for Android 15+

**Related Ticket:** https://wegomushi.atlassian.net/browse/MOBILE-8185

### Context

Play Console flagged v7.47.0 under "Your app uses deprecated APIs or parameters for edge-to-edge". On Android 15+ (API 35+), `Window.setStatusBarColor` and `setNavigationBarColor` are silent no-ops; the OS forces edge-to-edge. Dex disassembly found 34 Wego classes making these calls. This PR guards all Wego invocations with `if (Build.VERSION.SDK_INT < Build.VERSION_CODES.VANILLA_ICE_CREAM)` to suppress the warning on v7.49+. Pre-15 behavior (bar tinting) is preserved; Android 15+ skips the deprecated call.

### Approach

1. **New compat helpers** in `libbase/.../WegoUIUtils.kt`:
   - `Activity.setStatusBarColorCompat(@ColorInt Int)` — wraps `window.statusBarColor =` with SDK check
   - `Activity.setNavigationBarColorCompat(@ColorInt Int)` — wraps `window.navigationBarColor =` with SDK check

2. **Guard existing shared helpers** (5 sites):
   - `WegoUIUtils.kt`: `setStatusBarTransparent`, `setStatusBarColorIcons`, `setStatusBarColorAndAppearance`
   - `WegoAuthUtils.kt`: `setSystemBarTransparent`, `setSystemBarTransparentBlack`
   - Covers ~20 downstream callers automatically

3. **Migrate direct call sites** (~18 files):
   - Hotels (6 files): `HotelDetailsActivity`, `HotelRoomsActivity`, `HotelSearchActivity`, `HotelSearchResultActivity`, `HotelChooseLocationActivity`, `BOWRoomSelectionApp`
   - HotelsV2 (5 files): `HotelDetailsActivity`, `HotelRoomsActivity`, `HotelSearchResultActivityV2/V4`, `HotelChooseLocationActivity`
   - Flights (3 files): `FlightSearchActivity`, `FlightSearchResultActivity`, `ChoosePassengersBottomSheetFragment`
   - HomeBase (2 files): `MiniAppFragment`, `BoWFlightAddonMiniAppFragment`
   - Compose/LibBase (2 files): `BOWRoomSelectionApp`, `HotelUpSellActivity`, `WegoUIUtilLib`

4. **Trade-offs**:
   - Chose compat helpers (vs. inline guards everywhere) to centralize logic and reduce diff noise
   - Used `Build.VERSION_CODES.VANILLA_ICE_CREAM` (API 35) constant already in codebase
   - Robolectric @Config(sdk=[X]) for tests — MockK can't mock static final `Build.VERSION.SDK_INT`

### Testing

- **Unit tests**: 15 new tests (11 in `WegoUIUtilsTest.kt`, 4 in `WegoAuthUtilsTest.kt`)
  - Each guarded helper tested on both SDK <35 (call made) and SDK ≥35 (call skipped)
  - Robolectric `@Config(sdk=[34])` / `@Config(sdk=[35])` for compile-time SDK selection
  - All tests pass (100%)

- **Build & static analysis**:
  - `./gradlew :wegoapk:assemblePlaystoreDebug` — PASS (full DFM build, 3m 13s)
  - `./gradlew detekt` — PASS (strict mode, maxIssues=0)

- **Grep verification**:
  - Zero unguarded `window.statusBarColor =` / `setStatusBarColor(...)` / navigation equivalents remain in Wego production code

- **Device smoke tests** (pending, user-driven):
  - Android 14 emulator: bar colors still tint correctly (pre-15 regression guard)
  - Android 15+ emulator: no visual regression on Home, Flights, Hotels, Login, Offers, Stories, MiniApp

### Checklist

- [x] I have commented on hard-to-understand areas or given context in the PR
- [x] Unit tests cover the changes
- [x] Code follows the project's style guidelines (detekt strict mode, 120-char line limit, ext. functions match WegoUIUtils style)
- [ ] Tested according to acceptance criteria
    - [x] Local (build, unit tests, detekt, grep verification)
    - [ ] Device (Android 14/15+ smoke tests — pending emulator availability)
- [x] Dependent changes have been merged (none)
- [x] Documentation updated if needed (none required — behavior-preserving fix)

---

### Out of Scope

Library-origin deprecated calls (`MaterialDatePicker.onStart`, `BottomSheetDialog.onCreate`, AndroidX `EdgeToEdgeApi23/26/29`, Places `AutocompleteImplFragment`) tracked separately — require dependency version bumps, not code changes.

### Files Changed

**Production (20 files):**
- `libbase/.../util/WegoUIUtils.kt` — guarded 3 helpers + added 2 compat helpers + import `@ColorInt`
- `libbase/.../util/WegoUIUtilLib.java` — guarded 1 call
- `wegoauth/.../login/utils/WegoAuthUtils.kt` — guarded 2 helpers
- `libbasewithcompose/.../HotelUpSellActivity.kt` — migrated to compat helper
- `hotels/` (7 files): `HotelDetailsActivity.kt`, `HotelDetailsGalleryGridActivity.kt`, `HotelRoomsActivity.java`, `HotelSearchActivity.java`, `HotelSearchResultActivity.java`, `HotelChooseLocationActivity.java`, `BOWRoomSelectionApp.kt`
- `hotelsv2/` (5 files): `HotelDetailsActivity.kt`, `HotelRoomsActivity.java`, `HotelSearchResultActivityV2.kt`, `HotelSearchResultActivityV4.kt`, `HotelChooseLocationActivity.java`
- `flights/` (3 files): `FlightSearchActivity.java`, `FlightSearchResultActivity.java`, `ChoosePassengersBottomSheetFragment.kt`
- `homebase/` (2 files): `MiniAppFragment.kt`, `BoWFlightAddonMiniAppFragment.kt`
- `wegoauth/build.gradle` — added `testImplementation libs.robolectric`

**Tests (2 new files):**
- `libbase/src/test/java/com/wego/android/util/WegoUIUtilsTest.kt` — 11 tests
- `wegoauth/src/test/java/com/wego/android/login/utils/WegoAuthUtilsTest.kt` — 4 tests

**Net diff:** ~82 insertions / ~40 deletions across 22 files.

---

Co-Authored-By: Claude <noreply@anthropic.com>
