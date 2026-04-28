# Execution Plan: MOBILE-8174 — Room Selection Code Cleanup

## Summary

Delete all V1 and V2 room selection variant files from the hotels module. Hardcode the Activity to use V3 directly. Clean up detekt baseline and commented-out references.

**Branch:** `feature/mobile-8174-cleanup-room-selection-variants`

## Approach

This is a safe, incremental deletion task. The strategy:
1. Delete V1 files first, then V2 files
2. Simplify the Activity entry point
3. Clean up secondary references (comments, detekt baseline)
4. Build and run tests to verify nothing is broken

**Risk:** Low. V3 code is fully self-contained. All V1/V2 files are only referenced by other V1/V2 files (verified via grep). The only cross-variant touchpoints are in `BOWRoomSelectionActivity.kt` (which we simplify) and one commented-out preview in `LabeledCheckbox.kt`.

## Files to Delete (17 files)

### V1 UI Files (6)
- [ ] `hotels/src/main/java/com/wego/android/bow/ui/roomselection/BOWRoomSelectionApp.kt`
- [ ] `hotels/src/main/java/com/wego/android/bow/ui/roomselection/RoomSelectionScreen.kt`
- [ ] `hotels/src/main/java/com/wego/android/bow/ui/roomselection/RoomSelectionCard.kt`
- [ ] `hotels/src/main/java/com/wego/android/bow/ui/roomselection/RoomBookingCard.kt`
- [ ] `hotels/src/main/java/com/wego/android/bow/ui/roomselection/RoomDetailsSection.kt`
- [ ] `hotels/src/main/java/com/wego/android/bow/ui/roomselection/RoomSelectionBookingCardUI.kt`

### V1 ViewModels (2)
- [ ] `hotels/src/main/java/com/wego/android/bow/viewmodel/BOWRoomSelectionViewModel.kt`
- [ ] `hotels/src/main/java/com/wego/android/bow/viewmodel/RoomBookingCardViewModel.kt`

### V2 UI Files (6)
- [ ] `hotels/src/main/java/com/wego/android/bow/ui/roomselection/BOWRoomSelectionAppV2.kt`
- [ ] `hotels/src/main/java/com/wego/android/bow/ui/roomselection/RoomSelectionScreenV2.kt`
- [ ] `hotels/src/main/java/com/wego/android/bow/ui/roomselection/RoomSelectionCardV2.kt`
- [ ] `hotels/src/main/java/com/wego/android/bow/ui/roomselection/RoomBookingCardV2.kt`
- [ ] `hotels/src/main/java/com/wego/android/bow/ui/roomselection/RoomDetailsSectionV2.kt`
- [ ] `hotels/src/main/java/com/wego/android/bow/ui/roomselection/RoomSelectionBookingCardUIV2.kt`

### V2 ViewModel (1)
- [ ] `hotels/src/main/java/com/wego/android/bow/viewmodel/BOWRoomSelectionViewModelV2.kt`

### Shared by V1/V2 Only (2)
- [ ] `hotels/src/main/java/com/wego/android/bow/ui/roomselection/bottomSheet/RoomDetailsBottomSheet.kt` (V3 has its own `RoomDetailsBottomSheetV3.kt`)
- [ ] `hotels/src/main/java/com/wego/android/bow/ui/roomselection/topbanners/FilterByHeader.kt` (V3 has its own `FilterByHeaderV3.kt`)

## Files to Modify (3 files)

### 1. `BOWRoomSelectionActivity.kt` — Simplify entry point
- Remove variant-checking if/else chain (lines 43-89)
- Remove `roomSelectionUIVariant()` method (lines 92-94)
- Hardcode `BOWRoomSelectionAppV3` directly in `setContent`
- Remove unused imports (`ConstantsLib`, `WegoConfig`)

### 2. `LabeledCheckbox.kt` — Clean commented-out preview
- Remove commented-out code in `PreviewBookingDrawer1()` (lines 88-94) that references `bowRoomBookingCardViewModel`

### 3. `config/detekt/baseline.xml` — Remove stale entries
- Remove all `<ID>` entries referencing deleted files:
  - `FilterByHeader.kt` entries
  - `BOWRoomSelectionApp.kt` entries (if any)
  - `RoomSelectionScreen.kt` entries (if any)
  - Any other entries for files in the delete list

## Files to Keep (Shared — Do NOT Touch)

| File | Reason |
|------|--------|
| `RoomSelectionCardViewModel.kt` | Used by V3 |
| `BOWRoomSelectionViewModelState.kt` | Used by V3 ViewModel |
| `BOWUiStateInterface.kt` | Shared sealed interfaces |
| `RoomSelectionCardViewModelTest.kt` | Tests shared ViewModel |
| `RefreshSearchDialog.kt` | Shared UI |
| `RoomSelectionBottomBar.kt` | Shared UI |
| `RoomSelectionErrorUi.kt` | Shared UI |
| `NoFilterResult.kt` | Shared UI |
| Shimmer files | Shared UI |
| Top banner files (CashBack, PromoCode) | Shared UI |
| Bottom sheet files (ChargesSummary, ItemRoomFeature, PriceTypeFilter) | Shared UI |

## Test Plan

- [x] `./gradlew :hotels:assemblePlaystoreDebug` — Compile check
- [x] `./gradlew :hotels:testPlaystoreDebugUnitTest` — Unit tests pass
- [x] `./gradlew detekt` — Static analysis passes
- [x] Clean build + install + run on device — Room selection screen verified

---

## Phase 2: Rename V3 Files (Remove Suffix)

### Summary

Rename all V3 files and their internal class/function names to remove the "V3" suffix. Now that V1/V2 are gone, V3 is the only variant — the suffix is redundant.

### Files to Rename (10 files via `git mv`)

| Current | New |
|---------|-----|
| `BOWRoomSelectionAppV3.kt` | `BOWRoomSelectionApp.kt` |
| `RoomSelectionScreenV3.kt` | `RoomSelectionScreen.kt` |
| `RoomSelectionCardV3.kt` | `RoomSelectionCard.kt` |
| `RoomBookingCardV3.kt` | `RoomBookingCard.kt` |
| `RoomDetailsSectionV3.kt` | `RoomDetailsSection.kt` |
| `RoomSelectionBookingCardUIV3.kt` | `RoomSelectionBookingCardUI.kt` |
| `BOWRoomSelectionViewModelV3.kt` | `BOWRoomSelectionViewModel.kt` |
| `RoomBookingCardViewModelV3.kt` | `RoomBookingCardViewModel.kt` |
| `RoomDetailsBottomSheetV3.kt` | `RoomDetailsBottomSheet.kt` |
| `FilterByHeaderV3.kt` | `FilterByHeader.kt` |

### Internal Renames Per File

| File | What to rename |
|------|---------------|
| `BOWRoomSelectionApp` | Function `BOWRoomSelectionAppV3` → `BOWRoomSelectionApp` |
| `RoomSelectionScreen` | Function `RoomSelectionScreenV3` → `RoomSelectionScreen` |
| `RoomSelectionCard` | Function `RoomSelectionCardV3` → `RoomSelectionCard`, TAG constant |
| `RoomBookingCard` | Function `RoomBookingCardV3` → `RoomBookingCard` |
| `RoomDetailsSection` | Function `RoomDetailsSectionV3` → `RoomDetailsSection` |
| `RoomSelectionBookingCardUI` | Function `RoomSelectionBookingCardUIV3` → `RoomSelectionBookingCardUI` |
| `BOWRoomSelectionViewModel` | Class `BOWRoomSelectionViewModelV3` → `BOWRoomSelectionViewModel`, factory, log strings |
| `RoomBookingCardViewModel` | Class `RoomBookingCardViewModelV3` → `RoomBookingCardViewModel` |
| `RoomDetailsBottomSheet` | Functions: `RoomDetailsBottomSheetViewV3` → `RoomDetailsBottomSheetView`, `RoomAmenitiesViewV3` → `RoomAmenitiesView`, `RoomAmenityCategoriesViewV3` → `RoomSelectionAmenityCategoriesView` (see naming note below), log string |
| `FilterByHeader` | Function `FilterByBannerV3` → `FilterByBanner` |

### External References to Update (1 file)

- `BOWRoomSelectionActivity.kt` — 2 calls to `BOWRoomSelectionAppV3` → `BOWRoomSelectionApp`

### Naming Conflict Resolution

`RoomAmenityCategoriesView` exists in both `RoomAmenityComponents.kt` (old style, used by `HotelDetailsPager.kt`) and was `RoomAmenityCategoriesViewV3` in `RoomDetailsBottomSheet.kt` (V3 style, used by room selection). Same function signature but different visual styling (bold vs regular text, different spacing).

**Resolution:** Rename by screen context, not by version:
- `RoomAmenityCategoriesView` stays in `RoomAmenityComponents.kt` — old style for `HotelDetailsPager.kt` (existing code untouched)
- `RoomAmenityCategoriesViewV3` → `RoomSelectionAmenityCategoriesView` in `RoomDetailsBottomSheet.kt` — V3 style for room selection

### Detekt Baseline

- ~138 entries: find-replace V3 suffixes in file names and class names

### Test Plan (Phase 2)

- [x] `./gradlew :wegoapk:assemblePlaystoreDebug` — Full app build
- [x] `./gradlew :hotels:testPlaystoreDebugUnitTest` — Unit tests pass
- [x] `./gradlew detekt` — Static analysis passes
- [x] Clean build + install + run on device — Room selection verified

## Execution Tracking
- **Started:** 2026-04-09
- **Developer:** muthuraman@wego.com
- **Branch:** feature/mobile-8174-cleanup-room-selection-variants
- **PR:** https://github.com/wego/wego-android-n/pull/2015

## Change Log
| Date | Change |
|------|--------|
| 2026-04-09 | Phase 1 completed — V1/V2 deleted, committed and pushed |
| 2026-04-09 | Phase 2 completed — V3 suffix removed, naming conflict resolved |
| 2026-04-09 | PR #2015 created (Ready for Review) |
