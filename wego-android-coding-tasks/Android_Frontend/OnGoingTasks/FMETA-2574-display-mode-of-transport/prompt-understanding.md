# [FMETA-2574] Display Mode of Transport

**Jira Ticket:** https://wegomushi.atlassian.net/browse/FMETA-2574
**Assignee:** bima@wego.com

## Summary

Display the correct transport mode (flight/train/bus) across three surfaces:
1. **Autocomplete (Search Form)** — show transport type icon next to station name based on `stationType`
2. **Search Result Card** — show correct operator logo(s); for mixed itineraries show both logos
3. **Flight Detail Page** — show transport type details per segment; only show mode of transport indicator when at least 1 segment is not a flight

New API fields powering this:
- `stationType` on airport/station objects: `airport` / `train_station` / `bus_station`
- `transportType` on segment objects: `FLIGHT` / `TRAIN` / `BUS`

---

## Surface 1: Autocomplete (Search Form)

**Where:** `FlightSearchLocationAdapter.java` and `FlightChooseLocationStickyListAdapter.java`

**Current behavior:** Icon (`iv_location_type`) shows `ic_flight` for airport type, `ic_location_pin` for everything else.

**New behavior:** Use `stationType` from `JacksonPlace` (already has this field) to determine icon:
- `train_station` → `ic_train` (new drawable — user will provide)
- `bus_station` → `ic_bus` (new drawable — user will provide)
- `airport` (or null/unrecognized) → keep `ic_flight`
- non-airport type (city/region) → keep `ic_location_pin`

---

## Surface 2: Search Result Card

**Where:** `PLFlightSearchResultFragment.kt` + `row_flight_search_result_pl.xml`

**Logo fetching:** `CloudinaryImageUtilLib.getAirlineSquareImageUrlWithoutBorder(airlineCode, size)` — verified to work identically for train/bus operator codes. No changes needed to logo loading.

**Current behavior:** Primary logo shown in `log1_card`. A second logo (`log_multi_1_card`) is shown when there are multiple airlines.

**New behavior for mixed itinerary (at least 1 non-FLIGHT segment):**
- Show both the airline logo and the train/bus operator logo side by side using the existing dual-logo layout (`log1_card` + `log_multi_1_card`)

**No change for Train Direct (all segments are train):**
- Single operator logo is shown as normal via Cloudinary

---

## Surface 3: Flight Detail Page

**Where:** `FlightDetailsUiUtils.kt` → `addAdditionalStops()` function (lines 62–260)

**Current behavior:** Segment details string = `designatorCode + aircraftType + cabin`

**New behavior:**

The condition "only show mode of transport when at least 1 segment is not a FLIGHT" applies at the leg level. If any segment in the leg has `transportType != FLIGHT`:

- Show the `transportType` value (localized: "Train" / "Bus") instead of `aircraftType` for non-flight segments
- For FLIGHT segments in a mixed leg: keep showing `aircraftType` as before

If all segments are FLIGHT (or `transportType` is null/FLIGHT): no change — show `aircraftType` as before.

---

## Data Model Changes Required

### `FlightSegment` interface (`interfaces/FlightSegment.java`)
- Add: `String getTransportType()`

### `JacksonFlightSegment.java`
- Add field: `String transportType`
- Add getter: `getTransportType()`
- Add to copy constructor

### `JacksonFlightAirport.java`
- Add field: `String stationType`
- Add getter: `getStationType()`
(The `FlightAirport` interface may also need updating — verify)

Note: `JacksonPlace` and `AutoSuggestResponse` already have `stationType` — no changes needed there.

---

## New Assets Required

| Asset | Usage |
|-------|-------|
| `ic_train.xml` | Autocomplete station type icon for `train_station` |
| `ic_bus.xml` | Autocomplete station type icon for `bus_station` |

User will provide these vector drawables. Place in `flights/src/main/res/drawable/`.

---

## Testing Routes (Staging)

Test environment: `sa-beta.wegostaging.com`

Routes with non-flight segments: **DMX–JXD, JXD–DMX, MKX–DMX, DMX–MKX**

Example URL:
`https://sa-beta.wegostaging.com/en/flights/searches/jxd-dmx-2026-04-25/economy/1a:0c:0i?sort=score&order=desc&payment_methods=3%2C10%2C14%2C15%2C152%2C183%2C187%2C192`

---

## Applicable Rules

- `coding-conventions.md` — Every code change (naming, Timber logging, max line length 120)
- `project-structure.md` — Correct module placement (data models in `flights`, shared models in `libbase`)
- `critical-thinking.md` — Verify interface changes don't break other implementors
