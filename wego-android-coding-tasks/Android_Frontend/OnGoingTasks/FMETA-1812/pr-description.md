# PR: FMETA-1812 Flight Time Timebox Filter

### Context
- Replaces the min/max range slider in the flight time filter with a 4-button timebox selector (00:00–06:00, 06:00–12:00, 12:00–18:00, 18:00–24:00). Users can select multiple blocks.
- Jira: https://wegomushi.atlassian.net/browse/FMETA-1812
- Gated by Remote Config flag `a_fmeta1812_timebox_filter_variant` (v1=off, v2=on)

### Approach
- Added `timeboxDepartTakeoff`, `timeboxDepartLandingOw`, `timeboxReturnTakeoff`, `timeboxReturnLandingTw` (`List<String>`) fields to `WegoFlightResultFilter`. Filter logic in `FlightListProcessingUtil`, `PLFilterUtil`, and `MultiCityListProcessingUtil` checks if a flight's minute-of-day falls within any selected box.
- `FlightSearchResultsFilterAdapter` gained a new `TimeboxFilterMenuItem`/`TimeboxFilterViewHolder` and a `TabSwitcherFilterMenuItem`/`TabSwitcherViewHolder` (RadioGroup-style departure/return tab) for round-trip searches.
- `FlightFilterNewMenu` and `PLFlightFilterMenu` wire the timebox items behind `isTimeboxFilterEnabled()` and handle Clear correctly.
- `copyNecessaryFiltersToNextLegs()` in `PLFlightSearchResultViewModel` extended to include all 4 timebox lists so selections propagate across legs.
- Analytics: `GenzoFlightSearchResultHelper` / `GenzoPLFlightSearchResultHelper` / `GenzoMultiCityFlightSearchResultHelper` updated to emit `departuretime_box_selected` / `arrivaltime_box_selected` keys with `List<String>` values.

### Testing
- Built and installed debug APK on emulator; navigated to flight search results with Remote Config flag set to v2
- Verified timebox buttons render and multi-select works
- Verified Clear button resets selections and chip un-highlights
- Verified per-leg search carries timebox selections from leg 1 to leg 2

### Checklist
- [x] I have commented on hard-to-understand areas or given context in the PR
- [ ] Unit tests cover the changes
- [x] Code follows the project's style guidelines
- [x] Tested according to acceptance criteria
    - [x] Local
    - [ ] Staging
- [x] Dependent changes have been merged
- [ ] Documentation updated if needed

---
Generated with [Claude Code](https://claude.ai/code) by Anthropic

Co-Authored-By: Claude <noreply@anthropic.com>
