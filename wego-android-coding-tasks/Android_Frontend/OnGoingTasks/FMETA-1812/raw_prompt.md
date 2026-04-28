# FMETA-1812

**Jira Ticket:** https://wegomushi.atlassian.net/browse/FMETA-1812

## Description

As a user, I want to filter flight times using 4 boxes corresponding to 4 sections of a day, so that I can filter flights by time quickly.


### Tracking
When a user filters, we still fire an event action in the existing format. The changes to the tracking are: 

| Change | Old | New |
| -------- | -------- | -------- |
| The key inside the event.value will change | departuretime_selected, arrivaltime_selected  | departuretime_box_selected, arrivaltime_box_selected |
| Instead of pointing to an array of minimum and maximum minutes, we now point to an array of strings | [X,Y] where X= minimum minutes and Y = maximum minutes |It will now be an array of possible time boxes (Strings) that user has selected. The possible string values are: "0000 - 0600", "0600 - 1200", "1200 - 1800", "1800 - 2400". User can select multiple timeboxes, so the array can have multiple of these values. Example array: ["0000-0600", "1800-2400"] |

### Design
Flight times filter in search results page sort & filter menu: [sort_filter_menu.png]](./sort_filter_menu.png)
Flight times flter in filter bottom sheet dialog: [filter_bottom_sheet.png]](./filter_bottom_sheet.png)

## Acceptance Criteria

- New flight filter type exists as per design
- Current depart and arrival filter changed with the new filter type
- Tracking updated as per requirement
- User can select multiple time boxes
- One-way and round trip flight search results can be filtered using new filter type
- Feature is gated with a filter flag

## Additional Details
- I have setup a feature/fmeta-1812-timebox-filter for this and have commited some initial codes for it. This code already has the new filter componet and attached it, look into FlightSearchResultsFilterAdapter.TYPE_FLIGHT_TIME_FILTER to understand the component and what needs to be added/changed. 
