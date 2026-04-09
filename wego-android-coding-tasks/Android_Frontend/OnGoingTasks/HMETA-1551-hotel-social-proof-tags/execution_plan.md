# Execution Plan: HMETA-1551 + HMETA-1552 Hotel Social Proof Tags

**Branch:** `feature/hmeta-1551-hotel-social-proof-tags`
**Tickets:** HMETA-1551 (SRP) + HMETA-1552 (Hotel Details)

## Summary

Add social proof tags ("Selling fast!", "Only X rooms left", "Loved by X") on:
1. **Hotel search result cards (SRP)** - HMETA-1551
2. **Hotel details room info section** - HMETA-1552

Parse from API at hotel and rate levels, resolve priority, display with icon + colored text, gated behind A/B test flag.

## Key Design Notes

- **`value` is String** (not Int) - API can send Int or String. iOS PR #2174 confirmed this and switched to String with flexible parsing. Android Jackson handles this via `@JsonProperty` with String type.
- **Detail page uses different display text** for room scarcity: "Hurry up! Only X rooms left" (`lbl_social_proof_room_scarcity_detail` plural) vs SRP's "Only X rooms left"
- **TRAVELLER_POPULARITY value** is a String like "families", "couples" - not always numeric
- **Hotel details** gets social proof from the rates API response (`hotelSocialProof` at response level + `rateSocialProof` per rate)

## Files to Change

### Phase 1: Model + API Parsing (shared by both tickets)

#### 1.1 New Model - `libbase`
- **NEW** `libbase/src/main/java/com/wego/android/models/hotels/JacksonHotelSocialProof.kt`
  - Data class: `priority: Int`, `type: String`, `value: String`
  - Enum `SocialProofType`: `BOOKING_STATS`, `ROOM_SCARCITY`, `TRAVELLER_POPULARITY`
  - `displayText` (SRP): "Selling fast!" / "Only X rooms left" / "Loved by {value}"
  - `detailDisplayText` (Details): "Hurry up! Only X rooms left" for ROOM_SCARCITY, others same
  - `iconResName`: drawable resource names for each type
  - `titleColorRes` / `iconColorRes`: color resource IDs
  - Companion `resolvePriority(hotel, rate)`: lowest priority wins, hotel wins ties, rate preferred in fallback

#### 1.2 Add to Hotel API model - `libbase`
- **MODIFY** `libbase/src/main/java/com/wego/android/models/hotels/JacksonHotel.java`
  - Add `JacksonHotelSocialProof hotelSocialProof` field with getter

#### 1.3 Add to Rate API model - `libbase`
- **MODIFY** `libbase/src/main/java/com/wego/android/models/hotels/JacksonHotelRate.java`
  - Add `JacksonHotelSocialProof rateSocialProof` field with getter
  - Add to Parcelable (writeToParcel / constructor from Parcel)

#### 1.4 Add to Rate Response model - `libbase`
- **MODIFY** `libbase/src/main/java/com/wego/android/models/hotels/JacksonHotelRateResponse.kt`
  - Add `val hotelSocialProof: JacksonHotelSocialProof? = null`

#### 1.5 Carry through to display model - `libbase`
- **MODIFY** `libbase/src/main/java/com/wego/android/models/hotels/JacksonHotelResult.java`
  - Add `JacksonHotelSocialProof socialProof` field with getter/setter
  - Add to `clone()` method

#### 1.6 Remote Config Flag
- **MODIFY** `libbase/src/main/java/com/wego/android/ConstantsLib.java`
  - Add `HOTEL_RESULTS_SHOW_SOCIAL_PROOF_TAGS = "a_hmeta_1553_hotel_results_show_social_proof_tags_fixed"`

- **MODIFY** `libbase/src/main/res/raw/config_defaults.json`
  - Add `"a_hmeta_1553_hotel_results_show_social_proof_tags_fixed": false`

### Phase 2: SRP Display (HMETA-1551)

#### 2.1 Data flow in adapter - `hotelsv2`
- **MODIFY** `hotelsv2/.../adapters/HotelResultListAdapter.kt`
  - In `addHotels()`: carry `hotelSocialProof` from `JacksonHotel` to `JacksonHotelResult`
  - In bind: resolve priority between hotel-level and best rate-level social proof

#### 2.2 Layout - `hotelsv2`
- **MODIFY** `hotelsv2/src/main/res/layout/row_hotel_search_full_result.xml`
  - Add `LinearLayout` (horizontal) with `ImageView` (16dp) + `TextView` (12sp semibold) for social proof, below amenities, above price section

#### 2.3 ViewHolder - `hotelsv2`
- **MODIFY** `hotelsv2/.../adapters/HotelResultItemViewHolderV2.kt`
  - Add `socialProofContainer`, `socialProofIcon`, `socialProofLabel` view refs
  - Add `configureSocialProof()` method
  - Read config flag, show/hide based on data + flag

### Phase 3: Hotel Details Display (HMETA-1552)

#### 3.1 Rate adapter - `hotelsv2`
- **MODIFY** `hotelsv2/.../adapters/RatesAdapter.kt`
  - In `onBindViewHolder`: display social proof from the resolved social proof on the rate item
  - Add social proof icon + label views

#### 3.2 Rate layout - `hotelsv2`
- **MODIFY** `hotelsv2/src/main/res/layout/row_hotel_book_mata.xml` (and/or `row_hotel_book.xml`)
  - Add social proof icon + label views in the rate card

#### 3.3 ViewModel - `hotelsv2`
- **MODIFY** `hotelsv2/.../features/hoteldetails/HotelDetailsViewModel.kt`
  - Resolve social proof from `JacksonHotelRateResponse.hotelSocialProof` + rate-level `rateSocialProof`
  - Pass resolved social proof through to rate display

#### 3.4 UI State - `hotelsv2`
- **MODIFY** `hotelsv2/.../data/models/HotelDetailsRatesUiState.kt`
  - Add `socialProof: JacksonHotelSocialProof?` field

### Phase 4: Tests

- **NEW** `libbase/src/test/java/com/wego/android/models/hotels/JacksonHotelSocialProofTest.kt`
  - Type parsing (all 3 types + unknown)
  - Display text for SRP (all types)
  - Detail display text (room scarcity uses detail-specific text)
  - Colors and icons per type
  - Priority resolution (hotel only, rate only, both - lower wins, equal - hotel wins, neither)
  - Value as String handling (numeric and non-numeric)

## Acceptance Criteria

### HMETA-1551 (SRP)
- [ ] Parse `hotelSocialProof` from hotel search API response
- [ ] Parse `rateSocialProof` from rate in search API response
- [ ] Priority resolution: lowest priority wins, hotel wins ties
- [ ] Display on SRP cards with correct icon, text, colors
- [ ] Gated behind `a_hmeta_1553_hotel_results_show_social_proof_tags_fixed`
- [ ] Existing tags unaffected

### HMETA-1552 (Hotel Details)
- [ ] Parse `hotelSocialProof` from hotel rates API response
- [ ] Parse `rateSocialProof` from individual rates
- [ ] Room scarcity uses detail text: "Hurry up! Only X rooms left"
- [ ] Display in room info / rate section
- [ ] Same A/B flag gates it

### Shared
- [ ] `value` field handles both Int and String from API
- [ ] Unit tests cover all scenarios

## Reminders

- **Icons needed**: User will add fire, clock, people/thumbs_up drawables - remind when reaching UI phase
