# FMETA-2596

**Jira Ticket:** https://wegomushi.atlassian.net/browse/FMETA-2596

## Description

Fix the following bugs:

On flight search result page, the position of the personalization banner and set price alert card is not correct when a disclaimer and hajj warning is present.

On a one-way search, currently the order is:
**personalization banner → disclaimer → price alert card**

Expected: personalization banner below the last banner
- If hajj warning present: **disclaimer → hajj → personalization**
- If only one exists: **disclaimer → personalization** or **hajj → personalization**

For set price alert card: should exclude all three banners (disclaimer, hajj, personalization) from its position calculation.

For per-leg: observe current banner placement logic and report back before fixing.

Record any new flows found while doing this.

## Scope

- One-way and round-trip flight search results (both use `FlightSearchResultsAdapter.java`)
- Per-leg: investigated — no fix needed (disclaimer/hajj are Fragment-level views above ViewPager, already in correct order)
- Multi-city: out of scope for this ticket
