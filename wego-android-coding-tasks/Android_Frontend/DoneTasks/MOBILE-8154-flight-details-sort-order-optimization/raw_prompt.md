# [Android] Flight Details page: Sort Order Optimization (Phase 1)

**Jira Ticket:** https://wegomushi.atlassian.net/browse/MOBILE-8154
**Type:** Task
**Priority:** Standard
**Assignee:** Muthuraman

## Description

Sort order experiments that honor our profitability.

## Context & Linked Resources

- **Overall Tech Plan:** https://wegomushi.atlassian.net/wiki/spaces/Advertisin/pages/3608018946
- **PRD:** https://wegomushi.atlassian.net/wiki/spaces/Advertisin/pages/3594682509
- **API Contract Changes:** https://wegomushi.atlassian.net/wiki/spaces/Advertisin/pages/3608018946#API-contract-changes
- **Sort Order Changes:** https://wegomushi.atlassian.net/wiki/spaces/Advertisin/pages/3608018946#Web%2Fmobile-sorting-logic
- **Test Plan:** https://wegomushi.atlassian.net/wiki/spaces/Advertisin/pages/3608018946#Test-Plan

## Tech Plan Summary

### Overview
Sort order experiments with reversible tech approach so we can release it sooner.

### Success Criteria
| Goal | Metric | Target |
|------|--------|--------|
| Rev/User Uplift | Rev/user | +3% |
| Guardrails | HoP CTR CVR | No degradation (within 1% of baseline) |

### Android Experiment Setup
- **Key:** `a_ads_330_sort_order`
- **Pennyworth Experiment:** https://pennyworth.staging.wego.net/us/sdc/abtests/experiments/386
- **Pennyworth Feature Flag:** https://pennyworth.staging.wego.net/us/sdc/core-config/820

### BE Expectation (ANDROID_APP / ANDROID_TABLET_APP)
- `baseline` → alpha = 0
- `variantA` → alpha = 0.1
- `variantB` → alpha = 0.8

### Android Expectation
- **Baseline** → keep existing sort logic (not using score)
- **Variant A, Variant B** → sort using score on middle with fees and middle without fees

### API Contract Changes
- New field `rankingScore` in the fare object (v5 and v6)
- Example:
```json
{
  "trip": {
    "fares": [
      {
        "id": "ff76ab97c52ccec2msr:kupi.com:ba45eef1fb2c7528",
        "rankingScore": 1234,
        "position": "middle"
      },
      {
        "id": "ff76ab97c52ccec2msr:waya.travel:b6ff70523ee16e89",
        "rankingScore": 1134,
        "position": "middle"
      }
    ]
  }
}
```

### Sorting Logic
- Sort applied to: `middle with fees` and `middle without fees` buckets only
- Sort by `rankingScore` descending (higher score = higher priority)
- Only sort by ranking score (no secondary sort)

### Test Plan
1. Set variant in Pennyworth Test Device
2. Make search on staging
3. Open flight detail page
4. Copy trip detail API URL from network
5. Paste URL to fare ranking calculator simulator
6. Compare fare order in simulator vs flight detail page

### Test Data (Staging)
**Scenario 1: Airline at top, has Wego fare, no sponsor**
- POS: SA, Route: JED-CAI, 1 adult, Click Saudia flight

**Scenario 2: Airline at middle, no Wego fare, has sponsor**
- POS: KW, Route: KWI-CAI, 2 adults, Click Kuwait Airways

---
*Fetched from Jira on 2026-03-26*