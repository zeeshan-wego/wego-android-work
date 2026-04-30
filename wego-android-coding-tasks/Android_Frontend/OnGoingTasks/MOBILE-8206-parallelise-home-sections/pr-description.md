# [MOBILE-8206] Parallelise independent home screen sections to reduce TTI

**Related Ticket:** [MOBILE-8206](https://wegomushi.atlassian.net/browse/MOBILE-8206)

## Context

`SectionsViewModel.loadData()` walked `sectionsToLoad` one section at a time. A single `var isSectionLoading: Boolean` gate (line 1446) blocked the queue from advancing until the current section's terminal callback (`onSectionSuccess` / `onSectionError` / `onSectionSkip`) flipped the flag back to `false`. With ~30 home sections issuing their own network calls, the user saw sections populate serially — multi-second stalls below the fold even at modest per-section latency.

Investigation showed the network calls themselves already run on Rx IO threads (`subscribeOn(Schedulers.io())`) — the bottleneck was purely the queue gate, not the per-section async style. Cross-section data dependencies were checked and none found in the current code.

## Approach

Remove the queue gate. `loadData()` now iterates `sectionsToLoad` once and fires every allowed section via `loadSection()` in a single pass; the existing per-loader Rx subscriptions race to completion concurrently.

- `var isSectionLoading: Boolean` → read-only `val` derived from a new `pendingSectionsCount: AtomicInteger` (preserves `BaseSectionFragment.kt:270` scroll-listener read).
- `var sectionIndexToLoad: Int` and `getSectionToLoad()` deleted — no cursor with a one-pass dispatcher.
- New `checkAllSectionsCompleted()` helper called from each terminal callback. When the counter reaches zero and `items` has no real section, surface the empty-state UI (preserves the pre-parallel `noSectionsFound()` behaviour that previously fired at cursor end).
- `loadData()` keeps its early-return guards and adds a re-entrancy guard `if (pendingSectionsCount.get() > 0) return` — so scroll-driven `BaseSectionFragment.loadMore()` re-calls remain idempotent.
- Terminal callbacks (`onSectionSuccess`, `onSectionError`, `onSectionSkip`) no longer flip a global flag and recurse into `loadData()`; they call `checkAllSectionsCompleted()` only.

`checkOrderAndInsert(viewType, …)` — which places each section at its `ViewType`-ordinal index in `items` — is unchanged. Display order stays stable regardless of which section completes first.

### What's not in scope

- No coroutine migration: per-loader internals (Rx `Single`/`Observable`, callback-based loaders, synchronous loaders) are untouched. The `kotlinx-coroutines-rx3` dep was deliberately not added — it was unnecessary once the gate was the only thing holding back parallelism.
- No per-section state map. The Phase-1 conversation flagged "per-section state replacement" as a goal, but the existing `isSectionLoading` was only consumed by the queue gate (and two log lines). With no UI consumer for richer per-section state, a `Map<String, SectionLoadState>` would have been dead code.
- No remote-config kill switch. Behaviour change is conservative (load order/contract preserved); rollback path is `git revert`.
- TTI benchmarking is owned by QA per the ticket.

## Files changed

| File | Δ |
|------|---|
| `home/src/main/java/com/wego/android/home/viewmodel/SectionsViewModel.kt` | +48 / -68 (net **-20** lines) |
| `home/src/test/java/com/wego/android/home/viewmodel/SectionssViewmodelTest.kt` | +172 (11 new tests + 4 reflection helpers) |

## Testing

### New unit tests (`SectionssViewmodelTest.kt`, region "Parallel Section Loading (MOBILE-8206)")

| # | Test | Asserts |
|---|------|---------|
| 1 | `isSectionLoading is false when pendingSectionsCount is zero` | derived getter |
| 2 | `isSectionLoading is true when pendingSectionsCount is positive` | derived getter |
| 3 | `onSectionSuccess decrements pendingSectionsCount` | terminal callback updates counter |
| 4 | `onSectionError decrements pendingSectionsCount` | terminal callback updates counter |
| 5 | `onSectionSkip decrements pendingSectionsCount` | terminal callback updates counter |
| 6 | `loadData no-op when lazyLoadingStarted is false` | early-return guard preserved |
| 7 | `loadData no-op when sectionsToLoad is empty` | early-return guard preserved |
| 8 | `loadData does not redispatch when round already in flight` | re-entrancy guard (the old `isSectionLoading` gate's job) |
| 9 | `loadData fans out all sections in single pass and counter drains to zero` | parallel dispatch + counter mechanics |
| 10 | `terminal callbacks insert in display order regardless of arrival order` | **the key invariant — perf without reordering UI** |
| 11 | `one section error does not block sibling success` | per-section failure isolation |

### Local gates run

```
./gradlew :home:compilePlaystoreDebugKotlin           # ✅ BUILD SUCCESSFUL
./gradlew detekt                                      # ✅ BUILD SUCCESSFUL (root, maxIssues=0)
./gradlew :home:lintAnalyzePlaystoreDebug             # ✅ BUILD SUCCESSFUL
./gradlew :home:testPlaystoreDebugUnitTest --rerun-tasks  # ✅ 96 test classes, zero failures, zero errors
```

`SectionssViewmodelTest`: **20 tests, 0 failures** (9 pre-existing + 11 new).

## Test plan

- [ ] QA: cold-start home TTI on a mid-tier device, before vs after this change. Use Firebase Performance / `am start -W`.
- [ ] QA: visual smoke — scroll the full home feed and confirm every section type still renders, in the same order as before.
- [ ] QA: kill-switch flip on a flaky network — confirm the empty-state / `noNetwork()` banner still appears when no section can load.
- [ ] QA: simulate a single section failing (e.g. block one specific endpoint) and confirm sibling sections still render.

## Risks & rollback

**Risk: hidden cross-section data dependency I missed.** Mitigation: all 11 new tests pass, `checkOrderAndInsert` is unchanged, and the Explore audit of the 30+ loaders found no shared state reads beyond city/locale/network state set externally.

**Risk: `ObservableList` writes from concurrent loaders.** Mitigation: today every Rx loader hops to `AndroidSchedulers.mainThread()` before invoking the success callback — that contract is preserved. No changes to Rx internals.

**Rollback:** `git revert <merge SHA>`. The change is local to `SectionsViewModel.kt` and one test file.

## Checklist

- [x] Detekt passes
- [x] Lint passes
- [x] Existing unit tests pass
- [x] New unit tests added for the changed behaviour
- [x] No public API change beyond `var isSectionLoading` → `val isSectionLoading` (the only external read in `BaseSectionFragment.kt:270` is preserved)
- [x] No documentation updates required (no API/DB/contract surface changed)
