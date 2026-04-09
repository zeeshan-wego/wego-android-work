# Add Social Proof Tags on Hotel Search Results Page (SRP)

**Jira Ticket:** https://wegomushi.atlassian.net/browse/HMETA-1551
**iOS Reference PR:** https://github.com/wego/wego-ios-swift/pull/2170 (HMETA-1553)
**Type:** Feature
**Priority:** Standard

## Description

Add social proof tags (e.g., "Selling fast!", "Only X rooms left", "Loved by X") on hotel search result cards in the Android app, matching the iOS implementation.

### Social Proof Types (from API)

The API returns social proof data at two levels:
1. **Hotel level** - `hotelSocialProof` field on the hotel object
2. **Rate level** - `rateSocialProof` field on the hotel rate object

Each social proof object contains:
- `priority` (Int) - lower value = higher priority
- `type` (String) - one of: `BOOKING_STATS`, `ROOM_SCARCITY`, `TRAVELLER_POPULARITY`
- `value` (Int) - the numeric value to display

### Display Logic

| Type | Display Text | Icon | Colors |
|------|-------------|------|--------|
| BOOKING_STATS | "Selling fast!" (localized key: `selling_fast`) | fire icon | Destructive (red) |
| ROOM_SCARCITY | "Only X rooms left" (localized key: `lbl_social_proof_room_scarcity` with plural) | clock icon | Destructive (red) |
| TRAVELLER_POPULARITY | "Loved by X" (localized key: `lbl_social_proof_traveller_popularity`) | people icon | Primary (blue) |

### Priority Resolution

When both hotel-level and rate-level social proof exist:
- Pick the one with the **lowest priority value** (highest priority)
- If equal priority, hotel-level social proof wins
- If only one exists, use that one
- Rate social proof is preferred in fallback (rate ?? hotel)

### A/B Test Gate

Feature is gated behind A/B test config flag: `i_hmeta1553_hotel_results_show_social_proof_tags_fixed`
(Note: iOS uses HMETA-1553 in the flag name, Android should follow the same convention for consistency)

### UI Placement

Social proof tag appears on hotel search result cards, below the amenities area, with:
- An icon (tinted with appropriate color)
- Text label (semibold, 12sp)
- Hidden when A/B flag is off or no social proof data

## Acceptance Criteria

- [ ] Parse `hotelSocialProof` from hotel API response
- [ ] Parse `rateSocialProof` from rate API response
- [ ] Implement priority resolution (lowest priority value wins)
- [ ] Display social proof on hotel result cards with correct icon, text, and colors
- [ ] Gate behind A/B test flag `i_hmeta1553_hotel_results_show_social_proof_tags_fixed`
- [ ] Support all three types: BOOKING_STATS, ROOM_SCARCITY, TRAVELLER_POPULARITY
- [ ] Existing deal tags / sold out / sponsored tags should NOT be affected
- [ ] Unit tests covering all business logic

---
*Created from iOS PR reference on 2026-03-26*
