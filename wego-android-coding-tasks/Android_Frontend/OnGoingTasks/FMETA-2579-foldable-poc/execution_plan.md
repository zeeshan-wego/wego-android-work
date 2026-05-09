# FMETA-2579: Foldable PoC — Execution Plan

## Execution Tracking
- **Started:** 2026-04-23
- **Developer:** bima@wego.com
- **Branch:** feature/fmeta-2579-foldable-poc
- **Collaborators:** (none)

---

## Summary

Proof-of-concept for adaptive two-pane layout on foldable Android devices, scoped to the flight search results flow. On a wide/unfolded screen, search results appear on the left and flight details appear on the right pane when a trip is tapped. On a narrow/folded screen, the existing full-screen results flow is preserved. The booking flow after details continues unchanged in a new Activity.

**Phase 1 only** (13 SP). Phase 2 (filter/sort in right pane, 12 SP) is deferred.
Branch is standalone — never merged to `develop`.

---

## Approach

Use `SlidingPaneLayout` from `androidx.slidingpanelayout`. It automatically handles:
- **Narrow/folded:** left pane fills screen, right pane off-screen
- **Wide/unfolded:** both panes side-by-side
- **Fold/unfold transition:** re-measures on window resize — smooth transition is built-in

The new `FlightSearchResultFoldableActivity` is the entry point. On wide screens, tapping a flight calls `showDetailInPane(Bundle)` which loads `FlightDetailsFragment` into the right pane. On narrow screens, the existing `startActivityForResult → FlightDetailsActivity` path is used unchanged.

---

## Trade-offs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Two-pane primitive | `SlidingPaneLayout` | Custom `LinearLayout` + `WindowSizeClass` | SlidingPaneLayout gives fold/unfold transition for free |
| Right pane default state | Empty / placeholder | Show filter | Deferred to Phase 2; simpler Phase 1 |
| Fragment coupling fix | `FlightDetailsPaneHost` interface | Rewrite fragment | Minimal change, preserves existing behaviour |
| Entry point | Swap intent target in `FlightSearchActivity` | Feature flag | PoC branch — no need for a flag |

---

## Deliverables

| File | Purpose |
|---|---|
| Working APK on foldable emulator | Demonstrates two-pane search + detail flow |
| `implementation-log.md` (in task folder) | **Living document** — updated throughout the PoC. Records each implementation step, issues found, conflicts, workarounds, and learnings. This is the primary output for informing Phase 2 scoping and future foldable work. |

---

## Files to Change

### New Files
| File | Module | Purpose |
|---|---|---|
| `flights/src/main/res/layout/activity_flight_search_result_foldable.xml` | flights | `SlidingPaneLayout` root with left + right `FrameLayout` panes |
| `flights/src/main/java/com/wego/android/features/flightdetails/FlightDetailsPaneHost.java` | flights | Interface so `FlightDetailsFragment` can get `emailMeButton` without hard-casting to `FlightDetailsActivity` |
| `flights/src/main/java/com/wego/android/features/flightsearchresults/FlightSearchResultFoldableActivity.java` | flights | New foldable-aware Activity; hosts `SlidingPaneLayout`; exposes `showDetailInPane(Bundle)` |

### Modified Files
| File | Change |
|---|---|
| `gradle/libs.versions.toml` | Add `slidingpanelayout` version + alias |
| `flights/build.gradle` | Add `implementation libs.androidx.slidingpanelayout` |
| `flights/src/main/AndroidManifest.xml` | Register `FlightSearchResultFoldableActivity` with `resizeableActivity=true` |
| `flights/src/main/java/com/wego/android/features/flightdetails/FlightDetailsActivity.java` | Implement `FlightDetailsPaneHost` interface |
| `flights/src/main/java/com/wego/android/features/flightdetails/FlightDetailsFragment.java` | Swap `instanceof FlightDetailsActivity` cast to `instanceof FlightDetailsPaneHost` (lines 272-273) |
| `flights/src/main/java/com/wego/android/features/flightsearchresults/FlightSearchResultsPresenter.java` | At line 1591: add `instanceof FlightSearchResultFoldableActivity` check — route to `showDetailInPane()` on wide screen, else existing `startActivityForResult` |
| `flights/src/main/java/com/wego/android/features/flightsearch/FlightSearchActivity.java` | Swap intent target from `FlightSearchResultActivity.class` to `FlightSearchResultFoldableActivity.class` |

---

## Implementation Steps

### Step 1 — Dependencies (I-1)
**File:** `gradle/libs.versions.toml`
- Add under `[versions]`: `slidingpanelayoutVersion = "1.2.0"`
- Add under `[libraries]`: `androidx-slidingpanelayout = { module = "androidx.slidingpanelayout:slidingpanelayout", version.ref = "slidingpanelayoutVersion" }`

**File:** `flights/build.gradle`
- Add: `implementation libs.androidx.slidingpanelayout`

### Step 2 — Layout (I-2)
**File:** `activity_flight_search_result_foldable.xml`
```xml
<androidx.slidingpanelayout.widget.SlidingPaneLayout
    android:id="@+id/sliding_pane_layout"
    ...>

    <!-- Left pane: search results -->
    <FrameLayout
        android:id="@+id/pane_list"
        android:layout_width="0dp"
        android:layout_weight="1"
        android:layout_height="match_parent" />

    <!-- Right pane: flight details (empty until a flight is tapped) -->
    <FrameLayout
        android:id="@+id/pane_detail"
        android:layout_width="0dp"
        android:layout_weight="1"
        android:layout_height="match_parent" />

</androidx.slidingpanelayout.widget.SlidingPaneLayout>
```
Both panes use `layout_weight=1` so they share screen space equally on wide screens.

### Step 3 — FlightDetailsPaneHost interface (W-2, part 1)
**File:** `FlightDetailsPaneHost.java` (new)
```java
public interface FlightDetailsPaneHost {
    View getEmailMeButton();
}
```

**File:** `FlightDetailsActivity.java`
- Add `implements FlightDetailsPaneHost` to class declaration (method `getEmailMeButton()` already exists)

**File:** `FlightDetailsFragment.java` (lines 272-273)
- Change `if (getActivity() instanceof FlightDetailsActivity)` → `if (getActivity() instanceof FlightDetailsPaneHost)`
- Change cast `((FlightDetailsActivity) getActivity())` → `((FlightDetailsPaneHost) getActivity())`

### Step 4 — FlightSearchResultFoldableActivity (I-5)
**File:** `FlightSearchResultFoldableActivity.java` (new)

Key logic:
```java
public class FlightSearchResultFoldableActivity extends WegoActionbarActivity {

    private SlidingPaneLayout mSlidingPaneLayout;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        mLayoutRes = R.layout.activity_flight_search_result_foldable;
        super.onCreate(savedInstanceState);

        mSlidingPaneLayout = findViewById(R.id.sliding_pane_layout);

        // Load search results into left pane (same fragment as before)
        if (savedInstanceState == null) {
            initFragment(mOrigin, mDestination); // reuse same init pattern
        }
    }

    public boolean isTwoPaneMode() {
        return !mSlidingPaneLayout.isSlideable();
    }

    public void showDetailInPane(Bundle extras) {
        FlightDetailsFragment fragment = new FlightDetailsFragment();
        fragment.setArguments(extras);
        getSupportFragmentManager()
            .beginTransaction()
            .replace(R.id.pane_detail, fragment)
            .commit();
        // On slideable (narrow): open the right pane by sliding it in
        if (mSlidingPaneLayout.isSlideable()) {
            mSlidingPaneLayout.openPane();
        }
    }

    @Override
    public View getEmailMeButton() {
        // Foldable Activity provides null — email button is not in this layout
        return null;
    }
}
```
- Implements `FlightDetailsPaneHost` so `FlightDetailsFragment` can call `getEmailMeButton()` (returns null — email share is a non-critical feature for this PoC)
- Extends `WegoActionbarActivity` for consistent action bar, back press, and inset handling
- Reuses `initFragment()` pattern from `FlightSearchResultActivity` for left pane setup

### Step 5 — Presenter routing (W-3)
**File:** `FlightSearchResultsPresenter.java` (~line 1588)

Before (current):
```java
FlightSearchResultActivity activity = (FlightSearchResultActivity) getActivity();
Intent intent = new Intent(activity, FlightDetailsActivity.class);
intent.putExtras(prepareFlightHandoffBundle(selectedItem, resultAdapter).getExtras());
((Fragment) getView()).startActivityForResult(intent, ConstantsLib.SavedInstance.FlightDetail.REQ_CODE);
```

After:
```java
Activity activity = getActivity();
Bundle detailBundle = prepareFlightHandoffBundle(selectedItem, resultAdapter).getExtras();

if (activity instanceof FlightSearchResultFoldableActivity
        && ((FlightSearchResultFoldableActivity) activity).isTwoPaneMode()) {
    ((FlightSearchResultFoldableActivity) activity).showDetailInPane(detailBundle);
} else {
    Intent intent = new Intent(activity, FlightDetailsActivity.class);
    intent.putExtras(detailBundle);
    ((Fragment) getView()).startActivityForResult(intent, ConstantsLib.SavedInstance.FlightDetail.REQ_CODE);
}
```

### Step 6 — Register in Manifest (I-3)
**File:** `flights/src/main/AndroidManifest.xml`
```xml
<activity
    android:name="com.wego.android.features.flightsearchresults.FlightSearchResultFoldableActivity"
    android:configChanges="screenSize|smallestScreenSize|screenLayout|orientation"
    android:resizeableActivity="true"
    android:screenOrientation="unspecified"
    android:exported="false"
    android:theme="@style/FlightSearchResultsTheme" />
```

### Step 7 — Route entry point (I-6)
**File:** `FlightSearchActivity.java`
- Find the `startActivity` call(s) that launch `FlightSearchResultActivity`
- Change target class to `FlightSearchResultFoldableActivity`

---

## Test Plan

| Test | How | Expected |
|---|---|---|
| Normal phone (folded) — search results | Run app on folded foldable or regular phone | Full-screen results, no two-pane |
| Normal phone — tap flight | Tap a result | `FlightDetailsActivity` launches as before |
| Foldable (unfolded) — search results | Open app on unfolded screen | Left pane = results, right pane = empty |
| Foldable (unfolded) — tap flight | Tap a result | Right pane shows flight details in-place |
| Foldable — unfold while on results | Open on folded, then unfold | Smooth transition to two-pane, no crash |
| Foldable — fold while detail is shown | Tap flight → unfold → fold | Detail slides away, full-screen results |
| Foldable — tap Book in right-pane details | Tap book button | `BowFlightActivity` launches in full screen (unchanged) |
| Detekt | `./gradlew detekt` | No new violations |
| Unit tests | `./gradlew :flights:testPlaystoreDebugUnitTest` | All pass |

---

## Acceptance Criteria

- [ ] On an unfolded foldable, search results open in a two-pane layout (left: results list, right: empty)
- [ ] Tapping a flight on wide screen loads `FlightDetailsFragment` in the right pane without launching a new Activity
- [ ] On a narrow/folded screen, the existing flow (full-screen results → `FlightDetailsActivity`) is completely unchanged
- [ ] Fold/unfold transition is smooth with no crash or visual glitch
- [ ] Booking flow (after flight details) continues in a new Activity as before
- [ ] Detekt passes with zero violations
- [ ] All existing unit tests pass

---

## Phase 2 (Deferred — 12 SP)

| Item | SP | Risk |
|---|---|---|
| `fragment_flight_sort_filter_pane.xml` | 2 | Low |
| Extend Foldable Activity with `showFilterInPane()` | 2 | Low |
| `FlightSortFilterPaneFragment.kt` + intercept sort/filter taps | 8 | Medium-High (dual sort path, 60-method listener) |

---

## Change Log

| Date | Person | Change |
|---|---|---|
| 2026-04-23 | bima@wego.com | Initial plan created (Phase 1 only; Phase 2 deferred) |
