# FMETA-2579: Foldable PoC — Technical Understanding

## Goal

Proof-of-concept for adaptive two-pane layout on foldable Android devices, scoped to the flight search results flow only. Branch is standalone — never merged to `develop`.

## Current Architecture (Flight Search Flow)

```
FlightSearchResultActivity (Java)       ← entry point, WegoActionbarActivity base
└── FlightSearchResultFragment (Java)   ← host fragment (sort/filter toolbar + list)
    ├── FlightSearchResultListFragment  ← flight results list
    ├── SortOptionsBottomSheet (Kotlin) ← sort: shown as BottomSheet
    └── FlightFilterBottomSheet (Kotlin)← filter: shown as BottomSheetDialogFragment
         (content hosted inside a FrameLayout via FlightFilterBottomSheet)

On flight tap (FlightSearchResultsPresenter.java:1591):
  startActivityForResult → FlightDetailsActivity (Java)
                           └── FlightDetailsFragment (Java)
```

**Key observation:** All search result + details code is Java. Filter/sort wrappers are Kotlin BottomSheetDialogFragments.

---

## Android Adaptive Display — How It Works

### The Right Component: `SlidingPaneLayout`

`SlidingPaneLayout` (from `androidx.slidingpanelayout:slidingpanelayout`) is Google's recommended building block for foldable/large-screen two-pane UIs:

- **Narrow screen (folded phone):** Only the left pane is visible. Right pane is off-screen.
- **Wide screen (unfolded foldable):** Both panes appear side by side.
- **Fold/unfold transition:** SlidingPaneLayout re-measures automatically when the window width changes — the smooth transition the user described is *built-in*.
- No extra WindowManager code is needed just to handle the fold animation — `SlidingPaneLayout` reacts to `onConfigurationChanged` / window resizing natively.

### Optional: Jetpack WindowManager (`androidx.window:window`)

Used for finer-grained fold awareness:
- `WindowInfoTracker` + `FoldingFeature` — detect if device is half-open (table-top), flat (fully open), etc.
- `WindowSizeClass` — categorize width as COMPACT / MEDIUM / EXPANDED.

For this PoC, the `SlidingPaneLayout` automatic behaviour is sufficient. WindowManager can be added if we want to react to *specific* fold states (e.g., different layout at half-open).

---

## Required Components

### 1. New Dependencies

| Dependency | Purpose |
|---|---|
| `androidx.slidingpanelayout:slidingpanelayout:1.2.0` | Two-pane layout with automatic fold/unfold |
| `androidx.window:window:1.3.0` *(optional)* | FoldingFeature / WindowSizeClass detection |
| `androidx.window:window-java:1.3.0` *(optional)* | Java-friendly WindowManager wrapper |

**Files to change:** `gradle/libs.versions.toml` (add version + alias), `flights/build.gradle` (add `implementation`)

---

### 2. New Layout: `activity_flight_search_result_foldable.xml`

```
SlidingPaneLayout (root)
├── FrameLayout  [id: pane_list]        ← left pane — search results
│   layout_width: 0dp, layout_weight: 1
└── FrameLayout  [id: pane_detail]      ← right pane — filter/sort or details
    layout_width: 0dp, layout_weight: 1
```

SlidingPaneLayout measures both children. If their combined width fits the window → side-by-side. If not → single-pane (left only, right slides in). For foldable, "fits" triggers automatically when the device unfolds.

**File to add:** `flights/src/main/res/layout/activity_flight_search_result_foldable.xml`

---

### 3. New Activity: `FlightSearchResultFoldableActivity.java`

Extends `WegoActionbarActivity` (same as the existing `FlightSearchResultActivity`).

Responsibilities:
- Inflate the `SlidingPaneLayout`-based layout
- Load `FlightSearchResultFragment` into the left pane (`pane_list`) on create
- Load the default right pane content (Sort & Filter panel) into `pane_detail`
- Expose a method `showDetailInPane(Bundle extras)` — called when the user taps a flight, shows `FlightDetailsFragment` in `pane_detail` instead of launching a new Activity
- Expose a method `showFilterInPane()` — shows filter UI in `pane_detail`
- On narrow/folded screens: retain existing behavior (launch `FlightDetailsActivity` as usual)

**File to add:** `flights/src/main/java/com/wego/android/features/flightsearchresults/FlightSearchResultFoldableActivity.java`

---

### 4. Right Pane: Sort & Filter Fragment

Currently the filter is a `BottomSheetDialogFragment` (`FlightFilterBottomSheet.kt`). Its internal layout (`flight_filter_bottom_sheet.xml`) is a bare `CoordinatorLayout` + `FrameLayout` — the actual filter content is inflated inside by a nested fragment.

For the right pane we need a plain `Fragment` (no bottom sheet wrapper) that holds the same filter content.

**Approach:**
- Create `FlightSortFilterPaneFragment.kt` — a regular `Fragment` that inflates the filter/sort UI directly (same content as the bottom sheet, minus the drag handle)
- This is mostly a copy-and-simplify of `FlightFilterBottomSheet`'s setup code

**File to add:** `flights/src/main/java/com/wego/android/features/flightsearchresults/FlightSortFilterPaneFragment.kt`
**Layout to add:** `flights/src/main/res/layout/fragment_flight_sort_filter_pane.xml`

---

### 5. Right Pane: Flight Details Fragment

`FlightDetailsFragment.java` already exists but is tightly coupled to `FlightDetailsActivity`:

```java
// FlightDetailsFragment.java:272
if (getActivity() instanceof FlightDetailsActivity)
    mEmailMeButton = ((FlightDetailsActivity) getActivity()).getEmailMeButton();
```

**Approach (minimal change):**
- Extract the `FlightDetailsActivity`-specific cast into a null-safe interface check
- OR: create a thin `FlightDetailsPaneFragment.java` that wraps `FlightDetailsFragment` and satisfies the `FlightDetailsActivity` contract via a delegate interface

For a PoC, the simplest approach is to create `FlightDetailsPaneHost` interface on the parent Activity so `FlightDetailsFragment` can get `emailMeButton` without a hard cast.

**Files to change:** `FlightDetailsFragment.java` (small: add interface null-check) or **add** `FlightDetailsPaneFragment.java` as a thin wrapper

---

### 6. Wiring Flight Selection → Right Pane

Currently in `FlightSearchResultsPresenter.java:1591`:
```java
Intent intent = new Intent(activity, FlightDetailsActivity.class);
((Fragment) getView()).startActivityForResult(intent, REQ_CODE);
```

**Change needed:**
- Check if `activity instanceof FlightSearchResultFoldableActivity`
- If yes → call `activity.showDetailInPane(intent.getExtras())` instead
- If no → existing behavior (startActivityForResult to FlightDetailsActivity)

**File to change:** `FlightSearchResultsPresenter.java` (3–5 lines)

---

### 7. Wiring Filter/Sort → Right Pane

Currently in `FlightSearchResultFragment.java`:
- Sort: tap → `SortOptionsBottomSheet.newInstance(...)` → `dialog.show()`
- Filter: tap → `mListFragment.openFilerBottomSheet()` → `FlightFilterBottomSheet.show()`

**Change needed:**
- In `FlightSearchResultFoldableActivity`, override or intercept these triggers
- If `SlidingPaneLayout.isSlideable() == false` (wide screen) → replace right pane content with `FlightSortFilterPaneFragment` instead of showing bottom sheets
- If `SlidingPaneLayout.isSlideable() == true` (narrow/folded) → existing bottom sheet behavior

**File to change:** `FlightSearchResultFragment.java` (add check) or `FlightSearchResultFoldableActivity.java` (intercept callbacks)

---

### 8. AndroidManifest

**File to change:** `flights/src/main/AndroidManifest.xml`

- Register `FlightSearchResultFoldableActivity`
- Add `android:resizeableActivity="true"` to support multi-window and foldable
- Keep `android:configChanges="screenSize|smallestScreenSize|screenLayout|orientation"` (already on other activities — handles fold events)

---

### 9. Entry Point (for testing)

The PoC needs a way to reach the new foldable Activity. Options:
- **A (no code):** Set `FlightSearchResultFoldableActivity` as the target directly from the search form (modify `FlightSearchActivity` or `FlightSearchResultsPresenter` intent)
- **B (debug toggle):** Add a build-config flag that switches which Activity is launched

For a branch-only PoC, **Option A** is simplest — modify the existing intent construction in `FlightSearchActivity` to point to `FlightSearchResultFoldableActivity`.

**File to change:** Intent construction in `FlightSearchActivity.java` or whichever file builds the `startActivity` call to `FlightSearchResultActivity`

---

## Summary: Complete Change List

| # | Action | File |
|---|--------|------|
| 1 | ADD dependency versions | `gradle/libs.versions.toml` |
| 2 | ADD `implementation` entries | `flights/build.gradle` |
| 3 | ADD layout with SlidingPaneLayout | `flights/res/layout/activity_flight_search_result_foldable.xml` |
| 4 | ADD sort/filter pane layout | `flights/res/layout/fragment_flight_sort_filter_pane.xml` |
| 5 | ADD `FlightSearchResultFoldableActivity.java` | `flights/.../flightsearchresults/` |
| 6 | ADD `FlightSortFilterPaneFragment.kt` | `flights/.../flightsearchresults/` |
| 7 | CHANGE `FlightDetailsFragment.java` | Remove hard cast to `FlightDetailsActivity` (3–5 lines) |
| 8 | CHANGE `FlightSearchResultsPresenter.java` | Check for foldable Activity before `startActivityForResult` (3–5 lines) |
| 9 | CHANGE `FlightSearchResultFragment.java` | Intercept filter/sort taps for wide-screen path |
| 10 | CHANGE `AndroidManifest.xml` | Register new Activity, add `resizeableActivity` |
| 11 | CHANGE entry point (`FlightSearchActivity`) | Route to foldable Activity |

**Estimated file count: 4 new, 7 changed** — all within the `flights` module.

---

## What is "Free" vs. What Requires Work

| Behaviour | Free? | Notes |
|---|---|---|
| Smooth fold/unfold transition | ✅ Yes | SlidingPaneLayout handles it automatically |
| Single-pane on folded/narrow | ✅ Yes | SlidingPaneLayout automatic |
| Two-pane on unfolded/wide | ✅ Yes | SlidingPaneLayout automatic |
| Filter/sort in right pane | ❌ Work needed | Extract bottom sheet content to plain Fragment |
| Flight details in right pane | ❌ Work needed | Remove hard `FlightDetailsActivity` cast |
| Wiring selection → right pane | ❌ Work needed | Presenter check + callback |
| Booking continues in new Activity | ✅ Minimal | Existing `FlightDetailsActivity` flow unchanged |

## Applicable Rules

- `coding-conventions.md` — every code change
- `project-structure.md` — changes within `flights` module only (correct placement)
- `critical-thinking.md` — architectural decisions about fragment coupling
