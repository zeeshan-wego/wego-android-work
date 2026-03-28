# MOBILE-8155: GMA SDK Implementation Audit & Fix

## Execution Tracking
- **Branch:** feature/mobile-8155-gma-sdk-implementation-audit-fix

## Summary

Fix Google Mobile Ads SDK implementation so ad requests include `google_sdk_version` signal and qualify for AdX bidding. Three changes: explicit SDK initialization, fallback delay, and SDK version bump.

## Approach

### Phase 1: Add `MobileAds.initialize()` in AdsManager Constructor

**File:** `wegoapk/src/main/java/com/wego/android/managers/AdsManager.java` (line 56-57)

```java
private AdsManager(Context applicationContext) {
    MobileAds.initialize(applicationContext, initializationStatus ->
        WegoLogger.d("AdsManager", "GMA SDK initialized: " + initializationStatus)
    );
}
```

**Import:** `com.google.android.gms.ads.MobileAds`

**Why main thread is fine:** GMA SDK v24+ has `OPTIMIZE_INITIALIZATION` (default true) which automatically offloads heavy init work to background threads internally. No manual threading needed.

**Why constructor:** Called only once (guarded by `instance == null` in `init()`). The `init()` method re-registers EventBus on every call, so SDK init must not go there.

### Phase 2: Add 500ms Delay Before FLUID→BANNER Fallback

**File:** `wegoapk/src/main/java/com/wego/android/managers/AdsManager.java`

Add `Handler.postDelayed(500)` in 3 locations:

1. **`flightsLoadDFPNativeAd`** `onAdFailedToLoad` (lines 174-181)
2. **`hotelsLoadDFPNativeAd`** `onAdFailedToLoad` (lines 342-349)
3. **`perLegFlightsLoadDFPNativeAd`** `onAdFailedToLoad` (lines 109-112)

Pattern for each:
```java
@Override
public void onAdFailedToLoad(@NonNull LoadAdError loadAdError) {
    if (adtype.equals(AdSize.FLUID)) {
        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            // existing BANNER retry call
        }, 500);
    }
    // ... rest unchanged
}
```

**Import:** `android.os.Handler`, `android.os.Looper`

**Home ads (`homeLoadAds`):** BANNER only, no fallback — add TODO comment.

### Phase 3: SDK Version Upgrade

**File:** `gradle/libs.versions.toml` (line 51)

```
gmsVersionAds = '24.9.0'
```

## Files to Modify

| File | Change | Lines Added |
|------|--------|-------------|
| `wegoapk/.../managers/AdsManager.java` | Phase 1 + Phase 2 | ~15 lines |
| `gradle/libs.versions.toml` | Phase 3 version bump | 1 line |

**Line count:** 547 + ~15 = ~562 (safely under 600 Detekt limit)

## Test Plan

- `./gradlew :wegoapk:assemblePlaystoreDebug` — build succeeds
- `./gradlew detekt` — passes with maxIssues=0
- `./gradlew :wegoapk:testPlaystoreDebugUnitTest` — all pass

## Documentation Updates

- None required (no API or DB changes)

## PR Notes

Include in PR description:
- **Follow-up needed:** Consent gating (`canRequestAds()`) should be added in a separate ticket after coordinating UMP initialization with adops.
- **Action item for adops:** Verify Remote Config flag `a_enable_ump_google_consent` is enabled in production.
- **25.x SDK upgrade** should be a separate ticket (breaking changes).

### Phase 4: Fix HotelsV2 Ads Not Loading (Discovered During Audit)

**File:** `wegoapk/src/main/java/com/wego/android/managers/AdsManager.java`

**Problem:** HotelsV2 module posts `com.wego.android.hotelfeaturesv2.eventbus.HotelsAdsManagerEvent` but AdsManager only subscribes to `com.wego.android.eventbus.HotelsAdsManagerEvent` (v1). Otto EventBus matches by exact class type, so hotelsv2 ads were never loading.

**Fix:** Added separate `@Subscribe` method for the hotelsv2 event class.

```java
@Subscribe
public void hotelsV2AdsEventListener(com.wego.android.hotelfeaturesv2.eventbus.HotelsAdsManagerEvent event) {
    // delegates to same hotelsLoadAds()
}
```

## Acceptance Criteria

- [x] `MobileAds.initialize()` called once at app startup
- [x] FLUID→BANNER fallback has 500ms delay
- [x] SDK version upgraded to 24.9.0
- [x] HotelsV2 ads loading via correct EventBus subscription
- [x] Build, detekt, and tests pass