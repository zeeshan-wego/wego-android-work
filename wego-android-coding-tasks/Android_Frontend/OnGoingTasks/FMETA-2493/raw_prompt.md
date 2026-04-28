# [Android] Update baggage filter event tracking to align with dWeb schema

**Jira Ticket:** https://wegomushi.atlassian.net/browse/FMETA-2493
**Type:** Task
**Priority:** Standard

## Description

The current baggage filter events on Android (implemented in FMETA-1749) use a different schema than the one standardized on dWeb (FMETA-2454). This task aligns Android to the same schema.

### Current Implementation (FMETA-1749)

| User action | event.category | event.object | event.action | event.value |
|---|---|---|---|---|
| User taps "Cabin Bag" filter | flights_detail_page | baggage_filter | cabin_bag | `selected` or `deselected` |
| User taps "Checked Bag" filter | flights_detail_page | baggage_filter | checked_bag | `selected` or `deselected` |

### Target Implementation (aligned with FMETA-2454)

| User action | event.category | event.object | event.action | event.value |
|---|---|---|---|---|
| User taps "Cabin Bag" filter | flights_detail_page | filter | applied | `{baggages: ["cabin"]}` |
| User taps "Checked Bag" filter | flights_detail_page | filter | applied | `{baggages: ["checked"]}` |

## Acceptance Criteria

- Old baggage filter events are replaced with the new schema
- Events fire correctly on the Flight Details page when baggage filters are toggled
- `event.value` correctly reflects the selected filter (`cabin` or `checked`)
- No other events are affected

---
*Fetched from Jira on 2026-04-07*
