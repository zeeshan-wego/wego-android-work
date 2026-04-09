# [Android] Update Event Tracker for Hotel Card Click

**Jira Ticket:** https://wegomushi.atlassian.net/browse/HMETA-1787
**Type:** Task
**Project:** Hotels Metasearch (HMETA)

## Background

In evaluating our hotel sort order logic, we came across a lack of data visibility that would enable us to analyze the result more comprehensively. This includes hotel card click on SRP including data related to the hotel being clicked. To have more complete information on user's behavior and interaction, we want to implement a new event tracker for hotel card click.

## Acceptance Criteria

### 1. List View - Hotel Card Click

Given user is searching for hotels
When user clicks on the hotel card from list view
Then track the activity including information of hotel that is displayed in SRP

```
id =
event.id = "pages_views.id" (id of the pageview event)
event.category = "hotel_search_results"
event.object = "rate_card"
event.action = "selected"
event.value = json value (normalise with the impression naming: "hotel_id, hotel_price, rate_id, strikethrough_price, promocode, rate_tags, social_proof, hotel_sort_order_position")
```

### 2. Map View - Rate Icon Click

Given user is searching for hotels
When user clicks on the hotel card from map view
Then track the activity including information of hotel that is displayed in SRP

```
id =
event.id = "pages_views.id" (id of the pageview event)
event.category = "hotel_search_results"
event.object = "rate_icon"
event.action = "selected"
event.value = json value ("hotel_id, hotel_price, rate_id, strikethrough_price, promocode, rate_tags, social_proof, labels, hotel_sort_order_position")
```

### 3. Map View - Rate Card Click

```
id =
event.id = "pages_views.id" (id of the pageview event)
event.category = "hotel_search_results"
event.object = "rate_card"
event.action = "selected"
event.value = json value ("hotel_id, hotel_price, rate_id, strikethrough_price, promocode, rate_tags, social_proof, labels, hotel_sort_order_position")
```

## Notes

- To align with web, the format for social proof is `social_proof = type-value`

---
*Fetched from Jira on 2026-03-18*