# FMETA-2579: Foldable PoC — Effort Estimation

## Story Point Scale (Fibonacci)

**1 SP baseline task:** Register `FlightSearchResultFoldableActivity` in `AndroidManifest.xml` — add one `<activity>` block, add `android:resizeableActivity="true"`. Single file, no logic, zero risk.

| SP | What it means | Approx time |
|----|--------------|-------------|
| 1 | Trivial config / single-line change | < 30 min |
| 2 | Isolated, small change, clear solution | ~1 hr |
| 3 | Straightforward new code, low unknowns | ~2-3 hr |
| 5 | Moderate complexity, some decisions | ~4-6 hr |
| 8 | Complex, coupling/architecture involved | ~1-2 days |
| 13 | Very complex or high uncertainty | ~3-4 days |

---

## Phase 1 — Core Two-Pane Flow

**Scope:** On wide/unfolded screen, show search results on the left and flight details on the right when a trip is tapped. On narrow/folded screen, full-screen results as today. Booking continues in a new Activity unchanged.

| # | Item | Key Facts | SP | Risk |
|---|------|-----------|----|------|
| I-1 | Add `SlidingPaneLayout` dep to `libs.versions.toml` + `flights/build.gradle` | ~3 lines each, zero logic | **1** | Low |
| I-2 | `activity_flight_search_result_foldable.xml` — `SlidingPaneLayout` with left + right `FrameLayout` panes | Straightforward XML, layout weights only; right pane starts empty | **1** | Low |
| I-3 | Register `FlightSearchResultFoldableActivity` in `AndroidManifest.xml` *(baseline)* | One `<activity>` block, `resizeableActivity=true` | **1** | Low |
| I-5 | `FlightSearchResultFoldableActivity.java` — loads `FlightSearchResultFragment` in left pane; exposes `showDetailInPane(Bundle)`; uses `SlidingPaneLayout.isSlideable()` | Simpler than original estimate — no filter/sort routing; right pane is empty until a flight is tapped | **3** | Low-Medium |
| W-2 | Remove hard cast to `FlightDetailsActivity` in `FlightDetailsFragment.java` | Exactly 1 cast (line 272-273); add `FlightDetailsPaneHost` interface (5 lines); swap cast; already null-safe | **2** | Low |
| W-3 | Presenter routing: result tap → right pane (`FlightSearchResultsPresenter.java`) | Add `instanceof FlightSearchResultFoldableActivity` check at line 1591; reuse existing `prepareFlightHandoffBundle()` (27 extras, all Serializable) for `setArguments()`; ~50 new lines | **3** | Low |
| I-6 | Route entry point in `FlightSearchActivity.java` to `FlightSearchResultFoldableActivity` | Find intent construction (1-2 spots), swap class reference | **2** | Low |

**Phase 1 Total: 13 SP**

---

## Phase 2 — Filter & Sort in Right Pane

**Scope:** When on wide/unfolded screen, show sort & filter in the right pane instead of as bottom sheets.

| # | Item | Key Facts | SP | Risk |
|---|------|-----------|----|------|
| I-4 | `fragment_flight_sort_filter_pane.xml` — layout for right-pane filter/sort content | Mirror bottom sheet UI minus drag handle | **2** | Low |
| I-5b | Extend `FlightSearchResultFoldableActivity` with `showFilterInPane()` method | Additive to Phase 1 Activity; loads sort/filter pane fragment into right container | **2** | Low |
| W-1 | `FlightSortFilterPaneFragment.kt` + intercept sort/filter taps in `FlightSearchResultFragment` | Filter view is pre-built by `FlightFilterNewMenu` (60-method listener); wrapping is simpler than rebuilding. **Hidden risk:** dual sort paths (`drawSortOptionDialog` legacy + `SortOptionsBottomSheet`) guarded by `isSortBottomSheetEnabled()` — must audit which path is live before touching intercept. 4 touch points in `FlightSearchResultFragment.java` (1,752 lines) + backstack decisions | **8** | Medium-High |

**Phase 2 Total: 12 SP**

---

## Summary

| Phase | Scope | SP | Risk |
|-------|-------|----|------|
| **Phase 1** | Two-pane layout, flight details in right pane on tap, full-screen on fold | **13** | Low |
| **Phase 2** | Filter & sort panel in right pane instead of bottom sheets | **12** | Medium-High |
| **Grand Total** | | **25** | |

---

## Notes

- **Phase 1 risk is low end-to-end** — the only non-trivial item is I-5 (new Activity). W-2 and W-3 are small, isolated changes.
- **W-1 (Phase 2) is the highest-risk item.** The dual sort path must be audited before any interception code is written. If both paths are conditionally live, this could escalate to **13 SP**.
- **Phase 2 W-1 depends on Phase 1 I-5b** — the Activity method `showFilterInPane()` must exist first.
- The entire PoC is self-contained in the `flights` module. No other module is touched.
