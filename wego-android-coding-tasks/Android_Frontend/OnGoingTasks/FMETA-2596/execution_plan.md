# Execution Plan: Fix Banner Ordering & Price Alert Position

**Ticket:** FMETA-2596
**Branch:** `fix/fmeta-2596-banner-position`

## Summary

Fix the banner insertion order and price alert position offset in `FlightSearchResultsAdapter.updateRecyclerView()`. One method, one file changed.

## Change

**File:** `flights/src/main/java/com/wego/android/features/flightsearchresults/FlightSearchResultsAdapter.java`
**Method:** `updateRecyclerView()` — lines ~326–356

Replace the entire banner + price alert insertion block:

### Before
```java
int topIndex = 0;
if (showPersonalizationBanner && !displayedTrips.isEmpty()) {
    JacksonFlightTrip bannerItem = new JacksonFlightTrip(
            JacksonFlightTrip.TYPE_PERSONALIZATION_BANNER);
    displayedTrips.add(topIndex, bannerItem);
    topIndex++;
}
if (disclaimerItem != null) {
    displayedTrips.add(topIndex, disclaimerItem);
    topIndex++;
}
if (!filteredTrips.isEmpty() && advisoryItem != null) {
    displayedTrips.add(topIndex, advisoryItem);
    topIndex++;
}
if (isHajjSeasonActive) {
    JacksonFlightTrip item = new JacksonFlightTrip(JacksonFlightTrip.TYPE_HAJJ_SEASON_WARNING);
    displayedTrips.add(topIndex, item);
    // topIndex NOT incremented (bug)
}

// Add Set Price Alert item - only if there's at least one flight and at most in 3rd position
if (!filteredTrips.isEmpty() && setPriceAlertClickListener != null) {
    if (setPriceAlertItem == null) {
        setPriceAlertItem = new JacksonFlightTrip(JacksonFlightTrip.TYPE_SET_PRICE_ALERT);
    }
    int insertPosition = Math.max(0, defaultPriceAlertItemPosition);
    // Make sure we don't insert beyond the list size
    insertPosition = Math.min(insertPosition, displayedTrips.size());
    displayedTrips.add(insertPosition, setPriceAlertItem);
}
```

### After
```java
int topIndex = 0;
if (disclaimerItem != null) {
    displayedTrips.add(topIndex, disclaimerItem);
    topIndex++;
}
if (!filteredTrips.isEmpty() && advisoryItem != null) {
    displayedTrips.add(topIndex, advisoryItem);
    topIndex++;
}
if (isHajjSeasonActive) {
    JacksonFlightTrip item = new JacksonFlightTrip(JacksonFlightTrip.TYPE_HAJJ_SEASON_WARNING);
    displayedTrips.add(topIndex, item);
    topIndex++;
}
if (showPersonalizationBanner && !filteredTrips.isEmpty()) {
    JacksonFlightTrip bannerItem = new JacksonFlightTrip(
            JacksonFlightTrip.TYPE_PERSONALIZATION_BANNER);
    displayedTrips.add(topIndex, bannerItem);
    topIndex++;
}

// Add Set Price Alert item after banners, at defaultPriceAlertItemPosition within flight results
if (!filteredTrips.isEmpty() && setPriceAlertClickListener != null) {
    if (setPriceAlertItem == null) {
        setPriceAlertItem = new JacksonFlightTrip(JacksonFlightTrip.TYPE_SET_PRICE_ALERT);
    }
    int insertPosition = topIndex + Math.max(0, defaultPriceAlertItemPosition);
    // Make sure we don't insert beyond the list size
    insertPosition = Math.min(insertPosition, displayedTrips.size());
    displayedTrips.add(insertPosition, setPriceAlertItem);
}
```

## Files Changed

| File | Change |
|------|--------|
| `flights/src/main/java/com/wego/android/features/flightsearchresults/FlightSearchResultsAdapter.java` | Reorder banner insertion, fix `topIndex++` after hajj, offset price alert by `topIndex` |

## Files NOT Changed

| File | Reason |
|------|--------|
| `PLFlightSearchResultsAdapter.kt` | Per-leg: no fix needed |
| `PLFlightSearchResultFragment.kt` | Per-leg: disclaimer/hajj Fragment views, correct order already |
| `MultiCityFlightSearchResultsAdapter.java` | Out of scope |
| All ViewHolder classes | Only insertion order changes |
| `JacksonFlightTrip.java` | No type constant changes |

## Flow to Record After Implementation

Record `flight-banner-stack` flow in `~/.claude/flows/`: `updateRecyclerView()` banner insertion order, `topIndex` tracking, price alert offset logic.

## Test Plan

| Scenario | Expected result |
|----------|----------------|
| One-way, disclaimer + hajj present | `[disclaimer, hajj, personalization, ...flights..., price_alert]` |
| One-way, disclaimer only | `[disclaimer, personalization, ...flights..., price_alert]` |
| One-way, hajj only | `[hajj, personalization, ...flights..., price_alert]` |
| One-way, no banners | `[personalization, ...flights..., price_alert]` (same as before) |
| Round-trip, any banners | Same ordering as one-way (same adapter) |
| Price alert position | Not in banner area — at `defaultPriceAlertItemPosition`-th flight result |

## Acceptance Criteria

- [ ] Personalization banner appears below all warning banners (disclaimer, advisory, hajj)
- [ ] Set price alert card position does not overlap with banner area
- [ ] No regression: when no banners are present, positions unchanged
- [ ] No regression: collapsed/grouped price cards unaffected
- [ ] Detekt passes (no new violations)
- [ ] Build passes: `:flights:assemblePlaystoreDebug`
