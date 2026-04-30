# JaCoCo Coverage Script Audit — Fix False Positives, Stale Excludes, and a Silent Module Drop

## Problem

The Android project's JaCoCo coverage configuration in `tools/script-jacoco.gradle` had drifted over time, producing a coverage report that was misleading in three ways:

1. **65 untestable files were leaking INTO the coverage report**, dragging the percentage down without contributing meaningful signal: 9 Activities/Fragments/Adapters/Screens, 16 custom view classes (including all 5 `Wego Design System` `W*View` components), 40 Dagger modules/components/factories living under `presentation/di/` (the script only excluded `**/di/modules/**`), plus 41 Kotlin standard-library synthetic source names (`Comparisons.kt`, `Emitters.kt`, `LazyDsl.kt`, `CoroutineExceptionHandler.kt`, `SafeCollector.common.kt`, `Transition.kt`) inlined by the Kotlin compiler.

2. **~18 `fileFilter` patterns were silently dead** — pointing at classes that had been renamed or deleted, or directories that no longer exist. Examples: `**/*BottomSheetDialogFragment.class`, `**/NonScrollableRecyclerView.class`, `**/*Navigator.class`, `**/FirebasePushTokenCallback.class`, `**/flights/**/component/**`, `**/hotels/**/component/**`, `**/multicity/**/component/**`, `**/home/features/shopcash/**`, `**/home/features/**/presenter/**`. Plus 1 stale entry in `sourceFileFilter` (`**/CalendarFlightsViewActivityV1.java`).

3. **The `onboardingflow` module's 2 unit tests were silently producing zero coverage data.** The module's `build.gradle` was missing `apply plugin: 'jacoco'` and `testCoverageEnabled true`, so its tests ran successfully but never wrote a `.exec` file — the aggregate report was dropping that module entirely.

A fourth issue surfaced during the fix: **two glob patterns were inert because they targeted directory names that don't match the declared package paths** (`**/wegodesignsystem/**` for files declaring `com.wego.android.designsystem`, and `**/wegowear/**` for files declaring `com.wego.android.*`). The script looked like it was excluding those, but Gradle's class-file matching follows package paths, not the source-tree directory layout.

## Solution

Align `tools/script-jacoco.gradle` and `onboardingflow/build.gradle` with the actual codebase:

- **Tighten exclude lists** to actually catch the false positives by package path: `**/com/wego/android/designsystem/**`, `**/com/wego/android/component/**`, `**/presentation/di/**`, `**/data/di/**`, `**/domain/di/**`, plus explicit excludes for the three map-view subclasses and two `wegowear/` files (`ShapeWear`, `AspectRatioImageview`) whose packages don't reflect the module name.
- **Move Kotlin stdlib synthetic source names from `fileFilter` to `removeExcludedSourceFilesFromXml`'s `excludedFilePatterns`** — they have no `.class` files to filter (they're inlined bytecode debug info), so they have to be stripped at the XML post-processing step.
- **Pluralize the home-util pattern** from `**/home/util/*Util.class` to also cover `*Utils.class` (catches `NotificationsUtils.kt`).
- **Add module-level excludes** for `**/baselineprofile/**/*.class` (instrumented benchmarks only) and the two leaked `wegowear` files.
- **Remove ~18 stale patterns** that no longer match anything in the source tree.
- **Wire up Jacoco in `onboardingflow/build.gradle`** with `apply plugin: 'jacoco'` and `testCoverageEnabled true` so the module's 2 tests start contributing coverage data.

## Benefits

- **Cleaner, more honest coverage signal.** All 785 unit tests across 21 modules now contribute coverage data (previously 783 — `onboardingflow`'s 2 tests were silently dropped).
- **Reported LINE coverage rises from 22.63% to 23.41%** (+0.78 pts) and **BRANCH from 12.75% to 13.28%** (+0.53 pts) — same numerator, smaller and more honest denominator.
- **The aggregate `coverage.xml` shrinks by ~6%** (1,588 → 1,492 sourcefiles) by dropping 96 untestable files. The remaining 1,492 files genuinely represent the testable surface area.
- **Easier maintenance going forward** — ~18 dead patterns gone, no more silent `**/wegodesignsystem/**` / `**/wegowear/**` no-ops to mislead future contributors.
- **Three test-pipeline metrics improve:**
  - `aggregateCoverageReport` (CI's `post_pr_coverage.py`): **+0.78 pts LINE** on release-PR comments.
  - `aggregateCoverageReportByModule`: same numbers; per-module breakdown is now an accurate diagnostic.
  - SonarQube: same `coverage.xml` feeds Sonar; the Sonar dashboard reflects the same improvement.

## Acceptance Criteria

- [x] All 21 modules with active tests produce `.exec` files (`audit-test-execution.py` reports 0 MISSING_EXEC).
- [x] All 8,611 active test methods across 775 test classes pass and contribute to the aggregate report.
- [x] LINE coverage in `build/reports/jacoco/aggregate/coverage.xml` ≥ 23.4% (was 22.63%).
- [x] No untestable file slips back into the report — verified empirically: `wegodesignsystem` (0 entries), Kotlin stdlib synthetics (0 entries), `presentation/di/**` (0 entries).
- [x] `./gradlew aggregateCoverageReport --rerun-tasks` and `./gradlew aggregateCoverageReportByModule --rerun-tasks` both produce reports cleanly with no Groovy syntax errors.
- [x] Two follow-up code-quality issues documented but **out of scope** for this PR:
  - 2 source files (`BowFlightPassengerSelVm.kt`, `MiniAppActivityWithIntercept.kt`) are missing `package` declarations.
  - 8 test source files have classes whose names don't match the filename (and 9 test files are entirely commented out as dead code).
