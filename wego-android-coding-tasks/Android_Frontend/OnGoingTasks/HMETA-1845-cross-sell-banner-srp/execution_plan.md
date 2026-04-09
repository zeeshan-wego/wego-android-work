# HMETA-1845: Cross-sell Banner in Hotel Search Results Page

**Branch:** `feature/hmeta-1845-cross-sell-banner-srp`

## Summary

Add a cross-sell banner to the hotel SRP that shows when users arrive from a cross-sell flow. The banner replaces the login banner slot (position 0) and opens an info bottom sheet on tap.

## Approach

Follow the existing login banner pattern in `HotelResultListAdapter`:
- Add a new type constant `TYPE_CROSS_SELL_BANNER` to `JacksonHotelResult`
- Add a new `addCrossSellBanner()` method mirroring `addSignUpBanner()`
- Create XML layout for the banner and bottom sheet
- Create ViewHolder and BottomSheetDialogFragment classes
- Wire the `crossSell` flag from ViewModel through to the adapter

**Key decision:** Use XML (not Compose) for the banner since it lives inside a `BaseAdapter` ListView pattern alongside the existing login banner. The bottom sheet also uses XML following the `HotelFacilitiesBottomSheet` pattern.

**Cross-sell detection:** The `dlInternalCampaign` is already available in the ViewModel. We'll check it against all cross-sell campaign types (`HOTEL_CROSSSELL`, `HOTEL_CROSSSELL_HOMEPAGE`, `HOTEL_CROSSSELL_MYTRIPS`, `HOTEL_CROSSSELL_MEMBER`) to set a flag on the adapter.

## Files to Change

### New Files
| File | Purpose |
|------|---------|
| `hotelsv2/src/main/res/layout/cross_sell_banner.xml` | Cross-sell banner layout (green bg, title, subtitle, Fly&Save badge, monster image) |
| `hotelsv2/src/main/res/layout/bottom_sheet_cross_sell_info.xml` | Bottom sheet layout (flight+hotel icons, title, body, close button) |
| `hotelsv2/src/main/java/.../hotelsearchresults/CrossSellInfoBottomSheet.kt` | BottomSheetDialogFragment for cross-sell info |

### Modified Files
| File | Change |
|------|--------|
| `libbase/.../models/hotels/JacksonHotelResult.java` | Add `TYPE_CROSS_SELL_BANNER = 10` constant |
| `hotelsv2/.../adapters/HotelResultListAdapter.kt` | Add `isCrossSell` flag, `addCrossSellBanner()`, `CrossSellBannerViewHolder`, view type handling |
| `hotelsv2/.../hotelsearchresults/HotelSearchResultsFragmentV2.kt` | Pass cross-sell flag to adapter, show bottom sheet on banner click |
| `hotelsv2/.../hotelsearchresults/HotelSearchResultsViewModel.kt` | Expose `isCrossSellSearch` based on `dlInternalCampaign` |
| `localisation/src/main/res/values/strings.xml` | Add new string resources for banner and bottom sheet text |

### Drawable Resources (New)
| File | Purpose |
|------|---------|
| `hotelsv2/src/main/res/drawable/bg_cross_sell_banner.xml` | Rounded corner green background for banner |
| `hotelsv2/src/main/res/drawable/bg_fly_save_badge.xml` | Red "Fly & Save" badge background |
| `hotelsv2/src/main/res/drawable/ic_cross_sell_monster.xml` or PNG | Monster mascot image (check if exists in assets) |

## Implementation Steps

### Step 1: Add Type Constant
- In `JacksonHotelResult.java`, add `public static byte TYPE_CROSS_SELL_BANNER = 10;`
- In `HotelResultListAdapter.kt` companion object, add `private const val VIEW_TYPE_CROSS_SELL = 10`
- Update `getViewTypeCount()` to return 11

### Step 2: Add String Resources
Add to `localisation/src/main/res/values/strings.xml`:
- `cross_sell_banner_title`: "Your flight unlocked private hotel rates"
- `cross_sell_banner_subtitle`: "Only available with your booking."
- `cross_sell_badge_text`: "Fly & Save"
- `cross_sell_info_title`: "You've just accessed a restricted price tier."
- `cross_sell_info_body`: "You booked your flight with us, so you can see Fly & Save hotel prices for this trip. These prices aren't available to everyone — add a hotel to save."

### Step 3: Create Banner Layout XML
Create `cross_sell_banner.xml` — similar structure to `log_in_banner.xml` but with:
- Light green rounded background
- Title + subtitle on the left
- "Fly & Save" red badge at top-right
- Monster mascot image on the right
- Clickable container

### Step 4: Create Bottom Sheet Layout + Fragment
- Create `bottom_sheet_cross_sell_info.xml` with close button, icons row, title, body
- Create `CrossSellInfoBottomSheet.kt` following `HotelFacilitiesBottomSheet` pattern

### Step 5: Create ViewHolder + Adapter Logic
In `HotelResultListAdapter.kt`:
- Add `var isCrossSell: Boolean = false`
- Add `CrossSellBannerViewHolder` inner class
- Add `addCrossSellBanner()` method that inserts at position 0 when `isCrossSell` is true
- Modify `addSignUpBanner()` to skip when `isCrossSell` is true
- Update `getItemViewType()` to handle `TYPE_CROSS_SELL_BANNER`
- Update `getView()` to inflate cross-sell banner
- Add listener callback `onCrossSellBannerClick()`

### Step 6: Wire ViewModel → Fragment → Adapter
- In `HotelSearchResultsViewModel.kt`: Add `isCrossSellSearch` property checking `dlInternalCampaign` against all cross-sell campaign constants
- In `HotelSearchResultsFragmentV2.kt`: Set `mAdapter?.isCrossSell` from ViewModel, handle banner click to show bottom sheet

### Step 7: Add to Adapter Listener Interface
- Add `onCrossSellBannerClick()` to `HotelResultListAdapterListener` interface

## Test Plan
- **Manual:** Trigger cross-sell flow from flight booking → verify banner appears
- **Manual:** Normal hotel search → verify login banner still shows for logged-out users
- **Manual:** Normal hotel search while logged in → verify no banner
- **Manual:** Tap cross-sell banner → verify bottom sheet opens with correct content
- **Manual:** Tap X on bottom sheet → verify it dismisses
- **Unit test:** `addCrossSellBanner()` inserts item at position 0 with correct type
- **Unit test:** `addSignUpBanner()` skips when `isCrossSell = true`

## Acceptance Criteria
- [x] Cross-sell banner shows at top of results for cross-sell searches
- [x] Login banner shows for non-cross-sell + not logged in
- [x] Cross-sell banner takes priority over login banner
- [x] No banner for non-cross-sell + logged in
- [x] Banner occupies same layout position as login banner
- [x] Tapping banner opens info bottom sheet
- [x] Bottom sheet dismissible with X button
