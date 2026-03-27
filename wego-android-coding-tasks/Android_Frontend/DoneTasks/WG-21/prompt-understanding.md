# WG-21: Home Screen Search Tab Experiment (2nd Run) — Prompt Understanding

## Ticket
- **ID**: WG-21
- **Branch**: `feature/GR-21-App-homepage-search-tab-experiment-2nd-run`

## Sub-task 1: Variant Refactor (Binary → Ternary) with V2 Vertical Pill Buttons

### Current State
- `isHomeScreenV2: Boolean` in HomeFragment drives a binary if/else for V1 vs V2.
- V1 (CONTROL + V1): Hero image + big card buttons + logo.
- V2: Green gradient background + greeting text + 56dp horizontal pill buttons.
- Split: CONTROL 80%, V1 10%, V2 10% (unchanged).

### What Changes
| Variant | % | UI |
|---------|---|----|
| CONTROL | 80% | No change — hero image + big card buttons (existing V1 UI) |
| V1 | 10% | Current V2 design — green bg + 56dp horizontal pill buttons |
| V2 | 10% | **New design** — green bg + greeting + **98dp vertical pill buttons** (icon top, text below, white card bg) |

### Key Decisions
- **Approach**: Replace `isHomeScreenV2: Boolean` with `homeScreenVariant: String` + helper properties (`isControl`, `isV1`, `isV2`, `isNewHeader`).
- **V2 component**: Create `HomePillButtonV2` — vertical layout variant of `HomePillButton`. New layout XML + thin wrapper class (layout orientation is fundamentally different: vertical vs horizontal).
- **Collapsed V2**: Uses same 98dp vertical pill button design (not a smaller collapsed variant).
- **Split percentages**: Unchanged (80/10/10).
- **DevSettings**: Update dialog labels to reflect 3 variants (CONTROL, V1, V2).

## Sub-task 2: Mini Apps "Show More"

### Current State
- V2 (`HomeCategoriesSectionViewHolderV2`) shows ALL mini app items in horizontal scroll.
- V1 (`HomeCategoriesSectionViewHolder`) uses grid with 6+More truncation.

### What Changes
- **Responsive width-based**: Show items that fit the screen width, "More" replaces the last visible slot when items overflow.
- ~3-4 items + More on phones < 600dp, more items on wider devices.
- "More" opens existing `HomeCategoriesItemsBottomSheet`.
- Reuse existing `HomeCategoriesItem(isMore=true)` model + `ic_two_tone` icon.
- Skip `applyPortraitPeekLayoutIfNeeded()` when show-more is active.
- Reset on layout width change for orientation/resize recalculation.

## Acceptance Criteria
1. CONTROL (80%) users see unchanged hero image + big buttons.
2. V1 (10%) users see green bg + 56dp horizontal pill buttons (current V2 design).
3. V2 (10%) users see green bg + greeting + 98dp vertical pill buttons.
4. Mini apps section shows items that fit screen width + "More" button when overflow.
5. "More" tapping opens `HomeCategoriesItemsBottomSheet` with full list.
6. DevSettings allows switching between all 3 variants.
7. All builds pass detekt + lint + unit tests.