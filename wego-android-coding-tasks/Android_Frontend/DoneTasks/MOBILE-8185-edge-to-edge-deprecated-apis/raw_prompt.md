# [Wego Android] Migrate away from deprecated edge-to-edge APIs (setStatusBarColor / setNavigationBarColor) on Android 15+

**Jira Ticket:** https://wegomushi.atlassian.net/browse/MOBILE-8185
**Type:** Task
**Priority:** Medium (Play Console advisory — not a crash)

## Description

### Problem

Play Console flagged v7.47.0 (release `1274701401`) under **"Your app uses deprecated APIs or parameters for edge-to-edge"**. On Android 15+ (API 35), the OS forces edge-to-edge display; `android.view.Window.setStatusBarColor` and `android.view.Window.setNavigationBarColor` become silent no-ops. The app continues to render correctly on 15+ because layouts already use `fitsSystemWindows` and `WindowInsetsCompat`, but Play Console wants the dead deprecated calls removed.

On API ≤ 34, the setters still paint the bars — any fix must preserve pre-15 behavior.

### Play Console listing (10 entries)

```
android.view.Window.setStatusBarColor
android.view.Window.setNavigationBarColor

These start in the following places:
1.  com.wego.android.util.WegoUIUtilsKt.setStatusBarColorIcons
2.  com.wego.android.util.WegoUIUtilsKt.setStatusBarTransparent
3.  com.google.android.material.datepicker.MaterialDatePicker.onStart
4.  ji.e.onCreate               (R8-obfuscated)
5.  jp.d.invoke                 (R8-obfuscated)
6.  com.wego.android.features.hoteldetails.HotelDetailsActivity.editStatusBar
7.  com.wego.android.features.hotelimagegallery.HotelDetailsGalleryGridActivity.editStatusBar
8.  com.wego.android.hotelfeaturesv2.features.hoteldetails.HotelDetailsActivity.editStatusBar
9.  com.wego.android.libbasewithcompose.hoteleducationcomponent.HotelUpSellActivity.onCreate
10. com.wego.android.login.utils.WegoAuthUtils$Companion.setSystemBarTransparent
```

### Investigation (dex-disassembled v7.47.0 release APK + R8 mapping)

APK's compiled bytecode contains **40 distinct classes** invoking the deprecated APIs — 54 unique `(class, method, api)` tuples, 56 raw invocations.

| Origin | Count | Fixable here? |
|---|---|---|
| Wego code | **34 classes** | ✅ Yes |
| AndroidX / Material / Places libraries | **6 classes** | ❌ No — needs dependency bumps (separate ticket) |

**Decoded R8 obfuscation from v7.47 `mapping.txt`:**
- `ji.e.onCreate` → `com.google.android.material.bottomsheet.BottomSheetDialog.onCreate` (library)
- `jp.d.invoke` → `com.wego.android.bow.ui.BOWAppKt$$ExternalSyntheticLambda2.invoke` → `BOWRoomSelectionAppV3$lambda$13$lambda$1$lambda$0` (our Compose `setContent` lambda)

**Summary:** of the 10 Play Console entries → **7 Wego + 3 library**. Play Console's selection is a sample — the other ~27 Wego classes calling the same deprecated API are not surfaced this release, but will likely bubble up on later scans if left unfixed.

### Solution — Scope B (comprehensive)

Guard every Wego invocation with `if (Build.VERSION.SDK_INT < Build.VERSION_CODES.VANILLA_ICE_CREAM) { ... }` (API 35 constant, already used once in the codebase at `SprinklrChatActivity.kt:83` — no new project constant needed).

**Change consolidation:**
- Guard inside **5 existing shared helpers** in `libbase/.../WegoUIUtils.kt` and `wegoauth/.../WegoAuthUtils.kt` — covers ~20 downstream callers automatically with zero caller-side changes
- Add **2 new extension helpers** `Activity.setStatusBarColorCompat(Int)` and `Activity.setNavigationBarColorCompat(Int)` in `WegoUIUtils.kt` (consistent with the file's existing extension style)
- Migrate **~18 direct call sites** (Activities/Fragments/Compose lambdas) to use the new compat helpers instead of assigning `window.statusBarColor` directly

**Net diff:** ~60 production lines across ~21 files (most are 1-line edits) + ~120 test lines.

### Out of scope (separate tickets)

- **Library dependency bumps** to clear `MaterialDatePicker.onStart`, `BottomSheetDialog.onCreate`, AndroidX `EdgeToEdgeApi23/26/29.setUp`, `EdgeToEdgeUtils.applyEdgeToEdge`, Places `AutocompleteImplFragment.onViewCreated`. Requires `com.google.android.material` + `androidx.activity` version bumps with their own blast-radius validation.
- **Full migration to `ActivityCompat.enableEdgeToEdge()` + `WindowInsetsCompat`** throughout. Architectural change. Not required by the Play Console warning — left for a dedicated initiative.

## Acceptance Criteria

- [ ] Build passes: `./gradlew :wegoapk:assemblePlaystoreDebug`
- [ ] New unit tests pass: `:libbase:testPlaystoreDebugUnitTest` for `WegoUIUtilsTest`, `:wegoauth:testPlaystoreDebugUnitTest` for `WegoAuthUtilsTest`
- [ ] Detekt clean (strict mode, `maxIssues=0`): `./gradlew detekt`
- [ ] Android 15+ emulator smoke test — no visual regression on Home, Flight search+results, Hotel details (hotels + hotelsv2), Hotel search results, Hotel rooms, Login/auth, Offers, Stories, MiniApp screens
- [ ] Android 14 emulator smoke test — bar colors still tint correctly on pre-15 (no regression from a wrongly-guarded site)
- [ ] Grep verification: zero direct `window.statusBarColor =` / `setStatusBarColor(` / `window.navigationBarColor =` / `setNavigationBarColor(` outside the compat helpers
- [ ] Optional: APK dex re-scan confirms only `androidx.*` / `com.google.*` library entries remain as invokers (no Wego classes)

---

*Ticket created on 2026-04-23. Investigation summary carried over from prior session (dex analysis + R8 mapping decode). Full implementation plan pre-approved at `~/.claude/plans/delegated-percolating-cray.md`.*
