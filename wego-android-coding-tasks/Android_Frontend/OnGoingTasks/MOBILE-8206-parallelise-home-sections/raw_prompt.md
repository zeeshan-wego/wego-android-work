# Parallelise independent home screen sections to reduce TTI

**Jira Ticket:** https://wegomushi.atlassian.net/browse/MOBILE-8206
**Type:** Task
**Status:** To Do
**Project:** Mobile (MOBILE)
**Assignee:** Zeeshan Arif (zeeshan@wego.com)
**Platform:** Android

## Description

### Background

Home screen sections currently load **strictly sequentially** in `SectionsViewModel`. The `isSectionLoading` flag at `home/src/main/java/com/wego/android/home/viewmodel/SectionsViewModel.kt:1446` blocks `loadData()` from advancing to the next section until the previous one calls `onSectionSuccess` / `onSectionError` / `onSectionSkip`. With ~10 home sections (flights search, hotels search, weekend getaway, stories, deals, recent searches, etc.) each issuing its own network call, the user sees sections populate one-at-a-time.

Even at a modest 200 ms per section, that is **2+ seconds of stalled below-the-fold rendering** on cold start that we currently spend serially.

### Proposed change

Split `sectionsToLoad` into two groups inside `SectionsViewModel`:

* **Independent sections** — no shared state, no ordering requirement (most home sections fall here). Launch concurrently in `viewModelScope`.
* **Dependent sections** — anything that consumes a prior section's result (e.g. recent-search-derived offers). Keep the existing serial pipeline for these.

Use a single `viewModelScope.launch` per independent section with `Dispatchers.IO`, collect results back to the main thread via `StateFlow` / `LiveData` as they arrive, and update the adapter incrementally (DiffUtil already handles this). Replace `isSectionLoading` with per-section state so independents do not contend on a shared boolean.

### Out of scope

* Section ordering in the final UI list — must remain stable; only the _load_ runs in parallel, not the rendering position.
* RxJava → coroutines migration for sections that still use `Single` / `Observable` (e.g. weekend getaway, booking history). Those can continue using Rx but should be launched concurrently rather than chained.
* Splash sync block, RemoteConfig fetch caching, prefs → DataStore — tracked separately.

## Acceptance Criteria

* Independent home sections kick off in parallel rather than waiting on each other.
* No regression in section ordering, click handlers, or analytics events.
* Cold-start home TTI improves on a mid-tier device — measure with Firebase Performance / `am start -W` before and after.
* Existing unit tests pass; add coverage for parallel-load completion ordering.

## References

* `home/src/main/java/com/wego/android/home/viewmodel/SectionsViewModel.kt:902` (`startLoadingData`)
* `home/src/main/java/com/wego/android/home/viewmodel/SectionsViewModel.kt:1424` (`loadData`)
* `home/src/main/java/com/wego/android/home/viewmodel/SectionsViewModel.kt:1560` (`loadSection`)
* `home/src/main/java/com/wego/android/home/features/home/view/HomeFragment.kt:278` (caller)

---
*Fetched from Jira on 2026-04-28*
