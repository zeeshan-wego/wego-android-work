# MOBILE-8174: Code Cleanup - Room Selection Screen

**Jira Ticket:** https://wegomushi.atlassian.net/browse/MOBILE-8174

## Objective

Remove V1 and V2 room selection variant code from the hotels module, keeping only V3. This is a pure deletion/cleanup task with no logic changes.

## Background

The room selection screen uses a Firebase Remote Config flag (`a_bow_hotels_room_selection_ui_variant_config`) to switch between 3 UI variants (v1, v2, v3). V3 is the current production variant. V1 and V2 are dead code that should be removed.

The variant system is purely client-side (config is never sent to backend).

## What to Do

1. **Delete all V1 and V2 files** (UI composables, ViewModels, bottom sheets, filter headers)
2. **Hardcode V3** in `BOWRoomSelectionActivity.kt` — remove variant-checking logic, always use `BOWRoomSelectionAppV3`
3. **Keep V3 files as-is** with the "V3" suffix (no renaming in this task)
4. **Keep** `ConstantsLib.BOWRoomSelectionUIVariant` interface and Firebase Remote Config key (may be used by config dashboard)
5. **Clean up** any commented-out references to deleted classes (e.g., `LabeledCheckbox.kt`)
6. **Clean up** detekt baseline entries for deleted files

## What NOT to Do

- Do NOT rename V3 files (no suffix removal)
- Do NOT change any V3 logic
- Do NOT remove the variant constants from `ConstantsLib.java`
- Do NOT remove the Firebase Remote Config key
- Do NOT write new tests — this is purely a deletion task

## Shared Code (Must NOT Be Touched)

These are used by V3 and must remain:

- `RoomSelectionCardViewModel` — card-level ViewModel used by all 3 variants
- `BOWRoomSelectionViewModelState` — state data class used by all 3 main ViewModels
- `BOWUiStateInterface.kt` — sealed interfaces (BOWRoomSelectionUiState, etc.)
- `BOWRoomSelectionActivity.kt` — entry point (will be simplified, not deleted)
- Shared UI components: `RefreshSearchDialog`, `RoomSelectionBottomBar`, `ErrorUi`, `NoFilterResult`, shimmers, `CashBackTopBanner`, `PromoCodeTopBanner`, `ChargesSummaryBottomSheet`, `ItemRoomFeature`, `PriceTypeFilterBottomSheet`
- Test file: `RoomSelectionCardViewModelTest.kt`

## Acceptance Criteria

- [ ] All V1/V2 room selection files deleted
- [ ] Activity hardcoded to V3 (no variant switching)
- [ ] V3 room selection screen works identically to before
- [ ] Project compiles without errors
- [ ] Detekt passes
- [ ] Existing unit tests pass
- [ ] No logic changes to V3 code

## Applicable Rules

- `critical-thinking.md` — Verify every deletion doesn't break V3 references before removing
- `coding-conventions.md` — Ensure Activity changes follow project formatting
