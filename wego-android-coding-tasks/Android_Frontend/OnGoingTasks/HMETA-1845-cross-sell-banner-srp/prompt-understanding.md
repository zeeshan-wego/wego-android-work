# HMETA-1845: Cross-sell Banner in Hotel Search Results Page

**Jira Ticket:** https://wegomushi.atlassian.net/browse/HMETA-1845

## Summary

Add a cross-sell banner at the top of the hotel search results list when users arrive from a cross-sell flow (e.g., after completing a flight booking). The banner replaces the login banner position and communicates exclusive "Fly & Save" pricing. Tapping the banner opens a bottom sheet explaining the restricted price tier.

## Requirements

### Cross-sell Banner (SRP list item)
- **Position:** Top of hotel results list (position 0), same slot as the existing login banner
- **Background:** Light green
- **Content:**
  - Title: "Your flight unlocked private hotel rates"
  - Subtitle: "Only available with your booking."
  - "Fly & Save" red badge at top-right corner
  - Green monster mascot image on the right side
- **Behavior:** Tapping opens a bottom sheet dialog
- **Priority:** Cross-sell banner takes priority over login banner (they never show together)

### Cross-sell Info Bottom Sheet
- **Trigger:** Tap on the cross-sell banner
- **Icons:** Flight icon + "+" + Hotel icon at the top
- **Title:** "You've just accessed a restricted price tier."
- **Body:** "You booked your flight with us, so you can see Fly & Save hotel prices for this trip. These prices aren't available to everyone — add a hotel to save."
- **Close:** X button at top-left

### Visibility Rules
| Condition | Banner Shown |
|-----------|-------------|
| Cross-sell search | Cross-sell banner (no login banner) |
| Not cross-sell + not logged in | Login banner (existing behavior) |
| Not cross-sell + logged in | No banner |

### Cross-sell Detection
The `JacksonHotelSearch.crossSell` flag is already set to `true` when the `internalCampaign` matches any of:
- `hotels_crosssell`
- `hotels_crosssell_homepage`
- `hotels_crosssell_mytrips`
- `hotels_crosssell_member`

This flag is set in `HotelRepository.java` (lines 1299-1302) but is **not currently used in the SRP UI layer**. It needs to be passed through to the adapter.

## Existing Patterns to Follow

- **Login banner:** `addSignUpBanner()` in `HotelResultListAdapter.kt` — creates `JacksonHotelResult` with `TYPE_LOG_IN`, inserts at position 0
- **Bottom sheets:** `HotelFacilitiesBottomSheet.kt` pattern — `BottomSheetDialogFragment`, `Theme_Wego_BottomSheetDialog_Transparent`, companion `newInstance()`
- **Lottie animation:** `x_sell_banner.json` already exists in `hotelsv2/src/main/res/raw/`
- **Strings:** Localized via `localisation/src/main/res/values/strings.xml`

## Out of Scope
- "Fly & Save" badge on individual hotel cards (already visible in screenshot, likely existing feature)
- Cross-sell pricing logic (backend-driven)
- Changes to cross-sell detection logic

## Applicable Rules
- **coding-conventions.md** — Kotlin style, naming, detekt compliance
- **project-structure.md** — Files go in `hotelsv2` module
- **critical-thinking.md** — Verify patterns against existing codebase before implementing
