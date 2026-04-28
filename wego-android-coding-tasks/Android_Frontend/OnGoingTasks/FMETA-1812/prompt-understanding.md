# FMETA-1812: Flight Time Timebox Filter

**Jira:** https://wegomushi.atlassian.net/browse/FMETA-1812

## What

Replace the existing min/max range-based flight time filter with a new "timebox" filter — 4 selectable buttons representing 4 blocks of the day (00:00–06:00, 06:00–12:00, 12:00–18:00, 18:00–24:00). Users can select multiple time boxes at once.

This applies to:
- Departure time filter (outbound + inbound for round trip)
- Arrival time filter (outbound + inbound for round trip)
- Per-leg filters (multi-city)
- Both the sort/filter menu and the filter bottom sheet dialog

The feature is gated behind a Firebase Remote Config flag (same pattern as `isPriceWatchEnabled` in `WegoUtilLib`).

## What Already Exists (branch: feature/fmeta-1812-timebox-filter)

Two commits are already on the branch:
1. **Add flight time filter section to search results** — adds the `FlightTimeFilterViewHolder` and `TYPE_FLIGHT_TIME_FILTER` constant to `FlightSearchResultsFilterAdapter`, plus layout `row_filter_flight_time.xml` and drawables
2. **Implement selection logic and state-driven styling** — wires up click listeners, `sectionLimits`, selection state + visual highlighting (selected/normal states for buttons)

**What's NOT done yet (this task):**
- Multi-selection: current code only supports single box selection (one min/max range at a time)
- New data model to hold a `List<String>` of selected boxes
- Updated `TimeFilterListener` interface to pass `List<String>` instead of `(lowest, highest)`
- Wire-up to `WegoFlightResultFilter` (currently uses `Long` min/max fields, needs new `List<String>` fields)
- Internal filter logic: `FlightListProcessingUtil` (and PL/MultiCity equivalents) must be updated to match flights against selected time boxes instead of a min/max range
- Tracking: replace `departuretime_selected` / `arrivaltime_selected` keys with `departuretime_box_selected` / `arrivaltime_box_selected`, and change value format from `{leg: [min, max]}` to `{leg: ["0000-0600", "1800-2400"]}`
- `GenzoFlightSearchResultHelper` updated to build new tracking values
- Feature flag: new Remote Config key in `ConstantsLib.FirebaseRemoteConfigKeys` + helper method in `WegoUtilLib`
- Round trip and per-leg filter paths wired to use the new component

## Time Box Definitions

| Box | Label | Minute Range (for internal filtering) |
|-----|-------|---------------------------------------|
| "0000-0600" | Midnight – 6am | 0–359 |
| "0600-1200" | 6am – Noon | 360–719 |
| "1200-1800" | Noon – 6pm | 720–1079 |
| "1800-2400" | 6pm – Midnight | 1080–1439 |

## Data Model Change

**Old:** `WegoFlightResultFilter` uses `Long filterTakeoffDepartTimeFrom/To` (single range)
**New:** Add `List<String> selectedDepartTimeBoxes` (and equivalent for arrival, return leg)

A flight passes the filter if its departure/arrival time (in minutes from midnight) falls within **any** of the selected boxes. If no boxes are selected → no filter applied (show all).

## Tracking Change

The existing tracking fires in `FlightSearchResultsPresenter` when the sort/filter event is logged. No new event is created — only the key and value format change:

| | Old | New |
|--|-----|-----|
| Key | `departuretime_selected` | `departuretime_box_selected` |
| Key | `arrivaltime_selected` | `arrivaltime_box_selected` |
| Value | `{"1": [360, 719]}` | `{"1": ["0600-1200"]}` |
| Value (multi) | `{"1": [0, 719]}` (was single range) | `{"1": ["0000-0600", "0600-1200"]}` |

`GenzoFlightSearchResultHelper.getSelectedDepartureTime()` and `getSelectedArrivalTime()` must be updated to read from the new `List<String>` fields instead of `Long` min/max fields.

## Feature Flag

- Add new key to `ConstantsLib.FirebaseRemoteConfigKeys`: `a_fmeta1812_timebox_filter_variant`
- Add `WegoUtilLib.isTimeboxFilterEnabled()` — returns `true` when value equals `"v2"`, same pattern as `isPriceWatchEnabled()`
- When flag is `v1` (default / OFF): show existing slider/range filter (no change)
- When flag is `v2` (ON): show new timebox component

## Scope of Files

| File | Change |
|------|--------|
| `FlightSearchResultsFilterAdapter.java` | Multi-select logic, updated `TimeFilterListener` interface |
| `WegoFlightResultFilter.java` | Add `List<String>` fields for selected time boxes |
| `FlightListProcessingUtil.java` | Update time filter logic to match against selected boxes |
| `FlightFilterNewMenu.java` | Wire timebox filter items with feature flag gate |
| `GenzoFlightSearchResultHelper.kt` | New tracking methods for `_box_selected` keys |
| `FlightSearchResultsPresenter.java` | Use new tracking keys; pass multi-selection to filter |
| `ConstantsLib.java` | Add Remote Config key for feature flag |
| `WegoUtilLib.java` | Add `isTimeboxFilterEnabled()` |
| `PLFlightFilterMenu.kt`, `PLListProcessingUtil.kt` | Per-leg filter support |
| `MulticityFlightFilterMenu.java`, `MultiCityListProcessingUtil.java` | Multi-city filter support |
| Existing tests in `flights/` | Update for new filter model |

## Acceptance Criteria

- [ ] Timebox filter UI shows 4 selectable buttons per filter row (depart/arrival)
- [ ] Multiple boxes can be selected or deselected independently
- [ ] Selecting a box filters flights to those with departure/arrival time in that range
- [ ] Selecting multiple boxes shows flights in any of the selected ranges
- [ ] Deselecting all boxes removes the filter (shows all)
- [ ] Works for one-way, round trip (outbound + inbound legs), and per-leg
- [ ] Feature is hidden behind Remote Config flag; old behavior unchanged when flag is off
- [ ] Tracking fires `departuretime_box_selected` / `arrivaltime_box_selected` with correct array value

## Applicable Rules

- `coding-conventions.md` — Java + Kotlin conventions, Timber logging
- `critical-thinking.md` — Filter logic change has broad impact; verify against all trip types
