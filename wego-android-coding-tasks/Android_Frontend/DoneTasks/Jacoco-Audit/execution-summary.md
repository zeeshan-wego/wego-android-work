# Execution Summary — Jacoco-Audit

## Current State
- **Phase:** ARCHIVED (5) — task complete, folder moved to DoneTasks on 2026-04-30
- **Branch:** `chore/jacoco-script-audit` (renamed from `feature/mobile-tbd-jacoco-audit`)
- **Commit:** `e8012e9404` on origin
- **PR:** https://github.com/wego/wego-android-n/pull/2077 (Draft — awaiting Ready for Review)
- **Final empirical numbers (vs PR #2040 baseline, build #10663):**
  - Files in coverage.xml: 1,588 → 1,492 (−96 false positives)
  - LINE coverage: 22.63% → 23.41% (+0.78 pts)
  - BRANCH coverage: 12.75% → 13.28% (+0.53 pts)
  - 21 modules with active tests, 0 MISSING_EXEC, 8,611 active tests pass

## Q&A Log
- Q: Scope — all modules or specific? → A: All modules
- Q: Where is the Jacoco script? → A: `tools/script-jacoco.gradle` (confirmed)
- Q: Audit only, fix only, or both? → A: (c) Both — audit first, then decide what to fix
- Q: Related to MOBILE-8162? → A: Independent
- Q: Ticket ID? → A: TBD for now (ticket-late approach, no ticket assigned)

## Key Findings From Initial Read of script-jacoco.gradle
- Script has THREE exclusion layers:
  1. `fileFilter` (~970 lines, 14 categories) — applied to all `JacocoReport` tasks via class file globs
  2. `sourceFileFilter` (~110 lines) — applied only by `aggregateCoverageReportByModule` (Ant-based) on `.kt`/`.java` source globs
  3. `removeExcludedSourceFilesFromXml(...)` — post-processing that strips 5 specific Compose UI files from the final XML
- Two report tasks: `aggregateCoverageReport` (single tree) and `aggregateCoverageReportByModule` (grouped, uses Ant + jacoco 0.8.11)
- Test runner: `runTestsForAllModules` calls `./gradlew {module}:testDebugUnitTest` for every subproject
- Default project flavor: playstoreDebug

## Follow-ups (out of scope for this PR — separate cleanup)
- Add `package` declarations to the 2 files that landed in JVM default package: `BowFlightPassengerSelVm.kt`, `MiniAppActivityWithIntercept.kt`
- Delete or resurrect 9 entirely-commented-out test files in `wegoapk/`, `flights/`
- Rename the 8 test files whose declared class name doesn't match the filename (e.g. `ContactUsCustomSectionConfigTest.kt` declares `class ContactUsCustomSectionConfigV2Test`)
- Audit-tool reusability: the 6 Python/bash scripts in `scripts/` are reproducible — could be promoted into a CI quality gate ("fail PR if UNEXPLAINED count > 0 in classify-misses.tsv")
