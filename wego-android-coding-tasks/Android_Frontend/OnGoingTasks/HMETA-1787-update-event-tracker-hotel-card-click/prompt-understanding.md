# HMETA-1787: Update Event Tracker for Hotel Card Click

## Overview

Add detailed event tracking when users click hotel cards on the Search Results Page (SRP). Track clicks from both list view and map view, sending a JSON value payload with hotel data alongside the existing Genzo v3 event action system.

## Requirements

### 1. List View - Hotel Card Click
When user clicks a hotel card from the list view, fire:
- `event.category` = `"hotel_search_results"`
- `event.object` = `"rate_card"`
- `event.action` = `"selected"`
- `event.value` = JSON with: `hotel_id`, `hotel_price`, `rate_id`, `strikethrough_price`, `promocode`, `rate_tags`, `social_proof`, `hotel_sort_order_position`
- **Position is 1-based** (first item = 1)

### 2. Map View - Rate Icon Click (marker tap)
When user taps a hotel marker/pin on the map:
- `event.object` = `"rate_icon"`
- `event.action` = `"selected"`
- Same JSON fields but **without position** (position = null/omitted)

### 3. Map View - Rate Card Click (hotel card tap from map)
When user taps the hotel card shown after selecting a map marker:
- `event.object` = `"rate_card"`
- `event.action` = `"selected"`
- Same JSON fields but **without position** (position = null/omitted)

### JSON Value Fields
| Field | Source | Notes |
|-------|--------|-------|
| `hotel_id` | `HotelResult.id` | Always present |
| `hotel_price` | Active rate's price amount | Null if no rate |
| `rate_id` | Active rate's ID (`JacksonHotelRate.id`) | Null if no rate |
| `strikethrough_price` | `JacksonHotelRate.usualPrice.usualAmount` | Null if no usual price |
| `promocode` | First promo code from `JacksonHotelRate.promos` | Null if no promo |
| `rate_tags` | `JacksonHotelRate.rateTag.label` or name | Null if no tag |
| `social_proof` | Format: `"type-value"` (e.g., `"satisfaction-85"`) | Null if none |
| `hotel_sort_order_position` | 1-based index in list view; omitted in map view | Only for list view |

**Null handling:** Fields with null values are **omitted** from the JSON (not sent as empty strings).

### Key Decisions (from iOS PR reference)
- Action changed from `"clicked"` to `"selected"`
- `labels` field mentioned in ticket is **NOT implemented** (iOS PR doesn't include it)
- Position is 1-based for list, omitted for map
- Uses existing `logGenzoClickEventAction()` infrastructure with enhanced value parameter

## Applicable Rules
- `coding-conventions` - Kotlin formatting, naming
- `critical-thinking` - Verify data availability at click time
