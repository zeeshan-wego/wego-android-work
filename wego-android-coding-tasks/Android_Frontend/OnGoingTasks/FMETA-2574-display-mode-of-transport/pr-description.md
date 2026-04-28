# [FMETA-2574] Display Mode of Transport

**Related Ticket:** FMETA-2574

## Context

The Flights API now returns `transportType` (FLIGHT/TRAIN/BUS) on flight segments and `stationType` (airport/train_station/bus_station) on airport/station objects. This PR implements display of transport mode across three UI surfaces: location autocomplete, search result cards, and flight detail pages. See https://wegomushi.atlassian.net/browse/FMETA-2574 for full requirements.

## Approach

**Interface-first:** Added `getTransportType()` to `FlightSegment` interface and `transportType` field to `JacksonFlightSegment` to ensure all segment implementations are compatible. Similarly, `stationType` is handled in the Jackson deserialization layer.

**Backward-compatible:** New fields default to null. All-flight journeys (the existing case) behave identically to before — no changes to aircraft type display logic.

**Extracted helpers:** Created `hasMixedTransport()` to efficiently determine if a leg contains non-flight segments (checks distinct transport type count > 1). Created `getSegmentTransportInfo()` to centralize icon and label lookup, reducing duplication.

**Localization:** Transport type labels ("Train", "Bus") use string resources rather than hardcoded values, supporting multi-language deployment.

## Changes

**Data Models:**
- `ConstantsLib.java`: Added `TransportType` interface (FLIGHT, TRAIN, BUS) and `STATION_TYPE_*` constants
- `FlightSegment.java` (interface): Added `@Nullable String getTransportType()`
- `JacksonFlightSegment.java`: Added `transportType` field, getter, and copy-constructor assignment
- `JacksonFlightSegmentTest.kt` (new): Deserialization tests for `transportType` field

**Localization:**
- `strings.xml`: Added `lbl_transport_train`, `lbl_transport_bus`, and related service labels

**Location Autocomplete:**
- `FlightSearchLocationAdapter.java`: Updated icon logic to check `stationType` for train/bus stations
- `FlightChooseLocationStickyListAdapter.java`: Same icon logic applied to sticky list variant

**Flight Detail Display:**
- `FlightDetailsUiUtils.kt`: Added `hasMixedTransport()` helper; added `getSegmentTransportInfo()` to return Pair<iconResId, label>; modified `addAdditionalStops()` to display transport labels for non-flight segments
- `FlightDetailsUiUtilsTest.kt`: Updated and added test cases for `hasMixedTransport()` with mixed transport scenarios
- `FlightDetailsFragment.java` / `FlightItineraryFragment.java`: Already calling `updateDetailTransportIcons()` (no changes needed)

**Search Result Cards:**
- `PLFlightSearchResultsAdapter.kt`: Added `setupTransportTypeView()` extension method to populate transport type badge (icon + label) on search result card views
- `row_flight_search_result.xml` and variants: Added `transport_type_view` component to display badge
- `row_flight_search_result_pl.xml` and variants: Added `transport_type_view` component

**Icons:**
- `ic_train.xml` (new): Train transport icon
- `ic_bus.xml` (new): Bus transport icon

## Testing

**Unit Tests:**
- `JacksonFlightSegmentTest.kt`: Validates deserialization of `transportType` (FLIGHT, TRAIN, absent)
- `FlightDetailsUiUtilsTest.kt`: Tests `hasMixedTransport()` across pure-flight, mixed, and pure-train/bus scenarios

**Manual Testing (Staging):**
- Test routes with mixed transport: DMX–JXD, JXD–DMX, MKX–DMX, DMX–MKX on sa-beta.wegostaging.com
- Verify autocomplete icons: train icon for train stations, bus icon for bus stations
- Verify search card badges: correct transport label and operator logos shown
- Verify flight detail: transport labels and icons render correctly per segment type

**Coverage:** All new logic paths tested; backward compatibility verified on all-flight trips.

## Checklist

- [x] Tests added (deserialization, mixed transport detection)
- [x] All unit tests pass (flights module)
- [x] Detekt static analysis passes (max line length, method complexity)
- [x] No breaking changes (new fields are nullable, default behavior unchanged)
- [x] Follows Wego Design System (uses existing icon/label patterns)
- [x] Follows coding conventions (Timber for logging, Kotlin/Java style)
- [x] Localization strings added for transport labels
