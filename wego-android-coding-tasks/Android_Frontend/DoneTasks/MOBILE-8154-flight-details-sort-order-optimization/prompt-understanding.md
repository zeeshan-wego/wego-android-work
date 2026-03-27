# MOBILE-8154: Flight Details Sort Order Optimization (Phase 1)

## What We're Building

An A/B test experiment on the Flight Details page that changes how fare providers are sorted in the **middle** position buckets. The goal is to optimize sort order for profitability (+3% rev/user) without degrading user experience.

## How It Works

### Current Behavior (Baseline)
When a user opens Flight Details, fares are sorted by:
1. Baggage filter match (checked vs unchecked)
2. Within each group: price ascending (cheapest first)

There is **no position-based sorting** in the live ViewModel path. The position-aware sorting (`sortFaresByPositionTypes()`) exists only in the deprecated Presenter path.

### New Behavior (Variant A / Variant B)
For fares in **middle with fees** and **middle without fees** buckets:
- Sort by `rankingScore` **descending** (higher score = higher position)
- `rankingScore` is a new field the API sends per fare
- The app does NOT calculate the score — the backend does, using different `alpha` weights per variant
- Top, bottom, and sponsored fares remain unaffected

### Experiment Variants
| Variant | App Behavior | Backend Alpha |
|---------|-------------|---------------|
| `baseline` | Keep existing sort (ignore rankingScore) | 0 |
| `variantA` | Sort middle fares by rankingScore desc | 0.1 |
| `variantB` | Sort middle fares by rankingScore desc | 0.8 |

App behavior is identical for variantA and variantB — the difference is only in the backend's scoring calculation.

## Key Technical Details

### Feature Flag
- **Key:** `a_ads_330_sort_order`
- **Source:** Pennyworth via CoreConfig (delivered in `/app/sections` API response)
- **Read pattern:** `WegoConfig.instance.getString("a_ads_330_sort_order")`
- **Values:** `baseline`, `variantA`, `variantB`

### API Contract Change
- New field `rankingScore` (Double/number) in the fare object
- Available in v5 and v6 trip detail endpoints
- Null/missing `rankingScore` = fare goes to bottom of its bucket

### Fare Position Buckets (display order)
1. Sponsored (`sponsoredListing = true`)
2. Top (`position = "top"`)
3. Middle with fees (`position = "middle"` + has `paymentFees`)
4. Middle without fees (`position = "middle"` + no `paymentFees`)
5. Bottom (`position = "bottom"`)

Only buckets 3 and 4 are affected by the experiment.

### Architecture: Presenter → ViewModel Flow
The Flight Details page has a **sequential flow**:

```
API Response → Presenter.onSuccess()
  → sortFares() → FlightDetailUtil.sortFaresByPositionTypes()  ← SORTING HERE
    → Fragment.setBookWith(pre-sorted fares)
      → ViewModel.updateFareData(pre-sorted fares)  ← receives already-sorted
        → buildFareModels() preserves order → UI displays
```

- **Presenter** sorts fares via `FlightDetailUtil.sortFaresByPositionTypes()`
- **ViewModel** receives pre-sorted fares, converts to UI models, applies baggage filters
- New features go in ViewModel, but sorting lives in the Presenter/Util layer

### Implementation Decision: Option A — Modify `sortFaresByPositionTypes()`
Modify the existing sorting in `FlightDetailUtil.sortFaresByPositionTypes()` to use `rankingScore` for middle buckets when experiment variant is A/B. This is minimal change in the right place — no duplication, no fighting the existing flow.

### BOW Fare Handling
- BOW eCPC x2 is backend-only — app just sorts by the `rankingScore` the API sends
- No special client-side handling needed for BOW fares in this experiment

## Acceptance Criteria
- [ ] Parse `rankingScore` from API fare response (v5/v6)
- [ ] Read experiment variant from `a_ads_330_sort_order` feature flag
- [ ] Baseline: existing sort behavior unchanged
- [ ] Variant A/B: middle fares sorted by `rankingScore` descending
- [ ] Top, bottom, sponsored fares unaffected
- [ ] Null/missing `rankingScore` treated as lowest priority
- [ ] Analytics: experiment variant logged via existing CoreConfig mechanism

## Applicable Rules
- **coding-conventions** — Detekt strict mode, 120 char lines, Timber logging
- **project-structure** — Changes span `libbase` (API model) and `flights` (sorting logic, ViewModel)
- **critical-thinking** — Position-based sorting integration into ViewModel needs careful approach to avoid breaking existing behavior
