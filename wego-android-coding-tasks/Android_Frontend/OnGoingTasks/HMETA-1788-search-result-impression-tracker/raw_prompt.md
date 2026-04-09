# [Android] Update Tracker for Search Result Impression

**Jira Ticket:** https://wegomushi.atlassian.net/browse/HMETA-1788
**Type:** Task
**Priority:** Standard
**Project:** Hotels Metasearch (HMETA)

## Background

In evaluating our hotel sort order logic, we came across a lack of data visibility that would enable us to analyze the result more comprehensively. This includes search result impression information when new result is being shown on the SRP. To have more complete information on user's behavior and interaction, we want to implement a new event tracker for search result impression.

## Acceptance Criteria

Given user is searching for hotels
When a sort/filter/scroll/poll action is triggered to load new results
Then track the activity including information of hotel list that is being shown

```
  id =
  created_at = (created_at of the impression)
  page_view_id = (for search results page)
  search_id = (for search)
  page = "search_results"
  trigger = "sort" / "filter"/ "scrolling" / "polling"
  sort_order_type = "cheapest" / "recommended" etc
  event_id = id of the event action for filter/sort
  list: [
  {
  object_id = "hotel_id"
  object_type = "hotel"
  sort_order_position = 1/2/3/4/5/6 etc
  rate_id = "1224" rate_id passed from back end
  final_price_usd = "$120" final price after discount
  initial_price_usd = "$140" price before discount
  strikethrough_offer = boolean
  promocode_offer = promocode / null
  rate_tags = "Wego best seller" / "hot deal"
  social_proof = "booked 10 today" / "last few rooms"
  }
  ,...]
```

## Notes

- `isa` is not active, we can deprio for now
- Implement a debounce, so after some delay of no activity then we send the event based on the action at that time
- Check if we need to remove the last one immediately or there needs to be a transition period in case the data is being used in live dashboards

---
*Fetched from Jira on 2026-03-30*
