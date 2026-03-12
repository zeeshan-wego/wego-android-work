# WG-21: Execution Plan

## Branch
`feature/GR-21-App-homepage-search-tab-experiment-2nd-run` (existing)

---

## Sub-task 1: Variant Refactor + V2 Vertical Pill Buttons

### Step 1.1 — Create `component_home_pill_button_v2.xml`
Vertical layout: ConstraintLayout, 98dp height, white card bg with rounded corners, icon (32dp) top, text (14sp) below.

### Step 1.2 — Create `HomePillButtonV2.kt`
Thin wrapper following `HomePillButton.kt` pattern. Inflates `component_home_pill_button_v2`. Reuses `HomePillButton` styleable attrs.

### Step 1.3 — Add V2 containers to `frag_home.xml`
- `pillButtonV2Container` in expanded area (below greeting, above big buttons) — contains two `HomePillButtonV2` (Flights, Hotels).
- `toolbarPillButtonV2Container` in collapsed toolbar — contains two `HomePillButtonV2` (same 98dp height).

### Step 1.4 — Refactor `HomeFragment.kt`
- Replace `isHomeScreenV2: Boolean` with `homeScreenVariant: String`.
- Add helper properties: `isControl`, `isV1`, `isV2`, `isNewHeader` (V1 || V2).
- Refactor `setupHomeScreenVersion()` from if/else → 3-way `when`:
  - CONTROL: Show hero + big buttons (existing V1 path)
  - V1: Show green bg + greeting + 56dp horizontal pills (existing V2 path)
  - V2: Show green bg + greeting + 98dp vertical pills (new path)
- Wire V2 button click listeners.
- Update all `isHomeScreenV2` references to use new helper properties.

### Step 1.5 — Update `DevSettingViewModel.kt`
Update labels: "V1 (Green + Pill Buttons)", "V2 (Green + Vertical Pill Buttons)", "CONTROL (Hero + Big Buttons)".

---

## Sub-task 2: Mini Apps "Show More" Width Logic

### Step 2.1 — Modify `HomeCategoriesSectionViewHolderV2.kt`
1. Store `allFeatures` list from original data.
2. Add `hasAppliedShowMore` flag.
3. Add `applyShowMoreIfNeeded()`:
   - Post-layout: measure RecyclerView width.
   - Calculate how many items fit using measured child width.
   - If all fit → show all, no "More" needed.
   - If overflow → truncate to (fitting - 1) + append "More" `HomeCategoriesItem`.
   - Update adapter via `setData()`.
4. Skip `applyPortraitPeekLayoutIfNeeded()` when show-more truncated the list.
5. Reset on layout width change (existing listener already present).

---

## Files

### CREATE
| File | Purpose |
|------|---------|
| `homebase/src/main/res/layout/component_home_pill_button_v2.xml` | Vertical pill button layout |
| `homebase/src/main/java/.../components/HomePillButtonV2.kt` | Thin wrapper class |

### MODIFY
| File | Changes |
|------|---------|
| `home/.../HomeFragment.kt` | Binary→ternary variant logic |
| `home/.../frag_home.xml` | Add V2 pill button containers |
| `home/.../HomeCategoriesSectionViewHolderV2.kt` | Responsive "Show more" |
| `home/.../DevSettingViewModel.kt` | Update variant labels |

### NO CHANGES
| File | Reason |
|------|--------|
| `HomeScreenVariantAssignmentUtils.java` | Split % stays same |
| `HomePillButton.kt` / `component_home_pill_button.xml` | Pattern reference only |
| `HomeCategoriesItemsAdapter.kt` | Already handles MORE_ITEM viewType |
| `HomeItemClickHandleUtil.kt` | Already handles isMore click → bottom sheet |
| `CommonBindings.kt` | Already binds ic_two_tone for isMore items |

---

## Sub-task 3: Port V2 Pill Buttons to layout-large (Tablet)

### Step 3.1 — Update `layout-large/frag_home.xml`
- Updated V2 green gradient height from 115dp → 122dp (matching normal layout).
- Added `pillButtonV2Container` with two `HomePillButtonV2` buttons (identical to normal layout).
- Clarified comment labels: V1 (horizontal 56dp) vs V2 (vertical 98dp) for both expanded and collapsed toolbar buttons.

### Step 3.2 — Regenerate detekt baseline
- Pre-commit hook runs full-project `./gradlew detekt` which had 25 pre-existing violations in unrelated files.
- Ran `./gradlew detektBaseline` to capture existing issues in `config/detekt/baseline.xml`.
- No rules changed or loosened — new violations still caught.

---

## Sub-task 4: Fix Weegio Icon Showing in V1/V2

### Problem
`setUpWeegioIcon()` (line 293 in `onViewCreated`) runs for ALL variants and sets `ivWeegioHome` back to VISIBLE when the feature flag is on — undoing the `GONE` set by `setupNewHeaderVariant()`.

### Fix
Added early-return `if (isNewHeader) return` at the top of `setUpWeegioIcon()`. Guard is inside the method (not at call site) so any future callers are also protected.

---

## Sub-task 5: Fix V2 Header Overlap and Collapsed Button Border

### Problem
- Categories section overlapping V2 vertical pill buttons — `HEADER_HEIGHT_V2_DP` (190dp) was too short for 98dp buttons.
- V2 collapsed pill buttons had no border, looking inconsistent with V1 collapsed style.

### Fix
- Increased `HEADER_HEIGHT_V2_DP` from 190dp → 210dp to give V2 buttons enough space.
- Adjusted categories top padding to 24dp (bottom stays 16dp) for better spacing.
- Created `bg_home_pill_button_collapsed_v2.xml` — ripple drawable with `line_divider` border stroke.
- Moved background ownership from XML to `HomePillButtonCollapsed.kt` for variant-specific styling.

### Files
| File | Changes |
|------|---------|
| `home/.../HomeFragment.kt` | Bump `HEADER_HEIGHT_V2_DP` to 210 |
| `home/.../HomeCategoriesSectionViewHolderV2.kt` | Adjust category padding (24dp top, 16dp bottom) |
| `homebase/.../HomePillButtonCollapsed.kt` | Set variant-specific background drawable |
| `homebase/.../drawable/bg_home_pill_button_collapsed_v2.xml` | New ripple drawable with border |
| `homebase/.../component_home_pill_button_collapsed.xml` | Remove hardcoded background (now set by component) |

---

## Sub-task 6: V2 Pill Button Slide-Up Animation, Ripple, and Spring Press

### Problem
- V2 pill buttons appeared instantly with no entrance animation.
- `ViewPropertyAnimator` (`view.animate()`) didn't work inside `CollapsingToolbarLayout` — toolbar scroll mechanics override view properties, and `ANIMATOR_DURATION_SCALE=0x` (common dev setting) causes instant completion.
- Pill buttons had no touch feedback (no ripple, no press state).

### Root Cause
`ViewPropertyAnimator` relies on `ValueAnimator` which respects `Settings.Global.ANIMATOR_DURATION_SCALE`. The legacy `Animation` API (`AnimationUtils.loadAnimation` + `startAnimation`) bypasses this and works correctly inside `AppBarLayout` scroll hierarchies.

### Fix
1. **Animation**: Created `slide_in_from_bottom_pill_v2.xml` (translate + alpha, 500ms) and rewrote `animateV2PillButtons()` to use `Animation` API with 120ms stagger between Flights and Hotels pills.
2. **Ripple**: Updated `bg_home_pill_button_v2.xml` and `bg_home_pill_button_collapsed_v2.xml` from plain `<shape>` to `<ripple>` drawables with `colorControlHighlight` mask.
3. **Spring press**: Added `HomePillButtonV2.kt` touch listener — 3% scale shrink on press (0.97f), 100ms down / 200ms up with `FastOutSlowInInterpolator`. Constants extracted to companion object for detekt compliance.
4. **Null safety cleanup**: Removed unnecessary `?.` and `?: return` on `pillButtonV2Container` (non-null in binding since it exists in both `layout/` and `layout-large/`).

### Files
| File | Changes |
|------|---------|
| `homebase/.../anim/slide_in_from_bottom_pill_v2.xml` | New slide-up + fade animation XML |
| `home/.../HomeFragment.kt` | Rewrote `animateV2PillButtons()` to use `Animation` API; null safety cleanup |
| `homebase/.../HomePillButtonV2.kt` | Added spring press effect with companion constants + explanatory comment |
| `homebase/.../drawable/bg_home_pill_button_v2.xml` | Converted to ripple drawable |
| `homebase/.../drawable/bg_home_pill_button_collapsed_v2.xml` | Converted to ripple drawable |
| `home/.../layout/frag_home.xml` | Added `clipChildren="false"` on V2 container |
| `home/.../layout-large/frag_home.xml` | Added `clipChildren="false"` on V2 container |

---

## Pending
- 4 remaining unnecessary `?.` safe calls in HomeFragment.kt (lines 504-505 in `setupNewHeaderButtonClickListeners` and 734-735 in `revealWithoutAnimation`) — `btHomeFlightsV2Vertical` and `btHomeHotelsV2Vertical` are non-null in binding.

---

## Verification
1. `./gradlew :wegoapk:assemblePlaystoreDebug`
2. `./gradlew detekt`
3. `./gradlew :home:testPlaystoreDebugUnitTest`
4. `./gradlew :homebase:testPlaystoreDebugUnitTest`