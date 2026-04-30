# MOBILE-8206 — Parallelise independent home screen sections to reduce TTI

**Jira:** https://wegomushi.atlassian.net/browse/MOBILE-8206
**Platform:** Android
**Module:** `home`

## Problem

Home screen sections in `SectionsViewModel` (`home/src/main/java/com/wego/android/home/viewmodel/SectionsViewModel.kt`) load **strictly sequentially**. A single `isSectionLoading` boolean (line 1446) gates `loadData()` so the queue cannot advance to the next section until the current one fires `onSectionSuccess` / `onSectionError` / `onSectionSkip` (which flip the flag back to `false` at lines 1909 / 1919 / 1929).

There are **30+ section loaders** dispatched from `loadSection()` (lines 1560–1671). Each one issues its own network call (mostly RxJava `Single`/callback, some Firebase config, a few synchronous JSON parses). Even at ~200 ms per section, the user sees stalled below-the-fold rendering for ≥2 s on cold start.

## Goal

Replace the single-flight `isSectionLoading` gate with **per-section state**. Fan out **independent sections** concurrently in `viewModelScope`. Keep the existing serial path for any **dependent sections** (sections that consume an earlier section's output). Section render order in the UI must remain stable — only the *loads* run in parallel; placement in `items` continues to use `checkOrderAndInsert` so order is preserved regardless of completion order.

## Decisions Captured (from Q&A)

1. **Refactor scope:** **Option B — replace `isSectionLoading` entirely** with per-section state. Cleaner long-term, and the existing flag is read in 12+ sites (lines 203, 348, 374, 391, 1433, 1446, 1448, 1552, 1563, 1665, 1909, 1919, 1929) — a half-measure leaves footguns.
2. **Independent vs dependent sections:** **Derive from code in Phase 2.** The Explore pass found no hard cross-section data dependencies — all 30+ loaders use Firebase config, location state, or self-contained callback state. The ticket's "recent-search-derived offers" hint did not materialise in code (`getOffers()` reads `homeOffers` populated by its own `offerListener`, not by another section's loader). I will produce a candidate "all-independent" list in the execution plan and confirm with the user before fanning out.
3. **RxJava sections:** **Wrap in coroutines via `rxSingle`/`await`** (kotlinx-coroutines-rx3) so all per-section loaders share one launch idiom. Don't rewrite Rx call sites internally.
4. **TTI measurement:** Out of scope. **QA owns the cold-start benchmark** before/after. No `am start -W` or Firebase Performance instrumentation in this PR.
5. **Test coverage:** **Unit tests only** — `runTest` + `TestCoroutineDispatcher`. Cover: (a) independents kick off concurrently, (b) results inserted in stable display order regardless of completion order, (c) per-section error doesn't block siblings, (d) dependent sections (if any) still run serially after their dependency completes.

## In Scope

- Replace `var isSectionLoading: Boolean` with per-section status (e.g. `Map<String, SectionLoadState>` or per-section `Job`).
- Restructure `loadData()` / `loadSection()` so independents launch concurrently via `viewModelScope.launch(Dispatchers.IO)`.
- Migrate Rx-based per-section loaders' subscription glue to `kotlinx.coroutines.rx3.await` / `rxSingle` so each loader is a `suspend fun`. Internal Rx implementation in repos/use-cases stays as-is.
- Preserve the contract of `onSectionSuccess` / `onSectionError` / `onSectionSkip` semantics, but no longer use them to advance a single-flight queue.
- Preserve `checkOrderAndInsert` so UI order is stable regardless of completion order.
- Add unit tests in `home/src/test/java/.../SectionsViewModelParallelLoadTest.kt` (new file).

## Out of Scope (per ticket + Q&A)

- Rewriting Rx implementations inside repos / use-cases.
- TTI benchmarking, `am start -W` measurement, Firebase Performance instrumentation.
- Splash sync block, RemoteConfig fetch caching, prefs → DataStore.
- UI render order changes — must remain identical.
- Click handler / analytics event changes — must remain identical.
- Migration of `BaseViewModel.items: ObservableList<BaseSection>` to `StateFlow` — out of scope; current adapter integration via `ObservableList` stays.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| 30+ loaders refactored at once = high blast radius | Per-section state keeps each loader independently testable; unit tests for ordering; QA cycle before merge |
| Rx → coroutine glue in `getXxxSection()` introduces lifecycle bugs | Use `viewModelScope` (auto-cancels on `onCleared`); `rxSingle`/`await` propagates cancellation |
| `ObservableList<BaseSection>` not thread-safe under concurrent inserts | All `checkOrderAndInsert` calls must marshal back to main thread (`withContext(Dispatchers.Main)` or post via `MutableLiveData.postValue`) |
| Hidden cross-section dependency I missed in Phase 2 | Surface candidate-independent list in execution plan and ask user to confirm before coding |
| Existing tests rely on serial ordering of section loads | None found in current repo (no `SectionsViewModelTest.kt`); new tests will assert insertion-order, not completion-order |

## Acceptance Criteria

- [ ] `isSectionLoading: Boolean` removed from `SectionsViewModel`; per-section state in its place.
- [ ] Independent sections (full list confirmed in execution plan) launch concurrently in `viewModelScope` from `startLoadingData()` / `loadData()`.
- [ ] Dependent sections (if any are confirmed in Phase 2) still run after their dependency resolves.
- [ ] UI render order in `items` is identical to current behaviour for any given response set.
- [ ] One section's error / skip does not block siblings.
- [ ] No regression in click handlers or analytics events.
- [ ] Detekt passes (`./gradlew detekt`, maxIssues=0).
- [ ] Lint passes (`./gradlew lintDebug`).
- [ ] Existing unit tests pass (`./gradlew :home:testPlaystoreDebugUnitTest --rerun-tasks`).
- [ ] New tests cover concurrent fan-out + stable ordering + per-section error isolation.

## Applicable Rules

These coding rules are loaded into the conversation as `alwaysApply: true` and are mandatory for this task. Phase-3 implementation must read each one before writing code:

- `docs/ai-rules/mvvm-rules.md` — **always-apply.** ViewModel responsibilities, `viewModelScope` for coroutines, `LiveData`/`StateFlow` thread rules. Directly relevant: we're refactoring a ViewModel and changing its async model.
- `docs/ai-rules/critical-thinking.md` — **always-apply.** Pause before hidden cross-section dependencies surface; ask the user before coding around an unclear case (especially if a "dependent section" turns up in Phase 2 that the Explore pass missed).
- `docs/ai-rules/coderabbit-compliance.md` — **always-apply.** Concurrency, lifecycle, thread-safety. Directly relevant: introducing coroutine fan-out + writing to `ObservableList` from background dispatchers.
- `docs/ai-rules/performance-optimization.md` — direct fit. The whole task is a perf optimisation; preserve logic for every loader; don't drop or reorder side effects.
- `docs/ai-rules/android-best-practices.md` — coroutine + lifecycle patterns.
- `docs/ai-rules/detekt-compliance.md` — strict mode, `maxIssues=0`. Watch line length (120), method length (60), class length (600 — `SectionsViewModel.kt` is already 4156 lines and over-budget; a refactor must not push it further. Likely need to extract a helper into a new file, e.g. `SectionLoadOrchestrator.kt`).

**Note on file size:** `SectionsViewModel.kt` is 4156 lines — already 7× the detekt class-length budget. Existing detekt baselines may grandfather this in, but the refactor should *not increase* its size. Plan to extract the orchestration logic into a separate file/class.
