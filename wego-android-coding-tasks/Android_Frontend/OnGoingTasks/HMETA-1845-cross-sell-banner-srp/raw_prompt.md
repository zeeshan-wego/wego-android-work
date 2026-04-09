# [Android] Cross-sell Banner in SRP

**Jira Ticket:** https://wegomushi.atlassian.net/browse/HMETA-1845
**Type:** Task
**Priority:** Standard

## Background

Users who land on hotel search results via cross-sell flows (e.g., after completing a flight booking) are eligible for special priced rates. However, there is currently no strong visual reinforcement on the results page to communicate that these rates are exclusive or tied to their recent flight booking.

We want to introduce a banner at the top of the hotel search results page (occupying the same placement as the current login banner) to clearly communicate that the user is seeing special cross-sell pricing.

### What needs to be done

As a user arriving on the hotel results page from a cross-sell flow,
I want to see a clear banner indicating that I am receiving special cross-sell rates,
so that I feel confident I am getting an exclusive deal and am more likely to book.

### Why it needs to be done

Cross-sell users have high booking intent, but the value proposition is not clearly reinforced once they land on the results page. Without strong contextual messaging, the experience feels like a normal search.

By introducing a prominent banner:
- We reinforce the perception of exclusivity
- We increase user confidence in pricing
- We improve clickthrough and downstream conversion
- We strengthen the flight-to-hotel attach rate

## Acceptance Criteria

- **Given** a user lands on the hotel search results page
  **When** the search context is identified as a **cross-sell search**
  **Then** the cross-sell banner is displayed at the top of the page

- **Given** a user lands on the hotel search results page
  **When** the search context is **not** cross-sell
  **And** the user is **not logged in**
  **Then** the existing login banner is displayed

- **Given** a user lands on the hotel search results page
  **When** the search context is **cross-sell**
  **Then** the cross-sell banner takes priority over the login banner (login banner is not shown)

- **Given** a user lands on the hotel search results page
  **When** the search context is **not cross-sell**
  **And** the user is **logged in**
  **Then** no banner is shown (unless triggered by other existing logic)

- **Given** the cross-sell banner is shown
  **When** rendered
  **Then** it occupies the same layout position and space as the current login banner

## References

- Figma: https://www.figma.com/design/BcFNJ0KS9X0J8V6ntu4AP3/-Flights--Hotels-Cross-Sell-Product-Placements?node-id=52-27232&t=RqHbnyQC4sVAX4Wv-4

---
*Fetched from Jira on 2026-03-31*
