# Execution Plan: Update Baggage Filter Event Tracking

**Ticket:** FMETA-2493
**Branch:** `feature/fmeta-2493-update-baggage-filter-tracking`

## Summary

Replace two separate baggage filter tracking methods in `FlightDetailsPresenter` with a single method that fires a unified `filter` + `applied` event with a JSON value reflecting all currently active baggage filters.

## Approach

### 1. Replace tracking methods in `FlightDetailsPresenter.java`

**Remove:**
- `trackCabinBaggageFilterEvent(boolean isActive)` (lines 1651-1659)
- `trackCheckedBaggageFilterEvent(boolean isActive)` (lines 1661-1669)

**Add:**
- `trackBaggageFilterAppliedEvent()` — no params needed, reads `cabinBaggageFilter` and `checkedBaggageFilter` fields directly

**Logic:**
```
1. Build a list of active filter names:
   - if cabinBaggageFilter == INCLUDED → add "cabin"
   - if checkedBaggageFilter == INCLUDED → add "checked"
2. Build JSON value string: {"baggages": ["cabin", "checked"]}
3. Fire event:
   - category: Genzo.EventCategory.flightsDetailPage
   - object: Genzo.EventObject.filter
   - action: Genzo.EventAction.applied
   - value: the JSON string
```

### 2. Update callers

- `toggleCabinBaggageFilter()` line 1647: replace `trackCabinBaggageFilterEvent(isActive)` → `trackBaggageFilterAppliedEvent()`
- `toggleCheckedBaggageFilter()` line 1674: replace `trackCheckedBaggageFilterEvent(isActive)` → `trackBaggageFilterAppliedEvent()`

**Important:** The new method must be called AFTER the filter state is updated (line 1646/1673) so it reads the correct current state.

## Files to Change

| File | Action | Purpose |
|------|--------|---------|
| `flights/.../flightdetails/FlightDetailsPresenter.java` | **MODIFY** | Replace two tracking methods with one unified method |

## Files NOT Changed

| File | Reason |
|------|--------|
| `FlightConstants.kt` | `EventObject.filter` and `EventAction.applied` already exist |
| `BookingOptionsAdapter.kt` | UI unchanged |
| `FlightDetailsFragment.java` | Callback wiring unchanged |
| `FlightDetailsViewModel.kt` | State management unchanged |
| `WegoAnalyticsLibv3.kt` | Analytics infrastructure unchanged |

## Test Plan

| Test | What |
|------|------|
| Manual | Toggle cabin bag → verify event fires with `{baggages: ["cabin"]}` |
| Manual | Toggle checked bag → verify event fires with `{baggages: ["checked"]}` |
| Manual | Toggle both → verify event fires with `{baggages: ["cabin", "checked"]}` |
| Manual | Deselect all → verify event fires with `{baggages: []}` |

Note: The tracking methods are private and fire analytics events via a singleton. Unit testing would require mocking `WegoAnalyticsLibv3` — check if existing presenter tests mock this. If not, manual verification via logcat is sufficient for this scope.

## Acceptance Criteria

- [ ] Old `baggage_filter` + `cabin_bag`/`checked_bag` events no longer fire
- [ ] New `filter` + `applied` event fires on every baggage filter toggle
- [ ] `event.value` is JSON with `baggages` array reflecting all active filters
- [ ] No other events are affected

## Documentation Updates

None required — internal tracking schema change only.
