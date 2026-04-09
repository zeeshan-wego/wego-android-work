# HMETA-1551: Add Social Proof Tags on Hotel Search Results (Android)

**Jira:** https://wegomushi.atlassian.net/browse/HMETA-1551
**iOS Reference:** https://github.com/wego/wego-ios-swift/pull/2170 (HMETA-1553)

## What

Display social proof tags ("Selling fast!", "Only X rooms left", "Loved by X") on hotel search result cards in the SRP. This is the Android counterpart of the iOS HMETA-1553 implementation.

## API Contract

The API returns social proof at **two levels**:

### Hotel Level
Field `hotelSocialProof` on `JacksonHotel`:
```json
{
  "hotelSocialProof": {
    "priority": 1,
    "type": "BOOKING_STATS",
    "value": 44
  }
}
```

### Rate Level
Field `rateSocialProof` on `JacksonHotelRate`:
```json
{
  "rateSocialProof": {
    "priority": 2,
    "type": "ROOM_SCARCITY",
    "value": 3
  }
}
```

### Social Proof Types

| Type | Display Text | Icon | Color |
|------|-------------|------|-------|
| `BOOKING_STATS` | "Selling fast!" (`selling_fast` key) | fire | Destructive (red) |
| `ROOM_SCARCITY` | "Only X rooms left" (`lbl_social_proof_room_scarcity` plural) | clock | Destructive (red) |
| `TRAVELLER_POPULARITY` | "Loved by X" (`lbl_social_proof_traveller_popularity`) | people | Primary (blue) |

## Priority Resolution

When both hotel-level and rate-level social proof exist:
1. Lowest `priority` value wins (lower = higher priority)
2. If equal, hotel-level wins
3. If only one exists, use that one
4. Fallback order: rate ?? hotel (rate preferred when only one exists)

## A/B Test Gate

Gated behind: `a_hmeta1553_hotel_results_show_social_proof_tags_fixed`
(Android uses `a_` prefix; iOS uses `i_` prefix)

## UI Placement

- Social proof appears on hotel result cards, in the details section
- Shows icon + text label (semibold, 12sp)
- Hidden when A/B flag is off or no social proof data exists
- Independent from existing tag display (sold out, sponsored, deal tags remain unchanged)

## Scope

- Parse social proof from API at both hotel and rate levels
- Create `JacksonHotelSocialProof` model in `libbase`
- Add social proof field to `JacksonHotel` and `JacksonHotelRate`
- Carry social proof through to `JacksonHotelResult`
- Resolve priority in adapter (hotel vs rate)
- Display in `HotelResultItemViewHolderV2` with icon + text
- Add layout elements to `row_hotel_search_full_result.xml`
- Gate behind A/B test config flag
- Unit tests for model, priority resolution, and display logic

## Out of Scope

- Hotel details page social proof (separate ticket)
- Similar hotels social proof (pass nil, same as iOS)
- Map view social proof

## Applicable Rules

- `coding-conventions.md` - Kotlin naming, formatting, max line 120 chars
- `project-structure.md` - Model in libbase, UI in hotelsv2
- `critical-thinking.md` - Verify API field names match actual response
