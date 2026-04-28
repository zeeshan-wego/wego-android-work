# Banner Position Bug — Flight Search Results

**Ticket:** FMETA-2596

## Problem

`FlightSearchResultsAdapter.updateRecyclerView()` inserts banners in the wrong order and the set price alert card ignores the banner count when calculating its insertion position. Three distinct bugs in one method:

1. **Wrong insertion order** — personalization banner is inserted first (position 0), then disclaimer, then hajj. Expected: disclaimer → advisory → hajj → personalization (personalization always last among banners)
2. **Missing `topIndex++` after hajj insertion** — if both advisory and hajj are present, the counter is stale, though this is incidentally harmless in the current insertion order
3. **Price alert position ignores banner count** — `Math.max(0, defaultPriceAlertItemPosition)` is used as an absolute list index, so when banners are present the price alert lands in the middle of the banner area instead of within the flight results section

## Current vs Expected Behaviour

| Banners present | Current order | Expected order |
|----------------|--------------|----------------|
| Disclaimer + Hajj | personalization → disclaimer → hajj → price_alert(pos N) → flights | disclaimer → hajj → personalization → flights → price_alert(pos N from flights) |
| Disclaimer only | personalization → disclaimer → price_alert(pos N) → flights | disclaimer → personalization → flights → price_alert |
| Hajj only | personalization → hajj → price_alert(pos N) → flights | hajj → personalization → flights → price_alert |
| Neither | personalization → price_alert(pos N) → flights | personalization → flights → price_alert(pos N) |

## Architecture Understood

- `FlightSearchResultsAdapter.java` (Java) handles **one-way + round-trip**
- `PLFlightSearchResultsAdapter.kt` (Kotlin) handles **per-leg**
- For per-leg: disclaimer/hajj are Fragment-level Views in `fragment_per_leg_flight_search_result.xml` (included as `pl_message_box` and `pl_hajj_message_box`), positioned above the ViewPager — they naturally appear above all RecyclerView content. No fix needed.
- `defaultPriceAlertItemPosition` = `WegoUtilLib.getPriceAlertItemPosition()` = Firebase Remote Config value `PRICE_ALERTS_CARD_INDEX` (≈ 2 in tests)
- `collapsedIndexSet` is recalculated AFTER all insertions (lines 388–402) so it always reflects final positions — no ordering constraint imposed by collapsed groups

## Key Items

| Item | File | Note |
|------|------|------|
| `updateRecyclerView()` | `flights/.../FlightSearchResultsAdapter.java` | Only method to change |
| `defaultPriceAlertItemPosition` | Same file, line 107 | Firebase Remote Config `PRICE_ALERTS_CARD_INDEX` |
| `TYPE_PERSONALIZATION_BANNER = 11` | `JacksonFlightTrip.java` | |
| `TYPE_DISCLAIMER = 7` | `JacksonFlightTrip.java` | |
| `TYPE_HAJJ_SEASON_WARNING = 9` | `JacksonFlightTrip.java` | |
| `TYPE_SET_PRICE_ALERT = 10` | `JacksonFlightTrip.java` | |
| `showHajjDisclaimerIfNecessary()` | `PLFlightSearchResultFragment.kt:588` | Per-leg hajj (Fragment-level) |
| `addDisclaimerMessage()` | `PLFlightSearchResultFragment.kt:408` | Per-leg disclaimer (Fragment-level) |

## What Does NOT Change

- All ViewHolder creation logic — only insertion order changes
- Per-leg adapter (`PLFlightSearchResultsAdapter.kt`) — confirmed no fix needed
- `findSetPriceAlertPosition()` — searches by type, still correct after position change
- `collapsedIndexSet` recalculation — runs after all insertions, unaffected
- Multi-city adapter — out of scope

## Edge Cases Verified

- **No banners:** `topIndex = 0` → price alert at `0 + defaultPriceAlertItemPosition` = same as before ✓
- **No flights (`filteredTrips` empty):** personalization guard changes from `!displayedTrips.isEmpty()` → `!filteredTrips.isEmpty()` to avoid showing banner when only banners are in the list ✓
- **Grouped/collapsed prices (`TYPE_GROUP` in list):** `collapsedIndexSet` recalculated after insertions; `VIEW_SHOW_MORE_BUTTON` is virtual (not in `displayedTrips`) ✓
