# Execution Summary — MOBILE-8185

## Current State
- **Phase:** 4 (Finish) — code-reviewer + doc-writer agents running in parallel
- **Branch:** `bug/MOBILE-8185-edge-to-edge-deprecated-apis` (22 files + 2 new tests, all unstaged, NO commits yet)
- **Last Action:** Hotel Details smoke test on Android 14 (Pixel_8, SDK 34) confirmed — white status bar is pre-existing `bg_surface` paint from `editStatusBar()`, not a regression. Git blame confirms behavior unchanged since initial commit. User chose option (a): keep MOBILE-8185 scope focused, no follow-up needed.

## Results

### ✅ Build
- `./gradlew :wegoapk:assemblePlaystoreDebug` — **PASS** (3m 13s, full DFM build)

### ✅ Unit tests — 20 tests, 100% pass
- `:libbase:testPlaystoreDebugUnitTest --tests "WegoUIUtilsTest"` — 11 tests PASS (Robolectric `@Config(sdk=[X])` per test)
- `:wegoauth:testPlaystoreDebugUnitTest --tests "WegoAuthUtilsTest"` — 4 tests PASS

### ✅ Detekt
- `./gradlew detekt` — **PASS** (strict mode, maxIssues=0)

### ✅ Grep verification
- No unguarded `window.statusBarColor = ...` / `setStatusBarColor(...)` / navigation equivalents remain in Wego production code
- Only hits: test files (expected) + 2 inline-guarded sites (already correctly guarded by preceding `if (SDK < VANILLA_ICE_CREAM)`)

## Files changed (22)

### Modified — production (19)
- `libbase/.../util/WegoUIUtils.kt` — guarded 3 helpers + added `setStatusBarColorCompat`/`setNavigationBarColorCompat` + `@ColorInt` import
- `libbase/.../util/WegoUIUtilLib.java` — inline guard on `setNavigationBarColor` (line ~1116)
- `wegoauth/.../login/utils/WegoAuthUtils.kt` — guarded 2 helpers
- `libbasewithcompose/.../HotelUpSellActivity.kt` — migrated to `setStatusBarColorCompat`
- `hotels/.../features/hoteldetails/HotelDetailsActivity.kt`
- `hotels/.../features/hotelimagegallery/HotelDetailsGalleryGridActivity.kt`
- `hotels/.../features/hotelrooms/HotelRoomsActivity.java`
- `hotels/.../features/hotelsearch/HotelSearchActivity.java`
- `hotels/.../features/hotelsearchresults/HotelSearchResultActivity.java`
- `hotels/.../activities/HotelChooseLocationActivity.java`
- `hotels/.../bow/ui/roomselection/BOWRoomSelectionApp.kt` — Compose SideEffect refactored
- `hotelsv2/.../features/hoteldetails/HotelDetailsActivity.kt`
- `hotelsv2/.../features/hotelrooms/HotelRoomsActivity.java`
- `hotelsv2/.../features/hotelsearchresults/HotelSearchResultActivityV2.kt`
- `hotelsv2/.../features/hotelsearchresults/HotelSearchResultActivityV4.kt`
- `hotelsv2/.../activities/HotelChooseLocationActivity.java`
- `flights/.../features/flightsearch/FlightSearchActivity.java`
- `flights/.../features/flightsearchresults/FlightSearchResultActivity.java`
- `flights/.../features/flightchoosepassengers/ChoosePassengersBottomSheetFragment.kt` — inline guard (dialog.window)
- `homebase/.../miniapp/MiniAppFragment.kt` — 3 sites migrated
- `homebase/.../miniapp/bowflights/BoWFlightAddonMiniAppFragment.kt` — 3 sites migrated

### Modified — build (1)
- `wegoauth/build.gradle` — added `testImplementation libs.robolectric` (new test dependency)

### Created — tests (2)
- `libbase/src/test/java/com/wego/android/util/WegoUIUtilsTest.kt` — 11 tests
- `wegoauth/src/test/java/com/wego/android/login/utils/WegoAuthUtilsTest.kt` — 4 tests

**Net diff:** ~82 insertions / ~40 deletions across 22 files.

## Remaining (Phase 4 — Finish)

1. **Device smoke test** (user-driven — requires emulators):
   - Android 14 emulator: verify bar colors still tint correctly (no pre-15 regression)
   - Android 15+ emulator: verify no visual regression
2. **Optional: APK dex re-scan** — confirm only `androidx.*`/`com.google.*` library entries remain as deprecated-API invokers
3. **Code review** — invoke `code-reviewer` agent on staged diff
4. **Create ticket.md** — product-level description for Jira
5. **Create pr-description.md** — PR body
6. **Commit** on `bug/MOBILE-8185-edge-to-edge-deprecated-apis` — via `github-commit` skill
7. **Push + create PR** — via `github-pr` skill

## Q&A Log
- Ticket → MOBILE-8185 (user created in Jira)
- Scope → B (all 34 Wego classes)
- Library bumps → Separate ticket
- Unit tests → Yes, Robolectric `@Config(sdk=[X])` for SDK gating (MockK can't mock `Build.VERSION.SDK_INT` static final field)
- Branch prefix → `bug/`
- Target release → after v7.48
- ChoosePassengersBottomSheet (dialog.window) → inline guard, not compat helper (helper is Activity-scoped)
- HotelUpSellActivity — was missed in first pass, caught by grep verification, fixed
- Robolectric added to wegoauth test deps — only ~4 wegoauth tests but needed for `@Config(sdk=[X])`

## Files in this task folder
- `raw_prompt.md`
- `prompt-understanding.md`
- `execution_plan.md`
- `execution-summary.md` — this file
