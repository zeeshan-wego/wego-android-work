# Audit and fix JaCoCo coverage script — close 3 silent gaps, drop 96 false positives

**Related Ticket:** _(none — code-quality cleanup; ticket can be assigned post-merge if desired)_

## Context

`tools/script-jacoco.gradle` is the shared coverage configuration the project's PR pipeline reads. The team's release-PR comment (`scripts/post_pr_coverage.py`, format_overall_coverage_comment) sums every `<sourcefile>` in `build/reports/jacoco/aggregate/coverage.xml` to compute LINE and BRANCH coverage. A fresh data-driven audit of that XML against the current source tree surfaced three classes of issue.

**1. False positives leaking INTO the report (65 files).** Despite the script's ~970-line exclude list, untestable code was still appearing as 0%-covered noise:
- 9 Activities/Fragments/Adapters/Screens (e.g. `FlyToAnywhereDestinationListActivity`, `FindBookingScreen`, `BoWFlightPriceBreakdownFragment`) escaped the broad `**/*Activity.class`/`**/*Fragment.class` patterns due to their bytecode landing in unusual package paths.
- 16 custom view classes — most importantly all 5 Wego Design System `W*View` files (`WBadgeView`, `WCheckboxView`, `WSegmentedControlView`, `WStepperView`, `WToggleView`) plus map view subclasses (`HotelDetailsMapView`, `HotelSearchResultsMapView`, `CountryDestinationPageMapView`).
- 40 Dagger DI classes living under `presentation/di/**` (e.g. `airlinesearchform/presentation/di/AppModule.kt`, `countrydestinationpages/presentation/di/RepositoryModule.kt`). The script only excluded `**/di/modules/**` — the actual DI layout in this codebase puts modules under `**/presentation/di/`.
- 41 Kotlin standard-library synthetic source names (`Comparisons.kt`, `Emitters.kt`, `LazyDsl.kt`, `CoroutineExceptionHandler.kt`, `SafeCollector.common.kt`, `Transition.kt`). These have no `.class` files — the Kotlin compiler inlines stdlib bytecode and JaCoCo attributes coverage to the original source name. They cannot be filtered by class-file globs; they have to be stripped at the XML post-processing step.

**2. Stale exclusion patterns (~18 dead).** Exclude entries pointing at classes/directories that no longer exist:
- `**/*BottomSheetDialogFragment.class`, `**/NonScrollableRecyclerView.class`, `**/*Navigator.class`, `**/FirebasePushTokenCallback.class` — classes deleted/renamed.
- `**/flights/**/component/**`, `**/flights/**/components/**`, `**/hotels/**/component/**`, `**/multicity/**/component/**`, `**/home/features/shopcash/**`, `**/home/features/**/presenter/**` — directories no longer exist.
- 1 stale `sourceFileFilter` entry: `**/CalendarFlightsViewActivityV1.java`.

**3. `onboardingflow` module's 2 tests producing zero coverage data.** The module's `build.gradle` was missing `apply plugin: 'jacoco'` and `testCoverageEnabled true`. Its 2 unit tests (`OnBoardingViewModelTest`, `OnBoardingVariantAssignmentUtilsTest`) ran successfully but never wrote a `.exec` file, so the aggregate report dropped the module entirely. A custom `audit-test-execution.py` script (cross-correlated test files vs `.exec` file presence per module) flagged this.

A fourth issue surfaced **during** the empirical re-run, after applying the first cut of the fix:

**4. Two patterns were inert because their globs targeted directory names, not declared package paths.** `**/wegodesignsystem/**/*.class` never matches the design system files at `com/wego/android/designsystem/W*.class` — the directory is `wegodesignsystem/`, but the package declaration is `com.wego.android.designsystem`, and JaCoCo's class-file matching follows the package. Same pattern for `**/wegowear/**/*.class` (files declare `com.wego.android.*`, not `com.wego.android.wegowear.*`). Both replaced with package-path-correct globs.

## Approach

Align the exclude lists with the actual codebase, by package path, not by directory name; route Kotlin stdlib synthetics to the post-processor that can actually reach them; remove demonstrably stale entries; wire Jacoco into the `onboardingflow` module.

### Changes to `tools/script-jacoco.gradle`

```diff
 // Section 4: DEPENDENCY INJECTION
+'**/presentation/di/**/*.class'
+'**/data/di/**/*.class'
+'**/domain/di/**/*.class'
+'**/baselineprofile/**/*.class'
+'**/ShapeWear.class', '**/ShapeWear$*.class'
+'**/AspectRatioImageview.class', '**/AspectRatioImageview$*.class'

 // Section 7: CUSTOM UI VIEWS — replace inert wegodesignsystem glob with package path
-'**/wegodesignsystem/**/*.class'   ← never matched (directory, not package)
+'**/com/wego/android/designsystem/**/*.class'
+'**/com/wego/android/component/**/*.class'
+'**/HotelDetailsMapView.class', '**/HotelDetailsMapView$*.class'
+'**/HotelSearchResultsMapView.class', '**/HotelSearchResultsMapView$*.class'
+'**/CountryDestinationPageMapView.class', '**/CountryDestinationPageMapView$*.class'

 // Section 12: HOME — pluralize *Util to also catch *Utils
+'**/home/util/*Utils.class', '**/home/util/*Utils$*.class'

 // Stale removals (entries that match nothing in the current tree)
-'**/*BottomSheetDialogFragment.class', '**/*BottomSheetDialogFragment$*.class'
-'**/NonScrollableRecyclerView.class', '**/NonScrollableRecyclerView$*.class'
-'**/FirebasePushTokenCallback.class', '**/FirebasePushTokenCallback$*.class'
-'**/*Navigator.class', '**/*Navigator$*.class'
-'**/flights/**/component/**/*.class', '**/flights/**/components/**/*.class'
-'**/hotels/**/component/**/*.class'
-'**/multicity/**/component/**/*.class'
-'**/home/features/shopcash/*Banner*.class', '**/home/features/shopcash/*Banner*$*.class'
-'**/home/features/**/presenter/*Presenter.class', '**/home/features/**/presenter/*Presenter$*.class'
-'**/home/features/myFlights/FlightBookingCardKt.class', '**/home/features/myFlights/FlightBookingCardKt$*.class'

 // sourceFileFilter
-'**/CalendarFlightsViewActivityV1.java'

 // removeExcludedSourceFilesFromXml — Kotlin stdlib synthetics (no .class files)
+'Comparisons\\.kt'
+'Emitters\\.kt'
+'SafeCollector\\.common\\.kt'
+'LazyDsl\\.kt'
+'CoroutineExceptionHandler\\.kt'
+'Transition\\.kt'
```

### Changes to `onboardingflow/build.gradle`

```diff
 apply plugin: 'com.android.library'
 apply plugin: 'kotlin-android'
+apply plugin: 'jacoco'
 ...
 buildTypes {
     debug {
         signingConfig signingConfigs.release
+        testCoverageEnabled true
     }
```

### What's NOT in scope

- **2 source files have no `package` declaration** (`BowFlightPassengerSelVm.kt`, `MiniAppActivityWithIntercept.kt`). Documented as a code-quality follow-up; not a Jacoco issue. They land in the JVM default package, which is a code smell independent of coverage.
- **9 test files are entirely commented out** (every `@Test` line is `// @Test`) — pre-existing dead code in `wegoapk/`, `flights/`. Should be deleted or resurrected in a separate cleanup PR.
- **8 test files have a class name that doesn't match the filename** (e.g. `ContactUsCustomSectionConfigTest.kt` declares `class ContactUsCustomSectionConfigV2Test`). The tests run fine — this is a rename hygiene cleanup.
- **No new tests are written.** The audit measures and cleans the existing report; net coverage gain comes only from `onboardingflow`'s 2 tests now being recognized.
- **No CI threshold change.** The release-PR comment script and SonarQube continue to read the same XML path.

## Files changed

| File | Δ |
|------|---|
| `tools/script-jacoco.gradle` | +51 / −22 |
| `onboardingflow/build.gradle` | +2 / 0 |

## Testing

### Empirical verification — fresh full test suite + report regen

```bash
./gradlew testPlaystoreDebugUnitTest                 # ✅ BUILD SUCCESSFUL in 4m 23s
./gradlew aggregateCoverageReport --rerun-tasks       # ✅ BUILD SUCCESSFUL
./gradlew aggregateCoverageReportByModule --rerun-tasks  # ✅ BUILD SUCCESSFUL
```

| Metric | PR #2040 baseline (Apr 24, build #10663) | This PR |
|---|---:|---:|
| Files in `coverage.xml` | 1,588 | **1,492** (−96 false positives) |
| **LINE coverage** | **22.63%** (20,753 / 91,723) | **23.41%** (20,740 / 88,598) |
| **BRANCH coverage** | **12.75%** (7,271 / 57,029) | **13.28%** (7,271 / 54,736) |
| INSTRUCTION (byModule) | — | 24.28% (128,661 / 529,986) |
| CLASS (byModule) | — | 50.63% (1,536 / 3,034) |
| METHOD (byModule) | — | 38.06% (7,898 / 20,754) |
| Modules with tests but no exec output | 1 (`onboardingflow`) | **0** |
| Active test methods | 8,609 | **8,611** (+2 from `onboardingflow`) |
| Test pass rate | 100% | 100% (0 failed, 0 errored, 0 skipped) |

### Reproducible audit pipeline

The audit was driven by a set of Python/bash scripts that anyone can re-run to verify (lives outside this repo, in the task folder):

```
build-source-index.py     → maps every src/main/java/*.kt|.java to its declared package
parse-coverage-xml.py     → extracts the <sourcefile> set from coverage.xml
classify-misses.py        → diffs source vs report; classifies each "missing" file against the 3 exclusion layers
find-stale-patterns.py    → flags fileFilter / sourceFileFilter entries that match nothing
audit-test-execution.py   → cross-correlates per-module test count vs .exec file presence
sonar-style-coverage.py   → simulates SonarQube's coverage.exclusions overlay
```

After applying the diff, `classify-misses.py` reports:
```
EXCLUDED_BY_FILEFILTER: 1315
EXCLUDED_BY_XML_POSTPROCESS: 5
UNEXPLAINED: 2     # the 2 missing-package-declaration files (out-of-scope follow-up)
```

### Local gates

```bash
./gradlew help --no-daemon                 # ✅ script parses cleanly, no Groovy syntax errors
./gradlew :onboardingflow:testPlaystoreDebugUnitTest --rerun-tasks   # ✅ 2 tests, exec file produced
```

## Test plan

- [ ] CI: confirm `aggregateCoverageReport` task succeeds on the build runner.
- [ ] CI: confirm `post_pr_coverage.py` posts a release-PR comment with **23%+ LINE coverage** (up from 22.63% on PR #2040).
- [ ] Verify `onboardingflow` module appears in the per-module HTML report at `build/reports/jacoco/aggregateByModule/html/onboardingflow/`.
- [ ] Spot-check that none of the previously-leaking files appear in the new HTML report:
  - `airlinesearchform/presentation/di/AppModule.kt`
  - `wegodesignsystem/.../WBadgeView.kt`
  - `wegoapk/.../HotelSearchResultsMapView.java`
  - `*/Comparisons.kt` (Kotlin stdlib synthetic)
- [ ] Verify SonarQube's coverage trendline reflects the +0.78 pts bump after the next push to develop.
