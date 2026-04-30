# Execution Plan — Jacoco Coverage Script Audit

**Branch:** `feature/mobile-tbd-jacoco-audit` (will rename to include ticket ID once assigned)
**Approach:** Audit-first, fixes-on-approval. No new tests are written; no script edits without sign-off on findings.

## Execution Tracking
- **Started:** (will fill on Phase 3 kickoff)
- **Developer:** zeeshan@wego.com
- **Branch:** feature/mobile-tbd-jacoco-audit
- **Collaborators:** (none)

## Summary

Audit the three exclusion layers in `tools/script-jacoco.gradle` to find:

1. **False negatives** — testable classes (ViewModels, use cases, mappers, business logic) silently dropped from coverage by an over-broad `fileFilter` / `sourceFileFilter` pattern. **These are the bugs.**
2. **False positives** — non-testable classes that are not yet excluded and are dragging the coverage % down without adding value.
3. **Stale exclusions** — entries pointing at files that no longer exist (renamed/deleted) — dead config to clean up.

Produce `findings.md` with evidence + a recommended diff to `script-jacoco.gradle`. User approves before any edits.

## Approach (and Trade-offs)

### Chosen approach: data-driven audit using existing report + scripted diff

1. Use the existing `build/reports/jacoco/aggregate/coverage.xml` (Apr 27) as the baseline coverage inventory, since regenerating it across 32 modules takes ~30+ min.
2. Regenerate it once at the start to ensure the data is current (commit-state aligned).
3. Enumerate ALL production source files with `find` over each module's `src/main/java`.
4. Enumerate ALL test files with `find` over `src/test/java`.
5. Parse the Jacoco XML to extract every `<sourcefile>` element → "files in report".
6. **Diff** "all source files" vs "files in report" → "missing files" set.
7. **Classify** each missing file by walking the `fileFilter` / `sourceFileFilter` patterns and matching:
   - **Pattern X covers file Y, and Y is testable** → false negative (BUG, fix the pattern).
   - **Pattern X covers file Y, and Y is non-testable** → correctly excluded (justify in report).
   - **No pattern matches Y, but Y is still missing** → likely no test exists or compile-time exclusion (e.g., test classes themselves) — categorize and note.
8. For each `fileFilter` category (1-14), audit the broadest patterns by inspecting matched files and judging "is there logic here?".
9. Write `findings.md`.

**Why this approach:**
- Empirical (driven by real coverage XML), not a hand-wave reading of the script.
- Reproducible — anyone can re-run with a fresh XML.
- Surfaces the highest-impact bugs first (false negatives that hide testable code).

### Alternatives considered (rejected)

- **Regenerate report fresh from scratch every time** — too slow (`runTestsForAllModules` then aggregate ≈ 30+ min on 32 modules). Use existing report; regenerate only once at start.
- **Manually read the script top-to-bottom and reason about each pattern** — won't catch real-world drift (renames, new classes matching old patterns). Data-driven beats reasoning-from-rules here.
- **Only audit the broad patterns (`**/*Service.class`, `**/*Activity.class`, etc.)** — misses category 14 ("Misc") and the surgical exclusions like `'**/SectionsViewModel.class'`. Need full coverage of all three layers.

## Files To Change

### Implementation (Phase 3 — audit)

| File | Action | Purpose |
|------|--------|---------|
| `(task folder)/findings.md` | Create | Audit report — primary deliverable |
| `(task folder)/scripts/list-source-files.sh` | Create | Enumerate `*.kt`/`*.java` under each module's `src/main/java` |
| `(task folder)/scripts/list-test-files.sh` | Create | Enumerate `*Test.kt`/`*Test.java` under each module's `src/test/java` |
| `(task folder)/scripts/parse-coverage-xml.py` | Create | Parse aggregate `coverage.xml` → list of `<sourcefile>` entries |
| `(task folder)/scripts/diff-coverage.py` | Create | Diff source files vs coverage report; classify each miss against `fileFilter`/`sourceFileFilter` patterns |
| `(task folder)/data/all-sources.txt` | Generate | Output of list-source-files.sh |
| `(task folder)/data/all-tests.txt` | Generate | Output of list-test-files.sh |
| `(task folder)/data/in-report.txt` | Generate | Files present in coverage.xml |
| `(task folder)/data/missing-from-report.txt` | Generate | Files NOT in coverage.xml |
| `(task folder)/data/false-negatives.txt` | Generate | Testable files wrongly excluded — the BUG list |

### Implementation (Phase 3 — optional fixes, only after user approves findings)

| File | Action | Purpose |
|------|--------|---------|
| `tools/script-jacoco.gradle` | Edit | Remove/narrow over-broad patterns; remove stale entries; add justified new exclusions |

### Tests

**No new unit tests** — this is a build-script audit, not feature work. Validation is empirical:
- Regenerate the Jacoco report after script edits and verify previously-missing testable files now appear.
- Spot-check that previously-excluded UI files are still excluded.

### Documentation

| File | Action | Why |
|------|--------|-----|
| `(task folder)/findings.md` | Create | Deliverable |
| `(task folder)/ticket.md` | Create in Phase 4 | Product-level summary |
| `(task folder)/pr-description.md` | Create in Phase 4 | Technical PR doc (only if script edits land) |

No updates needed to API specs or ERD docs — task does not touch APIs or DB.

## Test Plan

For the audit phase: not applicable (no production code changes).

For optional fixes phase:
1. **Before-edit baseline:** record total instructions covered + total classes in current `coverage.xml` (header `<counter>` totals).
2. **Apply edits to `script-jacoco.gradle`.**
3. **Regenerate** with `./gradlew aggregateCoverageReport --rerun-tasks` (uses existing exec data; doesn't re-run tests).
4. **After-edit measurement:** record same totals.
5. **Validate the bug-fix list:** for each false-negative file we un-excluded, confirm it now has a `<sourcefile>` entry in the new XML.
6. **Validate non-regressions:** for sampled excluded UI files (Activities, Compose screens), confirm they are still absent from the new XML.
7. **Build sanity:** `./gradlew :wegoapk:assemblePlaystoreDebug` still succeeds.

No script-level "tests" exist in the repo for `script-jacoco.gradle`; we rely on the report diff as the validation harness.

## Database / Schema Changes

None.

## Documentation Updates Required

None on the published-docs side (API specs / ERD untouched). The audit's own `findings.md` is the artifact.

## Acceptance Criteria

- [ ] `findings.md` exists with all required sections (test inventory, source inventory, in-report inventory, false-negative list, justified exclusions, recommended script diff).
- [ ] False-negative list is concrete — each entry has: filename, module, current matching exclude pattern, brief reason it's testable.
- [ ] Recommended `script-jacoco.gradle` diff is presented as a unified diff, ready to apply or reject.
- [ ] Helper scripts (`list-*`, `parse-coverage-xml.py`, `diff-coverage.py`) are reproducible and live in the task folder (not the main repo).
- [ ] User reviews `findings.md` and explicitly approves before any edit to `tools/script-jacoco.gradle`.
- [ ] If fixes are applied: aggregate coverage report regenerates without errors and previously-missing testable files now appear in the report.

## Branch Name

`feature/mobile-tbd-jacoco-audit` — will rename to `feature/mobile-<ticket>-jacoco-audit` in Phase 4i once a Jira ticket is assigned.

## Phase 3 Step Sequence (concrete)

1. **Setup branch:** `git pull origin develop` → `git checkout -b feature/mobile-tbd-jacoco-audit`
2. **Create scratch folders inside task dir:** `mkdir -p scripts data`
3. **Enumerate sources/tests** (cheap — seconds): write and run `list-source-files.sh`, `list-test-files.sh`
4. **Locate / freshen the Jacoco report:**
   - If the existing `build/reports/jacoco/aggregate/coverage.xml` is acceptable as a baseline, copy it to `data/baseline-coverage.xml`.
   - Otherwise run `./gradlew aggregateCoverageReport` (background, log in `data/jacoco-run.log`). User can decide on baseline vs fresh.
5. **Parse coverage XML:** `parse-coverage-xml.py data/baseline-coverage.xml > data/in-report.txt`
6. **Diff & classify:** `diff-coverage.py` produces `missing-from-report.txt` and `false-negatives.txt`.
7. **Audit broad patterns** category-by-category (1-14 in the script). For each big pattern, list 3-5 sample matches and judge testability. Capture in `findings.md`.
8. **Write `findings.md`** with all sections + recommended diff.
9. **Stop and present to user** for approval. No script edits yet.

## Phase 3b (only on user approval)

10. Apply diff to `tools/script-jacoco.gradle`.
11. Re-run `./gradlew aggregateCoverageReport --rerun-tasks`.
12. Confirm bug-fix list is now in the report; confirm UI exclusions still hold.
13. Update `findings.md` with "Applied" section showing before/after numbers.

## Change Log

| Date | Person | Change |
|------|--------|--------|
| 2026-04-30 | zeeshan@wego.com | Initial plan written |
