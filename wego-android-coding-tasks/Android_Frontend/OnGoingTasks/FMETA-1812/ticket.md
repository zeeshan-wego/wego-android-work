# FMETA-1812: Flight Time Timebox Filter

## Summary

Replaced the flight time filter's continuous range slider with a 4-button timebox selector. Users can now pick one or more time blocks (Midnight–6am, 6am–Noon, Noon–6pm, 6pm–Midnight) for departure and arrival times, rather than dragging a min/max range.

## What Changed

- **New timebox UI** — 4 selectable time-block buttons replace the range slider for departure and arrival time filters
- **Multi-select** — multiple time blocks can be selected simultaneously; results show flights matching any selected block
- **Round-trip tab switcher** — a Departure / Return tab above the timebox rows lets users switch between outbound and inbound leg filters without stacking two full filter sections
- **Per-leg search support** — timebox selections made on leg 1 are automatically carried forward to subsequent legs
- **Clear button** — tapping Clear on the time filter chip correctly resets all timebox selections
- **Filter chip highlight** — the time filter chip in the results toolbar activates when any timebox is selected
- **Feature flag** — the feature is gated by Firebase Remote Config (`a_fmeta1812_timebox_filter_variant`). When the flag is `v2`, the new timebox UI is shown; when `v1` (default), the old slider is shown
- **Analytics** — tracking keys updated from `departuretime_selected` / `arrivaltime_selected` to `departuretime_box_selected` / `arrivaltime_box_selected`, with values now reflecting the selected box IDs (e.g. `["0600-1200", "1200-1800"]`)

## Scope

Applies to one-way, round-trip, and per-leg (step-by-step) flight search results. Also applies to the multi-city flow.

## Acceptance Criteria

- [x] Timebox filter UI shows 4 selectable buttons per filter row (depart/arrival)
- [x] Multiple boxes can be selected or deselected independently
- [x] Selecting a box filters flights to those with departure/arrival time in that range
- [x] Selecting multiple boxes shows flights in any of the selected ranges
- [x] Deselecting all boxes removes the filter (shows all)
- [x] Works for one-way, round trip (outbound + inbound legs), and per-leg
- [x] Feature is hidden behind Remote Config flag; old behavior unchanged when flag is off
- [x] Tracking fires `departuretime_box_selected` / `arrivaltime_box_selected` with correct array value
