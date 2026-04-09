# [Android] Show Categorized Hotel Amenities in HDP

**Jira Ticket:** https://wegomushi.atlassian.net/browse/HMETA-1894
**Type:** Task
**Priority:** Standard
**Status:** In Progress
**Assignee:** Waqar Afzal

## Background

Currently, hotel amenities on the HDP are displayed as an ungrouped, dense list with no cost clarity. This causes user confusion and slower decision-making. As part of the Curated & Categorized Amenities initiative, the static data team is updating the amenities schema with categorization and curated detail. This ticket covers the Android frontend implementation.

## What needs to be done

As a hotel shopper on Android, I want to see hotel amenities grouped into clear categories with cost/availability context so that I can evaluate a property's offering efficiently and make faster booking decisions.

## Why it needs to be done

The current amenity display is scattered and unstructured, causing user confusion and increasing time-to-decision. Competitors (Booking.com, Agoda, Expedia) already display categorized, icon-led amenities.

## Acceptance Criteria

* Given a hotel has more than the visible threshold of amenities (currently set at 6), when a user taps "See more", then show a bottom sheet with:
    * The full list of hotel amenities displayed grouped under their respective category headers (e.g., Connectivity, Activities & Entertainment, Wellness & Fitness, Food & Drinks, Parking, etc.)
    * Cost type label, if available (e.g., "Free", "Additional Charge") using the badge/tag design from Figma
        * If a hotel has more than one cost type for the same amenities, only show one and prioritize as follows:
            * Additional Charge
            * Free
        * If cost type is null for the amenities, then show no labels at all
    * Search bar to search for amenities using a specific keyword
        * When user is searching for amenities:
            * Highlight the affected keywords
            * Track the event:
                ```json
                {
                    "event": {
                        "id": "{pageview_id}",
                        "category": "hotel_amenities",
                        "object": "search_phrase",
                        "action": "clicked",
                        "value": "[keyword]"
                    },
                    "created_at": "2025-04-09T17:02:35+05:30"
                }
                ```
* Given a hotel has no amenities in a particular category, when the user views the amenities section, then that category is not displayed
* Given the amenities section is loaded, when the page renders, then page load time does not increase by more than 1 second compared to baseline

## References

* PRD: https://docs.google.com/document/d/1ZFPlDL7WbN-phxOAwHXSG36n3mwiWizYky7ZZXyL1ZI/edit?tab=t.qj99yvsbwoqr
* mWeb Figma: https://www.figma.com/design/cjOujU9gNCr0O3x1VRub3k/-Android--Hotels?node-id=13242-3527&p=f&t=ZWbo2MnE6THbalyH-11
* Hotel Amenities Mapping sheet: https://docs.google.com/spreadsheets/d/1fqOpR5kF8OSWmwMJSvZSvQWj4QNEs-KcOtjgeuqKFgU/edit?gid=834694322#gid=834694322

---
*Fetched from Jira on 2026-04-09*
