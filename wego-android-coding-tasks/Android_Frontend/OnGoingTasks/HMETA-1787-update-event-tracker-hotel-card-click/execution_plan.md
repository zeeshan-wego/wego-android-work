# HMETA-1787: Update Event Tracker for Hotel Card Click

**Branch:** `feature/hmeta-1787-hotel-card-click-tracking`

## Summary

Add a JSON event value to hotel card click tracking on SRP. The existing Genzo v3 `logGenzoClickEventAction()` already fires on map view clicks (rate_icon, rate_card) but passes `null` as value. We need to:
1. Build a JSON value string with hotel data and pass it to the existing method
2. Add list view click tracking (currently missing)
3. Change action from `"clicked"` to `"selected"`
4. Apply to both V4 and V2 ViewModels/Fragments

## Approach

### Step 1: Add `SELECTED` constant
- Add `String SELECTED = "selected"` to `ConstantsLib.GenzoHotelSearchResults.Action`

### Step 2: Create `HotelCardClickTrackingValue` utility class
New file in `hotelsv2` module that builds the JSON value string:
- Takes `HotelResult`, active `JacksonHotelRate`, and optional position
- Builds JSON with: `hotel_id`, `hotel_price`, `rate_id`, `strikethrough_price`, `promocode`, `rate_tags`, `social_proof`, `hotel_sort_order_position`
- Omits null fields from JSON
- Social proof format: `"satisfaction-{score}"` using `h_satisfaction`

### Step 3: Add `trackHotelCardClick()` to ViewModels
New method in `HotelSearchResultsViewModelV4` and `HotelSearchResultsViewModel` (V2):
- Takes `hotelId: Int`, `position: Int?`, `eventObject: String`
- Looks up `HotelResult` from adapter data and active rate from `allResponse.hotelsRates`
- Builds `HotelCardClickTrackingValue` and calls `logGenzoClickEventAction()` with action `"selected"`

### Step 4: Update existing call sites

**FragmentV4:**
- Map view rate_icon click (line 459): Pass hotel ID, no position
- Map view rate_card click (line 464): Pass hotel ID, no position
- List view click (line 1611-1616): Add new tracking with 1-based position

**FragmentV2:**
- Map view rate_icon click (line 411): Pass hotel ID, no position
- Map view rate_card click (line 416): Pass hotel ID, no position
- List view click: Add new tracking with 1-based position

### Step 5: Update `logGenzoClickEventAction` signature
- Add `action` parameter with default `CLICKED` for backward compatibility
- New hotel card click calls pass `SELECTED`

## Files to Change

| File | Change |
|------|--------|
| `libbase/.../ConstantsLib.java` | Add `SELECTED` constant |
| `hotelsv2/.../HotelCardClickTrackingValue.kt` | **NEW** - JSON value builder |
| `hotelsv2/.../HotelSearchResultsViewModelV4.kt` | Add `trackHotelCardClick()`, update `logGenzoClickEventAction` |
| `hotelsv2/.../HotelSearchResultsViewModel.kt` | Add `trackHotelCardClick()`, update `logGenzoClickEventAction` |
| `hotelsv2/.../HotelSearchResultsFragmentV4.kt` | Update map click calls, add list view tracking |
| `hotelsv2/.../HotelSearchResultsFragmentV2.kt` | Update map click calls, add list view tracking |

## Test Plan
- Unit test for `HotelCardClickTrackingValue` JSON output
- Verify null fields are omitted
- Verify 1-based position for list, null for map
- Verify social_proof format

## Acceptance Criteria
- [ ] List view hotel card click fires `rate_card` / `selected` with JSON value
- [ ] Map view marker tap fires `rate_icon` / `selected` with JSON value (no position)
- [ ] Map view card tap fires `rate_card` / `selected` with JSON value (no position)
- [ ] JSON contains correct fields from hotel data
- [ ] Null fields omitted from JSON
- [ ] Social proof format: `type-value`
