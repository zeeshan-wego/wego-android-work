# Execution Plan: MOBILE-8154 Flight Details Sort Order Optimization (Phase 1)

## Summary
Add A/B test experiment support to sort middle fare buckets by `rankingScore` (from API) on the Flight Details page. Modify the existing `sortFaresByPositionTypes()` in `FlightDetailUtil.kt` to swap the middle comparator when the experiment variant is A or B.

## Branch
`feature/mobile-8154-flight-details-sort-order-optimization`

## Approach

**Minimal change in the right place.** The Presenter already sorts fares via `FlightDetailUtil.sortFaresByPositionTypes()` before passing to the ViewModel. We add a `rankingScore` comparator for middle buckets, gated by the experiment flag.

### Trade-offs
- **Option A (chosen):** Modify `sortFaresByPositionTypes()` — minimal, no duplication, right layer
- **Option B (rejected):** Re-sort in ViewModel — duplicates logic, fights existing flow

## Files to Change

### 1. `libbase` — API Model + Constant

**`libbase/src/main/java/com/wego/android/data/models/JacksonFlightFare.java`**
- Add field: `Double rankingScore`
- Add getter: `getRankingScore()`

**`libbase/src/main/java/com/wego/android/ConstantsLib.java`**
- Add constant in `FirebaseRemoteConfigKeys`:
  ```java
  String FLIGHT_DETAIL_SORT_ORDER_VARIANT = "a_ads_330_sort_order";
  ```

### 2. `flights` — Sorting Logic

**`flights/src/main/java/com/wego/android/util/FlightDetailUtil.kt`**
- Add `rankingScoreComparator`: sort by `rankingScore` descending, nulls last
- Modify `sortFaresByPositionTypes()`: accept a parameter or read the experiment flag to decide which comparator to use for middle buckets
- When variant is `variantA` or `variantB` → use `rankingScoreComparator` for middle fares
- When variant is `baseline` (or unknown/null) → use existing `middleComparator`

### 3. `flights` — Presenter (pass experiment flag)

**`flights/src/main/java/com/wego/android/features/flightdetails/FlightDetailsPresenter.java`**
- In `sortFares()`: read experiment variant via `WegoConfig.instance.getString(FLIGHT_DETAIL_SORT_ORDER_VARIANT)`
- Pass variant to `sortFaresByPositionTypes()` so it can choose the right comparator

### 4. Tests

**`flights/src/test/java/com/wego/android/util/FlightDetailUtilTest.kt`**
- Test: baseline variant → middle fares sorted by price (existing behavior)
- Test: variantA → middle fares sorted by rankingScore descending
- Test: variantB → middle fares sorted by rankingScore descending
- Test: null/missing rankingScore → fare goes to bottom of its middle bucket
- Test: top/bottom/sponsored fares unaffected by experiment

## Implementation Steps

### Step 1: Add `rankingScore` field to API model
- File: `JacksonFlightFare.java`
- Add `Double rankingScore` field + getter
- Minimal — Jackson auto-deserializes from API JSON

### Step 2: Add experiment constant
- File: `ConstantsLib.java`
- Add `FLIGHT_DETAIL_SORT_ORDER_VARIANT = "a_ads_330_sort_order"` in `FirebaseRemoteConfigKeys`

### Step 3: Add rankingScore comparator + modify sorting
- File: `FlightDetailUtil.kt`
- Add new parameter `experimentVariant: String?` to `sortFaresByPositionTypes()`
- Build `rankingScoreComparator` (descending, nulls last)
- When variant is `variantA`/`variantB` → use it for middle buckets
- Otherwise → existing `middleComparator`

### Step 4: Wire experiment flag in Presenter
- File: `FlightDetailsPresenter.java`
- Read variant from WegoConfig in `sortFares()`
- Pass to `sortFaresByPositionTypes()`

### Step 5: Write unit tests
- File: `FlightDetailUtilTest.kt`
- Cover all scenarios listed above

## Test Plan
1. **Unit tests:** Verify sorting behavior per variant
2. **Manual testing (staging):**
   - Set variant in Pennyworth Test Device
   - Search flights, open flight details
   - Compare fare order vs fare ranking calculator simulator
   - Test with both test data scenarios from tech plan

## Acceptance Criteria
- [ ] `rankingScore` parsed from API fare response
- [ ] Experiment flag `a_ads_330_sort_order` read from WegoConfig
- [ ] Baseline: existing sort unchanged
- [ ] Variant A/B: middle fares sorted by rankingScore descending
- [ ] Top/bottom/sponsored unaffected
- [ ] Null rankingScore = lowest priority in bucket
- [ ] Unit tests pass
- [ ] Detekt passes (maxIssues=0)
