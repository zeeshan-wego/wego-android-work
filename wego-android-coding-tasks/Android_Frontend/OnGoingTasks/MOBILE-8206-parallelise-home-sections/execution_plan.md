# Execution Plan — MOBILE-8206

**Jira:** https://wegomushi.atlassian.net/browse/MOBILE-8206
**Branch:** `feature/mobile-8206-parallelise-home-sections`
**Module:** `home`

## Execution Tracking

- **Started:** 2026-04-28
- **Developer:** zeeshan@wego.com
- **Branch:** feature/mobile-8206-parallelise-home-sections
- **Collaborators:** (none)

## Summary

Remove the single-flight `isSectionLoading` gate in `SectionsViewModel.loadData()` so all home sections kick off concurrently on cold start. Existing per-section async (Rx `subscribeOn(io)`) already runs off-thread; the bottleneck is purely the queue. Result render order in `items` stays stable via the existing `checkOrderAndInsert(viewType, …)` path.

## Approach

### Core change

`loadData()` currently dequeues exactly **one** section per call and re-enters itself only after that section's callback flips `isSectionLoading` back to false. New behaviour: iterate `sectionsToLoad` once, fire each allowed section's loader, and let their existing async machinery race to completion.

### Trade-off decisions (please confirm before I code)

#### Decision A — Coroutine wrapping vs callback-only

**Option A1 (recommended) — Callback-only, minimal diff**
Just remove the gate. Keep every existing per-section loader exactly as-is (Rx callbacks, Firebase config calls, JSON parses, the existing single coroutine loader). Each one is already non-blocking; they were just being throttled by the queue.

- ✅ Smallest possible diff (~30 lines net change in `SectionsViewModel.kt`).
- ✅ No new dependency.
- ✅ No new failure modes — same threading model as today.
- ❌ Does not satisfy your Phase-1 answer of "wrap Rx in coroutines via `rxSingle`/`await`."
- ❌ The 30+ loader signatures stay heterogeneous (Rx callback / sync / coroutine).

**Option A2 — Add `kotlinx-coroutines-rx3` and migrate Rx loaders to `suspend` + `await`**
Add the dep, change each `getXxxSection()` into a `suspend fun` that does `repo.fetchXxx().await()`, launch them all from `loadData()` via `viewModelScope.launch(ioDispatcher)`.

- ✅ Uniform `suspend fun` shape across all loaders.
- ✅ Native `viewModelScope` cancellation when the VM clears.
- ❌ ~30 loader functions touched → much higher diff and review cost.
- ❌ Adds a new dep (`kotlinx-coroutines-rx3`) — additive but still classpath churn.
- ❌ Higher regression risk for a perf optimisation that doesn't actually need it.

**My recommendation: A1.** The performance win is identical (parallelism comes from the existing `subscribeOn(io)` calls, not from the wrapper choice). A2 is a coroutine-migration project disguised as a perf task. If you still want the migration, I'd treat it as a follow-up MOBILE ticket.

> **Override needed.** Tell me if you want A1 or A2.

#### Decision B — Per-section state map vs no new state

Phase-1 Q&A picked "(b) replace `isSectionLoading` entirely with per-section state." After re-reading the code, `isSectionLoading` is only consumed by `loadData()`'s gate (line 1446) and two log statements (lines 1433, 1448). It does not feed any UI. Per-section state would be **dead state** unless we actively use it for retry buttons, per-section shimmer, or cancellation hooks — none of which are in scope.

**Option B1 (recommended) — Remove `isSectionLoading`; do not introduce a replacement.**
- ✅ Fewer moving parts. Net deletion from a 4156-line file.
- ✅ Implicit "done" state already encoded in `items` (section is either there or isn't).

**Option B2 — Introduce `sectionStates: ConcurrentHashMap<String, SectionLoadState>` for future use.**
- ✅ Forward-compatible if we later want per-section retry / shimmer.
- ❌ YAGNI — no consumer today. Detekt would flag unused properties.

**My recommendation: B1.** Decision A in Phase 1 was made before re-reading the code. If you want B2 anyway (e.g. you have an upcoming ticket that needs it), tell me and I'll wire it up.

> **Override needed.** Tell me if you want B1 or B2.

### Independent / dependent section list (for confirmation)

Based on the Explore agent's read of `loadSection()` (lines 1560–1671), I classify all 30 sections as **independent** (no cross-section data dependency). The Phase-1 ticket hinted at "recent-search-derived offers" but the code doesn't show that — `getOffers()` (3481) reads `homeOffers` populated by `offerListener` (line 281), not by another section's loader.

**Candidate dependent sections: NONE.** Please confirm or call out any I'm missing.

(If anything is dependent, I'll keep it in a serial post-pass after the parallel fan-out completes — same pattern as today, just for that subset.)

### Threading & ordering invariants

- **Section render order** stays stable. `checkOrderAndInsert(ViewType.values()[section.sectionType], …)` already inserts each section at its `ViewType`-ordinal position regardless of completion order. Verified in `onSectionSuccess` (line ~1907).
- **`ObservableList<BaseSection>`** in `BaseViewModel.items` is **not thread-safe**. All `checkOrderAndInsert` / `removePlaceholder` / `homePlaceholderOnly.postValue` calls must originate on the main thread. Today, Rx subscriptions hop to `AndroidSchedulers.mainThread()` before invoking `onSectionSuccess`. **Verify on each loader** that the success/error callback hits main; if any loader currently fires its callback off-main, fix that loader.
- **Synchronous loaders** (`getNewsBanner`, `getDynamicDislaimer`, `getAppUpdate`, `getSignInSection`, `getHotelDiscountSection`, `getCrisisSupportSection`, `getShopCashBanner`, `getCarouselSDUISection`) execute on the calling thread (main, since `loadData()` is invoked from the main lifecycle). They will execute serially among themselves but each takes <10 ms (Firebase config / JSON parse) and runs *in parallel with* all the network sections. No change needed.

## Files to Change

### Modified

| File | Change |
|------|--------|
| `home/src/main/java/com/wego/android/home/viewmodel/SectionsViewModel.kt` | Remove `var isSectionLoading` declaration (line 203). Remove all 12+ read/write sites (lines 348, 374, 391, 1433, 1446, 1448, 1552, 1563, 1665, 1909, 1919, 1929). Rewrite `loadData()` (lines 1424–1454) to iterate `sectionsToLoad` and dispatch each via `loadSection()`. Remove `sectionIndexToLoad` cursor and `getSectionToLoad()` if no longer used. Remove the recursive `loadData()` call from `onSectionError` (line 1920) and `onSectionSkip` (line 1930). |

### Net effect

- `isSectionLoading: Boolean` — deleted
- `sectionIndexToLoad: Int` — deleted (or kept for analytics if it's referenced elsewhere — verify)
- `loadData()` body — rewritten (~10 lines)
- `loadSection()` — first line (`isSectionLoading = true`) deleted
- `onSectionError` / `onSectionSkip` lambdas — `isSectionLoading = false; loadData()` lines deleted

Estimated net diff in `SectionsViewModel.kt`: **−25 to −40 lines.**

### Tests added

Tests added inline in `home/src/test/java/com/wego/android/home/viewmodel/SectionssViewmodelTest.kt` under a `// region Parallel Section Loading (MOBILE-8206)` block. Reverted from the planned new file because the existing setup (~80 lines of MockK fixtures) is non-trivial and not worth duplicating for 11 additional tests.

### NOT changed

- `home/build.gradle` — not modifying (rejecting Option A2 unless you override).
- All 30 `getXxxSection()` loader functions — internals untouched.
- `BaseViewModel.items` ObservableList — keeps current type.
- `HomeFragment.kt` (caller at line 278) — no change needed; `startLoadingData()` keeps its existing signature.
- `Sections.kt` model — unchanged.

## Test Plan

### New unit tests in `SectionsParallelLoadTest.kt`

Using `StandardTestDispatcher` injected as `ioDispatcher`, MockK for repo doubles:

| # | Test | What it asserts |
|---|------|-----------------|
| 1 | `loadData_dispatchesAllSectionsWithoutWaiting` | Given a `sectionsToLoad` list of N allowed sections, `loadData()` invokes each loader's repo call before any completes. |
| 2 | `loadData_insertsSectionsInDisplayOrderRegardlessOfCompletionOrder` | Two sections with different ViewType ordinals; the one that completes second has the lower ordinal; assert `items` ends in display order. |
| 3 | `loadData_oneSectionErrorDoesNotBlockSiblings` | One loader throws / fires `onSectionError`; the other still inserts into `items`. |
| 4 | `loadData_skippedSectionDoesNotPreventOthers` | Section with `isSectionAllowed == false` is silently skipped; remaining sections all load. |
| 5 | `isSectionLoading_isNotPresent` | Reflective check: `SectionsViewModel::class.java.declaredFields` does not contain `isSectionLoading`. (Compile-time guard against accidental re-introduction.) |
| 6 | (if Decision A2 chosen) `loadData_cancelsInFlightSectionsOnViewModelCleared` | Trigger `onCleared`; assert all `viewModelScope` jobs are cancelled. |

Test 6 only applies if we go with Option A2 (suspend functions) — under A1 (callback-only) the existing Rx subscriptions already use `disposables.add(...)`; lifecycle behaviour is unchanged.

### Existing tests

Run `./gradlew :home:testPlaystoreDebugUnitTest --rerun-tasks` to ensure `SectionssViewmodelTest.kt`, `BaseDestViewModelTest.kt`, `HotDealsTest.kt` etc. still pass.

### Local gates

```bash
./gradlew detekt                             # maxIssues=0, blocking
./gradlew :home:testPlaystoreDebugUnitTest --rerun-tasks
./gradlew lintDebug
./gradlew :wegoapk:assemblePlaystoreDebug    # full app build
```

QA owns cold-start TTI measurement (per Phase-1 Q&A); not part of this PR.

## Documentation Updates

`docs_root` is `null` in `.claude/skill.config`, so there is no project-level published-docs path configured. The change is **internal refactor with no API/DB/contract surface**, so no doc updates are required:

- ❌ No API endpoint changes.
- ❌ No DB schema changes.
- ❌ No public component API changes.
- ❌ No new feature flag (the change is unconditional; if you want a remote-config kill switch for safety, tell me and I'll add one).

If a remote-config gate is desired, that's an additional ~15 lines (read flag → fall back to serial path) — call it out and I'll add it to the plan.

## Acceptance Criteria

- [ ] `var isSectionLoading: Boolean` removed from `SectionsViewModel`.
- [ ] `loadData()` dispatches all allowed sections in a single pass.
- [ ] All 30 sections from the `loadSection()` `when` continue to load and insert into `items` exactly as before (visual smoke test by running the app + scrolling home).
- [ ] UI render order in `items` is byte-identical to current behaviour for an identical fixture set (covered by Test 2).
- [ ] One section's error/skip does not block siblings (covered by Tests 3, 4).
- [ ] Detekt clean (`./gradlew detekt`).
- [ ] Lint clean (`./gradlew lintDebug`).
- [ ] All existing `:home` unit tests pass.
- [ ] All new tests in `SectionsParallelLoadTest.kt` pass.
- [ ] App builds (`assemblePlaystoreDebug`) and launches without regression on a connected device.

## Locked-In Decisions

1. **Decision A:** **A1 — callback-only, minimal diff.** No coroutine migration, no `kotlinx-coroutines-rx3` dep.
2. **Decision B:** **B1 — drop `isSectionLoading` entirely, no replacement state.**
3. **Dependent sections:** **All 30 sections treated as independent.**
4. **Remote-config kill switch:** **None.** Ship unconditionally.

## Change Log

| Date | Time | Person | Change |
|------|------|--------|--------|
| 2026-04-28 | initial | zeeshan@wego.com | Plan created. |
| 2026-04-28 | approved | zeeshan@wego.com | Decisions locked: A1 + B1, all-independent, no kill switch. |
| 2026-04-28 | code | zeeshan@wego.com | Implemented A1 + B1. Net diff in `SectionsViewModel.kt` is small (deletions plus a derived getter, a single `AtomicInteger` field, and a `checkAllSectionsCompleted` helper). External read of `viewModel.isSectionLoading` in `BaseSectionFragment.kt:270` preserved by exposing it as a derived property over the new counter. Re-entrancy guard added to `loadData()` so scroll-listener calls remain idempotent. Tests added to existing `SectionssViewmodelTest.kt` instead of new file (avoids duplicating ~80 lines of MockK setup). 20/20 home VM tests pass; detekt clean. |
| 2026-04-28 | review-fix | zeeshan@wego.com | Code-reviewer flagged 1 critical + 2 major bugs around side-effect section types (`HOME_APP_UPDATE`, `SIGN_IN_BANNER`, `HOTEL_UPSELLING_BANNER`). Their `isSectionAllowed` paths trigger sub-loads that produce their own terminal callbacks, so the new outer `onSectionSkip()` was double-counting. Fixed in two parts: **(A)** `loadData` else-branch skips `onSectionSkip` for section types in the new `sideEffectSectionTypes` set; **(B)** every side-effect chain now fires exactly one terminal callback in all paths — `loadLoginSection` logged-in path adds `onSectionSkip()`, `loadUpdateAppSection` HMS / no-update / failure paths added respective terminals, `getHotelDiscountSection` flag-off path adds `onSectionSkip()`. 3 new regression tests in `SectionssViewmodelTest.kt` cover SIGN_IN_BANNER (logged-in + not-logged-in) and HOTEL_UPSELLING_BANNER (flag-off). |
