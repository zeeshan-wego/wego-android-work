# [FMETA-2574] Display Mode of Transport

**Jira:** https://wegomushi.atlassian.net/browse/FMETA-2574

## Problem

The Wego Android app did not differentiate between different transport types (flight, train, bus) when displaying search results and itinerary details. Users couldn't quickly identify whether a journey involved trains, buses, or flights until they opened the booking page. The API now provides `transportType` on segments (FLIGHT/TRAIN/BUS) and `stationType` on airports/stations, enabling the frontend to display this information upfront.

## Solution

Transport mode is now displayed across three user surfaces:

1. **Location Autocomplete (Search Form):** Station type icon shown next to location name:
   - Train station → train icon
   - Bus station → bus icon
   - Airport → flight icon (unchanged)

2. **Search Result Card:** Transport type badge displayed when at least one segment is non-flight:
   - Pure flight trip: no badge
   - Pure train trip: "Train Service" label
   - Pure bus trip: "Bus Service" label
   - Mixed itinerary: shows both operator logos side-by-side (e.g., flight + train)

3. **Flight Detail Pages:** Transport mode shown per segment:
   - Flight segments: aircraft type as before
   - Train/bus segments: localized "Train" / "Bus" label instead of aircraft type
   - Stops row: transport icon replaces duration icon for non-flight segments

## Benefits

- **Improved transparency:** Users see transport type at a glance without opening detail pages
- **Better decision-making:** Clear visibility of mixed-mode journeys (e.g., connecting via train)
- **Consistent UX:** Station types are now properly identified in location search
- **Expanded market reach:** Enables new train/bus product lines while maintaining flight experience

## Acceptance Criteria

- [x] Autocomplete displays train icon for train stations, bus icon for bus stations
- [x] Autocomplete displays flight icon for airports (unchanged behavior)
- [x] Search result card shows transport type badge for non-flight journeys
- [x] Search result card shows both operator logos for mixed itineraries
- [x] Flight detail displays "Train"/"Bus" label for non-flight segments
- [x] Flight detail displays aircraft type unchanged for all-flight trips
- [x] Stops row displays transport icon for non-flight segments
- [x] All unit tests pass (model deserialization + UI logic)
- [x] No breaking changes to existing flight-only journeys
