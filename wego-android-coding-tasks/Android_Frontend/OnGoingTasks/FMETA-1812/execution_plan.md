# Execution Plan: Flight Time Timebox Filter (FMETA-1812)

**Ticket:** FMETA-1812
**Branch:** `feature/fmeta-1812-timebox-filter`

---

## Summary

Replace the existing min/max range time filter with a 4-box multi-select timebox filter for departure and arrival times. The feature is gated behind Remote Config flag `a_fmeta1812_timebox_filter_variant` (v1 = off, v2 = on). Covers standard flights (one-way + round trip), per-leg (PL), and multi-city.

---

## Current State of Branch

Two commits already exist on `origin/feature/fmeta-1812-timebox-filter`:
- `FlightSearchResultsFilterAdapter` has `TYPE_FLIGHT_TIME_FILTER = 82` and `FlightTimeFilterViewHolder` with single-selection logic
- Drawables and layout (`row_filter_flight_time.xml`) are in place

**What remains (this task):**
- Change single-selection → multi-selection in the ViewHolder
- Add `List<String>` filter state fields to `WegoFlightResultFilter`
- Update filter menus to gate on feature flag and build timebox items correctly
- Update internal filtering logic to match against selected boxes
- Update analytics tracking keys and value format
- Add feature flag
- Update per-leg and multi-city paths

---

## Approach

### Step 1 — Feature Flag (`ConstantsLib.java` + `WegoUtilLib.java`)

**`ConstantsLib.java` → `FirebaseRemoteConfigKeys`:**
```java
String TIMEBOX_FILTER_VARIANT = "a_fmeta1812_timebox_filter_variant";
```

**`WegoUtilLib.java`:**
```java
public static boolean isTimeboxFilterEnabled() {
    String variant = WegoConfig.instance.getString(ConstantsLib.FirebaseRemoteConfigKeys.TIMEBOX_FILTER_VARIANT);
    return "v2".equalsIgnoreCase(variant);
}
```

---

### Step 2 — Filter State Model (`WegoFlightResultFilter.java`)

Add 4 new `List<String>` fields alongside the existing Long fields:

```java
// Timebox selections (empty = no filter / default)
public List<String> timeboxDepartTakeoff = new ArrayList<>();      // outbound departure
public List<String> timeboxDepartLandingOw = new ArrayList<>();    // outbound arrival
public List<String> timeboxReturnTakeoff = new ArrayList<>();      // inbound departure
public List<String> timeboxReturnLandingTw = new ArrayList<>();    // inbound arrival
```

Add "is default" helpers (empty list = default):
```java
public boolean isTimeboxDepartTakeoffDefault() { return timeboxDepartTakeoff.isEmpty(); }
public boolean isTimeboxDepartLandingOwDefault() { return timeboxDepartLandingOw.isEmpty(); }
public boolean isTimeboxReturnTakeoffDefault() { return timeboxReturnTakeoff.isEmpty(); }
public boolean isTimeboxReturnLandingTwDefault() { return timeboxReturnLandingTw.isEmpty(); }
```

Add setter methods that notify listener:
```java
public void setTimeboxDepartTakeoff(List<String> boxes) {
    timeboxDepartTakeoff = boxes;
    if (listener != null) listener.onFilterChanged(this);
}
// (repeat for other 3 fields)
```

Also update `isAllDefault()` to include timebox fields.

---

### Step 3 — TimeFilterListener Interface + ViewHolder (`FlightSearchResultsFilterAdapter.java`)

**Change the listener interface:**
```java
// Old
void onTimeFilterSelected(FILTER_ITEM_TYPE filterItemType, long lowest, long highest, int index);

// New
void onTimeFilterSelected(FILTER_ITEM_TYPE filterItemType, List<String> selectedBoxes);
```

**Update `FlightTimeFilterViewHolder.bind()`:**

The ViewHolder needs to:
1. Accept a `List<String>` of currently selected boxes (passed via a wrapper model — see Step 4)
2. On click: toggle the tapped box in/out of the selection, then call `onTimeFilterSelected` with the updated `List<String>`

```java
// Box label constants
private static final String[] BOX_LABELS = {"0000-0600", "0600-1200", "1200-1800", "1800-2400"};

public void bind(TimeboxFilterMenuItem currItem) {
    List<String> selectedBoxes = new ArrayList<>(currItem.getSelectedBoxes());
    label.setText(currItem.getTitleString());

    for (int i = 0; i < sectionButtons.size(); i++) {
        final int index = i;
        sectionButtons.get(i).setSelected(selectedBoxes.contains(BOX_LABELS[index]));
        sectionButtons.get(i).setOnClickListener(v -> {
            String box = BOX_LABELS[index];
            List<String> updated = new ArrayList<>(currItem.getSelectedBoxes());
            if (updated.contains(box)) {
                updated.remove(box);
            } else {
                updated.add(box);
            }
            timeFilterListener.onTimeFilterSelected(currItem.getItemType(), updated);
        });
    }
}
```

---

### Step 4 — New Filter Menu Model (`TimeboxFilterMenuItem.java`)

Create a new model class (in `flights` module or `libbase`) to carry timebox state instead of using `BaseFilterMenuItem<Long>`:

```java
public class TimeboxFilterMenuItem {
    private BaseFilterMenuItem.FILTER_ITEM_TYPE itemType;
    private String titleString;
    private List<String> selectedBoxes = new ArrayList<>();

    // getters/setters
}
```

> **Note:** If `BaseFilterMenuItem` can be generified to hold `List<String>`, that's an alternative. Prefer a new class to avoid breaking existing filter items.

---

### Step 5 — Filter Menu Setup (`FlightFilterNewMenu.java`)

Update `setupTakeOffTimeFilter(isReturn, isDepart)`:

```java
protected void setupTakeOffTimeFilter(boolean isReturn, boolean isDepart) {
    String title = /* existing title logic */;

    if (WegoUtilLib.isTimeboxFilterEnabled()) {
        TimeboxFilterMenuItem item = new TimeboxFilterMenuItem();
        item.setTitleString(title);
        item.setItemType(/* same FILTER_ITEM_TYPE logic as before */);
        // Set currently selected boxes from WegoFlightResultFilter
        if (!isReturn && isDepart) {
            item.setSelectedBoxes(allFilters.timeboxDepartTakeoff);
        } else if (!isReturn) {
            item.setSelectedBoxes(allFilters.timeboxDepartLandingOw);
        } else if (isDepart) {
            item.setSelectedBoxes(allFilters.timeboxReturnTakeoff);
        } else {
            item.setSelectedBoxes(allFilters.timeboxReturnLandingTw);
        }
        filterMenuItems.add(item); // TYPE_FLIGHT_TIME_FILTER
    } else {
        // existing seekbar setup (no change)
    }
}
```

**Update the `timeFilterListener` in `FlightFilterNewMenu`:**

```java
private final FlightSearchResultsFilterAdapter.TimeFilterListener timeFilterListener =
    (filterItemType, selectedBoxes) -> {
        allFilters.userModifiedFilterTypes.add(filterItemType);
        switch (filterItemType) {
            case DEPART_TAKEOFF:
                allFilters.setTimeboxDepartTakeoff(selectedBoxes);
                break;
            case ARRIVE_LANDING_OW:
                allFilters.setTimeboxDepartLandingOw(selectedBoxes);
                break;
            case RETURN_TAKEOFF:
                allFilters.setTimeboxReturnTakeoff(selectedBoxes);
                break;
            case ARRIVE_LANDING_TW:
                allFilters.setTimeboxReturnLandingTw(selectedBoxes);
                break;
        }
        mListener.applyFilter(allFilters, false);
        mListener.trackSortAndFilterItemChange(ConstantsLib.AnalyticsActionFlight.FILTER);
    };
```

---

### Step 6 — Internal Filter Logic

#### 6a. `FlightListProcessingUtil.java` (standard flights)

Add helper to check timebox match:
```java
private boolean matchesTimebox(long flightMinutes, List<String> selectedBoxes) {
    if (selectedBoxes == null || selectedBoxes.isEmpty()) return true; // no filter
    long[][] ranges = {{0, 359}, {360, 719}, {720, 1079}, {1080, 1439}};
    String[] labels = {"0000-0600", "0600-1200", "1200-1800", "1800-2400"};
    for (int i = 0; i < labels.length; i++) {
        if (selectedBoxes.contains(labels[i])) {
            if (flightMinutes >= ranges[i][0] && flightMinutes <= ranges[i][1]) return true;
        }
    }
    return false;
}
```

In `satisfyFilter()`, branch on feature flag:
```java
if (WegoUtilLib.isTimeboxFilterEnabled()) {
    if (!matchesTimebox(takeoffTimeMinutes, filter.timeboxDepartTakeoff)) return false;
    if (!matchesTimebox(landingTimeMinutes, filter.timeboxDepartLandingOw)) return false;
    if (froLeg != null) {
        if (!matchesTimebox(returnTakeoffMinutes, filter.timeboxReturnTakeoff)) return false;
        if (!matchesTimebox(returnLandingMinutes, filter.timeboxReturnLandingTw)) return false;
    }
} else {
    // existing min/max range check (no change)
}
```

> **Note:** `takeoffTime` is currently computed in seconds (`WegoDateUtilLib.getTimeFromString()`), then compared to `filterTakeoffDepartTimeFrom * 60`. Verify the unit used for `flightMinutes` here is consistent with the 0–1439 range.

#### 6b. `PLFilterUtil.kt` (per-leg)

Same pattern — add `matchesTimebox()` and branch on `isTimeboxFilterEnabled()` in `satisfyTripFilterDepartArivalTimesForFirstLeg()` and `satisfyTripFilterDepartArivalTimesForSecondLeg()`.

#### 6c. `MultiCityListProcessingUtil.java` (multi-city)

Same pattern — add `matchesTimebox()` helper and branch in the time filter check.

---

### Step 6d. Per-Leg Specifics (`flightspl` module)

**Key difference:** `PLFlightFilterMenu` overrides the parent's `setupTakeOffTimeFilter(isReturn, isDepart)` with an **empty body** (line 203) and uses its own `setupTakeOffTimeFilters(isReturn, isDepart, originCity, destCity)` instead. Changes to the parent will NOT propagate.

**`PLFlightFilterMenu.setupTakeOffTimeFilters()`:**
- Currently creates `BaseFilterMenuItem<Long>(TYPE_SEEKBAR)` — needs timebox gate
- When `isTimeboxFilterEnabled()`: create `TimeboxFilterMenuItem` with `TYPE_FLIGHT_TIME_FILTER`, read from `allFilters.timebox*` fields
- When off: existing seekbar logic (no change)
- PL handles `currentLegIndex` — outbound filters for leg 0, return filters when `onlyReturnFlightFilter`
- Has "show more" toggles for arrival time (`ARRIVE_LANDING_OW`, `ARRIVE_LANDING_TW`) — ensure timebox items work with this show/hide mechanism

**`PLFilterUtil.kt`:**
- `satisfyTripFilterDepartArivalTimesForFirstLeg(toLeg, filter)` and `satisfyTripFilterDepartArivalTimesForSecondLeg(froLeg, filter)` — add `isTimeboxFilterEnabled()` branch using `matchesTimebox()` for the 4 time fields
- Uses `FlightLeg.departureTimeMinutes` and `FlightLeg.arrivalTimeMinutes` — same minute-from-midnight unit as the box ranges

**`GenzoPLFlightSearchResultHelper.kt`:**
- Has a per-leg API with `analyticsLegId` parameter, different from standard `GenzoFlightSearchResultHelper`
- Add 4 new methods (mirroring existing per-leg pattern):
  - `getSelectedDepartureTimeBoxes(filter, analyticsLegId, HashMap)` — reads `filter.timeboxDepartTakeoff`
  - `getSelectedReturnDepartureTimeBoxes(filter, analyticsLegId, HashMap)` — reads `filter.timeboxReturnTakeoff`
  - `getSelectedArrivalTimeBoxes(filter, analyticsLegId, HashMap)` — reads `filter.timeboxDepartLandingOw`
  - `getSelectedReturnArrivalTimeBoxes(filter, analyticsLegId, HashMap)` — reads `filter.timeboxReturnLandingTw`
- Return `HashMap<String, List<String>>` (instead of `HashMap<String, List<Int>>`)

**`PLFlightSearchResultsViewModel.kt`:**
- Around lines 2367-2370: gate the departure/arrival time helper calls — use timebox methods when flag is on
- Around lines 2440-2450: use `departuretime_box_selected` / `arrivaltime_box_selected` keys when flag is on

---

### Step 7 — Analytics (`GenzoFlightSearchResultHelper.kt` + `FlightSearchResultsPresenter.java`)

**`GenzoFlightSearchResultHelper.kt`** — add new methods alongside existing ones:

```kotlin
fun getSelectedDepartureTimeBoxes(filter: WegoFlightResultFilter, tripType: TripType?): Map<String, List<String>>? {
    val result = hashMapOf<String, List<String>>()
    if (filter.timeboxDepartTakeoff.isNotEmpty()) result["1"] = filter.timeboxDepartTakeoff
    if (tripType == TripType.ROUND_TRIP && filter.timeboxReturnTakeoff.isNotEmpty()) result["2"] = filter.timeboxReturnTakeoff
    return result.ifEmpty { null }
}

fun getSelectedArrivalTimeBoxes(filter: WegoFlightResultFilter, tripType: TripType?): Map<String, List<String>>? {
    val result = hashMapOf<String, List<String>>()
    if (filter.timeboxDepartLandingOw.isNotEmpty()) result["1"] = filter.timeboxDepartLandingOw
    if (tripType == TripType.ROUND_TRIP && filter.timeboxReturnLandingTw.isNotEmpty()) result["2"] = filter.timeboxReturnLandingTw
    return result.ifEmpty { null }
}
```

**`FlightSearchResultsPresenter.java`** — in the analytics event construction, branch on flag:

```java
if (WegoUtilLib.isTimeboxFilterEnabled()) {
    // New keys
    Map<String, List<String>> selDepartBoxes = GenzoFlightSearchResultHelper.INSTANCE
        .getSelectedDepartureTimeBoxes(filter, tripType);
    if (selDepartBoxes != null && !selDepartBoxes.isEmpty())
        obj.put("departuretime_box_selected", selDepartBoxes);
    else if (filter.userModifiedFilterTypes.contains(DEPART_TAKEOFF) || ...)
        obj.put("departuretime_box_selected", new HashMap<>());
    // Same for arrivaltime_box_selected
} else {
    // Existing departuretime_selected / arrivaltime_selected (no change)
}
```

---

## Execution Batches

### Batch 1 — Foundation (Steps 1+2)
**Files:** `ConstantsLib.java`, `WegoUtilLib.java`, `WegoFlightResultFilter.java`
**Build:** `./gradlew :flights:assemblePlaystoreDebug`
**Device testable:** No

### Batch 2 — UI Components (Steps 3+4)
**Files:** `FlightSearchResultsFilterAdapter.java`, new `TimeboxFilterMenuItem.java`
**Build:** `./gradlew :flights:assemblePlaystoreDebug`
**Device testable:** No

### Batch 3 — Menu Wiring (Step 5 + 6d menu part)
**Files:** `FlightFilterNewMenu.java`, `PLFlightFilterMenu.kt`, `MulticityFlightFilterMenu.java`
**Build:** `./gradlew :flights:assemblePlaystoreDebug :flightspl:assemblePlaystoreDebug :multicity:assemblePlaystoreDebug`
**Device testable:** Yes
- Set Remote Config `a_fmeta1812_timebox_filter_variant = v2`
- One-way search → open filter → 4 timebox buttons visible for departure
- Round trip → departure + arrival boxes for both legs
- Per-leg → same, per current leg
- Tapping toggles visual state (selected/deselected)
- Flights won't filter yet (that's Batch 4)

### Batch 4 — Filter Logic (Step 6 + 6d filter part)
**Files:** `FlightListProcessingUtil.java`, `PLFilterUtil.kt`, `MultiCityListProcessingUtil.java`
**Build:** `./gradlew :flights:assemblePlaystoreDebug :flightspl:assemblePlaystoreDebug :multicity:assemblePlaystoreDebug`
**Device testable:** Yes
- Select "0600-1200" → only flights departing 6am–noon shown
- Select multiple boxes → flights in any selected range shown
- Deselect all → all flights return
- Test one-way, round trip, per-leg separately
- Set flag to `v1` → old seekbar filter appears and works

### Batch 5 — Analytics: Standard (Step 7 standard)
**Files:** `GenzoFlightSearchResultHelper.kt`, `FlightSearchResultsPresenter.java`
**Build:** `./gradlew :flights:assemblePlaystoreDebug`
**Device testable:** Yes
- Toggle departure box → logcat shows `departuretime_box_selected` with `{"1": ["0600-1200"]}`
- Toggle arrival box → `arrivaltime_box_selected`
- Flag `v1` → old `departuretime_selected` / `arrivaltime_selected` still fire

### Batch 6 — Analytics: PL + Multi-city (Step 7 PL + multi-city)
**Files:** `GenzoPLFlightSearchResultHelper.kt`, `PLFlightSearchResultsViewModel.kt`, `GenzoMultiCityFlightSearchResultHelper.kt`
**Build:** `./gradlew :flightspl:assemblePlaystoreDebug :multicity:assemblePlaystoreDebug`
**Device testable:** Yes
- Per-leg: toggle box → verify `departuretime_box_selected` with leg ID in map
- Round trip → verify leg "2" appears
- Multi-city → same verification

### Prompt template for each batch
```
task-flow-remember

Working on FMETA-1812. Implement Batch N from execution_plan.md:
- [list the specific steps]
Build after: [build command from batch definition]
Run tests in background after build passes.
```

---

## Files to Change

| File | Module | Change |
|------|--------|--------|
| `ConstantsLib.java` | `libbase` | Add `TIMEBOX_FILTER_VARIANT` key |
| `WegoUtilLib.java` | `libbase` | Add `isTimeboxFilterEnabled()` |
| `WegoFlightResultFilter.java` | `flights` | Add 4 `List<String>` timebox fields + helpers |
| `TimeboxFilterMenuItem.java` | `flights` (new) | New model for timebox filter menu item |
| `FlightSearchResultsFilterAdapter.java` | `flights` | Multi-select ViewHolder, updated listener interface |
| `FlightFilterNewMenu.java` | `flights` | Gate `setupTakeOffTimeFilter` with flag, updated listener |
| `FlightListProcessingUtil.java` | `flights` | `matchesTimebox()` + flag branch in `satisfyFilter()` |
| `GenzoFlightSearchResultHelper.kt` | `flights` | Add `getSelectedDepartureTimeBoxes()` + `getSelectedArrivalTimeBoxes()` |
| `FlightSearchResultsPresenter.java` | `flights` | Use new tracking keys when flag is on |
| `PLFlightFilterMenu.kt` | `flightspl` | Update `setupTakeOffTimeFilters()` with timebox gate — parent method overridden with empty body, so changes must be made here directly |
| `PLFilterUtil.kt` | `flightspl` | Add `matchesTimebox()` + flag branch in `satisfyTripFilterDepartArivalTimesForFirstLeg()` and `satisfyTripFilterDepartArivalTimesForSecondLeg()` |
| `GenzoPLFlightSearchResultHelper.kt` | `flightspl` | Add `getSelectedDepartureTimeBoxes()`, `getSelectedArrivalTimeBoxes()`, `getSelectedReturnDepartureTimeBoxes()`, `getSelectedReturnArrivalTimeBoxes()` methods (per-leg API with `analyticsLegId` param) |
| `PLFlightSearchResultsViewModel.kt` | `flightspl` | Use new `departuretime_box_selected` / `arrivaltime_box_selected` keys when flag is on (around lines 2443-2450) |
| `MulticityFlightFilterMenu.java` | `multicity` | Gate `setupTakeOffTimeFilter` or inherit if already does |
| `MultiCityListProcessingUtil.java` | `multicity` | `matchesTimebox()` + flag branch |
| `GenzoMultiCityFlightSearchResultHelper.kt` | `multicity` | Same tracking updates as `GenzoFlightSearchResultHelper` |

## Files NOT Changed

| File | Reason |
|------|--------|
| `row_filter_flight_time.xml` | Already added in feature branch |
| `bg_filter_flight_time*.xml` | Already in feature branch |
| `FlightSearchResultsContract.java` | No interface changes needed |
| `BaseFilterMenuItem.java` | Keeping existing model; new `TimeboxFilterMenuItem` added instead |

---

## Test Plan

| Test | Type | What |
|------|------|------|
| `PLFilterUtilTest.kt` | Unit | Add cases: single box selected, multiple boxes, no boxes (no filter), deselect all |
| `PLListProcessingUtilTest.kt` | Unit | Add timebox filter cases for first leg and second leg |
| `ApplyFilterExtensionTest.kt` | Unit | Add timebox cases if filter extension is tested here |
| Manual | — | Toggle single box → flights in that time range shown |
| Manual | — | Toggle multiple boxes → flights in any selected range shown |
| Manual | — | Deselect all → all flights shown (filter cleared) |
| Manual | — | Round trip: verify inbound + outbound each filter independently |
| Manual | — | Flag OFF: verify old seekbar still works |
| Manual | — | Verify analytics `departuretime_box_selected` fires with correct array |

---

## Acceptance Criteria

- [ ] Timebox UI shown when `a_fmeta1812_timebox_filter_variant = v2`; old UI shown for v1
- [ ] All 4 boxes independently selectable; multiple boxes can be active
- [ ] Deselecting all boxes clears the filter (all flights shown)
- [ ] Filter applied to: one-way depart/arrive, round trip outbound/inbound depart/arrive, per-leg
- [ ] Internal filtering correctly matches flights to selected time boxes
- [ ] Analytics fires `departuretime_box_selected` and `arrivaltime_box_selected` with correct `List<String>` values per leg
- [ ] Old analytics keys (`departuretime_selected`, `arrivaltime_selected`) still fire when flag is v1
