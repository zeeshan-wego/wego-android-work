# Jacoco Coverage Script Audit

**Status:** Independent audit (not tied to a specific Jira ticket — TBD for now)
**Platform:** Android_Frontend
**Scope:** All modules

## Goal

Audit `tools/script-jacoco.gradle` to verify two things are correct:

1. **All test files in the codebase are getting picked up** by the Jacoco execution and contributing to the coverage report.
2. **All source files that DO NOT appear in the coverage report are genuinely non-testable** — i.e., the `fileFilter` / `sourceFileFilter` exclusion lists in the script are correctly classifying files. No testable business logic should be silently excluded; no truly-untestable code should be sneaking into the report.

## Why This Matters

- A wrongly-excluded testable class artificially inflates coverage by hiding gaps.
- A wrongly-included non-testable class drags coverage down for no reason and pollutes the report.
- Today's exclude list in `tools/script-jacoco.gradle` is large (~970 lines, 14 categorized sections). It's grown organically and may have drifted — patterns may now match classes they weren't meant to, and new testable code may be falling under a broad pattern.

## Approach (from raw prompt)

The user explicitly described the audit method:

> "Create a complete list of test files within the code, then generate a report using the Jacoco script. Check which files are in the report and which are not. Then audit the Jacoco exclude list and keep specific files in test coverage if some paths in the exclude list are causing issues. First check that path for files which should not be part of the report."

Translated to concrete steps:

1. **Enumerate** all `*Test.kt` / `*Test.java` files across all 32 modules → this is the test inventory.
2. **Run** the Jacoco script (`runTestsForAllModules` then `aggregateCoverageReport` / `aggregateCoverageReportByModule`).
3. **Parse** the resulting Jacoco report (HTML/XML) to get the list of source files that ARE in the coverage report.
4. **Diff** the universe of source files vs. what's in the report → produce three lists:
   - **In report (covered or partially covered)** — already audited, safe.
   - **Not in report — correctly excluded** — these are non-testable (Activities, Fragments, generated code, DI modules, custom Views, etc.). Validate that exclusion is justified.
   - **Not in report — wrongly excluded** — testable classes (ViewModels, use cases, mappers, business logic) that got swept up by an over-broad pattern. THESE are the bugs to fix.
5. **Audit each excluded path** in the script category-by-category. For each broad pattern (e.g., `**/home/util/*Util.class`, `**/*Service.class`, `**/bow/ui/**/*.class`), open the matching files and verify they are genuinely untestable. Flag any testable class hiding inside.
6. **Produce** a findings report listing:
   - Test inventory size + breakdown per module.
   - Coverage report inventory size.
   - Wrongly-excluded files (the priority fix list).
   - Genuinely-untestable files inside each excluded path (justification).
   - Recommended changes to `fileFilter` and `sourceFileFilter`.
7. **Optionally**, after the user reviews findings, apply fixes to `tools/script-jacoco.gradle`.

## Deliverables

**(c) Both** — audit report first, then user decides what to fix.

- `findings.md` (in this task folder) — full audit report
- Optional follow-up: actual edits to `tools/script-jacoco.gradle`

## Key Files

- **Audit target:** `tools/script-jacoco.gradle` (the only file to potentially edit)
- **Source tree under audit:** all `*/src/main/java/**/*.kt` and `*.java` across 32 modules
- **Test tree under audit:** all `*/src/test/java/**/*Test.kt` and `*Test.java`
- **Generated artifacts to inspect:** `build/reports/jacoco/aggregate/coverage.xml` (machine-readable) and `aggregateByModule/coverage.xml`

## Non-Goals

- **Not** writing new unit tests to fill coverage gaps. (That's a separate effort, and there's already `MOBILE-8162-unit-test-code-coverage-phase-3` on the team.)
- **Not** refactoring the Jacoco script's task structure / build wiring. Only auditing the exclude lists and adding/removing entries.
- **Not** tightening coverage thresholds or CI gates.

## Open Questions / Assumptions

- **Build flavor for the report run:** the script supports both `playstoreDebug` and `debug`. We'll run with `playstoreDebug` since that's the project's default flavor (matches `./gradlew :wegoapk:testPlaystoreDebugUnitTest`).
- **Source file filter scope:** `sourceFileFilter` is only used by `aggregateCoverageReportByModule` (Ant-based). `fileFilter` (class files) is used by both. Audit must cover both lists.
- **XML post-processing:** there's a `removeExcludedSourceFilesFromXml(...)` helper that strips 5 specific Compose UI files from the final XML. This is a third exclusion layer — must include in the audit.

## Applicable Rules

This is primarily an audit/research task with potential script edits. Coding rules that apply if/when we modify the script:

- **`docs/ai-rules/critical-thinking.md`** (always-apply) — for every excluded file, ask "is there genuinely no logic to test, or is this lazy?" Don't accept exclusions at face value.
- **`docs/ai-rules/coding-conventions.md`** (always-apply) — formatting rules apply if we edit the Gradle script (line length, organization).
- **`docs/ai-rules/code-review.md`** — relevant for the audit report itself (clear evidence, actionable recommendations).

No rules for DB migrations, JPA, API conventions, etc. — this task does not touch those layers.

## Definition of Done

- `findings.md` exists in task folder with:
  - Test file inventory (count + per-module breakdown)
  - Coverage report inventory (count + per-module breakdown)
  - List of files **incorrectly excluded** (top priority — testable classes hidden by exclude patterns)
  - List of files **correctly excluded** with justification (sampled, not exhaustive)
  - Concrete recommended edits to `tools/script-jacoco.gradle` (which patterns to remove/narrow/add)
- User approves findings.
- (Optional) Script edits applied + `aggregateCoverageReport` re-runs cleanly.
