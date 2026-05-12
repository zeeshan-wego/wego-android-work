# MOBILE-8219 — Cleanup `assets.wego.com` Hardcoded Preview & Comment References

**Jira:** https://wegomushi.atlassian.net/browse/MOBILE-8219
**Status:** Refined understanding (scope re-shaped after user input)

---

## What the ticket originally asked for

Migrate the Wego Android app off `assets.wego.com` to a new asset CDN. Three layers of work:

1. Update `config_defaults.json` bundled defaults (10 top-level keys + 9 embedded JSON URLs).
2. Update Firebase Remote Config values (staging + production) for those same 11 keys.
3. Clean up cosmetic hardcoded `assets.wego.com` strings in `@Preview` literals and comments.

---

## Re-scoped intent (after user clarification)

The new CDN hostname has **not been confirmed** by the backend/infra team yet, so the actual host migration is deferred. This PR is **preparation work**:

- **Keep `assets.wego.com` URLs in `config_defaults.json` as-is.** Do not migrate runtime defaults until the new CDN is confirmed.
- **Do the housekeeping work** — clean up hardcoded `assets.wego.com` references that pollute future grep results and de-couple cosmetic preview code from the legacy host.
- **Firebase Remote Config console updates + change-log entry** — handled by the user outside this PR (no console access required from this branch).

So the actual code scope reduces to:

1. **AC4 — `@Preview` literal cleanup** in 4 Compose files.
2. **AC5 — comment-only cleanup** in 3 files from the ticket **+ 3 extras found during fresh audit** (the original audit was slightly stale).
3. **Findings/follow-ups** documented in the PR description.

---

## Fresh audit (2026-05-12)

Repo-wide grep `assets\.wego` in `.kt` / `.java` / `.json` / `.xml` (excluding `/test/`, `/build/`, `baseline.xml`):

| Category | Ticket said | Audit found | Delta |
| --- | --- | --- | --- |
| `config_defaults.json` top-level + embedded URLs | 10 + 9 | Same | — |
| Hardcoded runtime literals (Kotlin/Java) | **0** | **1** | **`mytrips/.../FlightBookingCard.kt:580`** (the `mytrips` module was added recently — post-audit) |
| `@Preview`-only literals | 6 files | 4 files (CheckInCheckOutSection, BookingSuccessTop, HotelDetailPaymentSummarySection, CityDestinationCardView) | Ticket listed 6 but only 4 contain `assets.wego` |
| Comment-only references | 3 files | **6 files** | 3 extra: `PaymentSummarySection.kt:1110`, `HotelDetailsSection.kt:533`, `BookingStatusUi.kt` (×8 lines) |

---

## In scope for this PR

### A. `@Preview` literal cleanup (AC4)

Replace hardcoded `https://assets.wego.com/...` strings inside `@Preview` Compose functions with a neutral placeholder (`https://example.com/preview/...`). Compose Previews don't fetch images at render time, so neutral URLs render the same placeholder.

Files:

| File | Lines | Notes |
| --- | --- | --- |
| `hotels/.../bow/ui/booking/CheckInCheckOutSection.kt` | 202, 204, 210, 212, 218, 220, 226, 228, 234, 236 | 10 occurrences of one hotel JPG URL inside `CheckInCheckOutSectionPreview` |
| `hotels/.../bow/ui/booking/BookingSuccessTop.kt` | 637, 639, 645, 647, 653, 655, 661, 663, 669, 671 | 10 occurrences |
| `hotels/.../bow/ui/booking/HotelDetailPaymentSummarySection.kt` | 905, 907, 913, 915, 921, 923, 929, 931, 937, 939 | 10 occurrences (ticket said 6; audit shows 10) |
| `flights/.../flytoanywhere/ui/compose/CityDestinationCardView.kt` | 303 | 1 occurrence |

### B. Comment-only references cleanup (AC5 + extras)

Delete (or rewrite to be host-neutral) commented-out `assets.wego.com` URLs:

| File | Lines | Source |
| --- | --- | --- |
| `libbase/.../util/WegoSettingsUtilLib.java` | 67 | Ticket AC5 |
| `flights/.../data/models/JacksonFlightRoute.java` | 37 | Ticket AC5 |
| `multicity/.../features/details/MulticityFlightDetailsPresenter.java` | 103 | Ticket AC5 |
| `hotels/.../bow/ui/home/PaymentSummarySection.kt` | 1110 | **New find** |
| `hotels/.../bow/ui/home/HotelDetailsSection.kt` | 533 | **New find** |
| `hotels/.../bow/ui/booking/BookingStatusUi.kt` | 391, 393, 399, 401, 407, 409, 415, 417, 423, 425 | **New find** (10 commented lines, also a `@Preview` block) |

### C. Verification (AC6 subset)

- `./gradlew :wegoapk:testPlaystoreDebugUnitTest`
- `./gradlew detekt`
- `./scripts/smoke-test.sh`
- Final repo-wide grep `assets\.wego` should return only:
  - `config_defaults.json` (intentionally kept)
  - `mytrips/.../FlightBookingCard.kt:580` (flagged as follow-up — see below)
  - test fixtures (out of scope)

---

## Out of scope for this PR

| Item | Why |
| --- | --- |
| `config_defaults.json` host migration (AC2 in ticket) | User explicitly said "keep `assets.wego.com` in `config_defaults.json` for now" until the new CDN host is confirmed by backend/infra |
| Firebase Remote Config console updates (AC1) | User handles separately when new CDN host is confirmed |
| Firebase change-log entry (AC7) | Tied to AC1 — separate operational work |
| `mytrips/.../FlightBookingCard.kt:580` — hardcoded runtime asset URL | **NEW FINDING.** The ticket said 0 hardcoded runtime literals but the `mytrips` module added one after the audit. Refactoring it to read from `WegoConfig` is a separate change (touches runtime behavior, needs its own QA pass). Will be flagged in pr-description.md as a follow-up |
| `a_airline_square_logo_base_url` L62 truncation | User: "complete URL is from config so not required at FE" — leave as-is |
| Detekt baseline refresh | Only needed if a `MaxLineLength` ID changes — verify after edits, refresh only if necessary |

---

## Acceptance criteria (this PR)

- [ ] All 31 occurrences of `https://assets.wego.com` in `@Preview` blocks (across 4 files) replaced with `https://example.com/preview/...` placeholders.
- [ ] All 16 commented-out lines containing `assets.wego.com` across 6 files removed (or rewritten host-neutral).
- [ ] Detekt clean: `./gradlew detekt`
- [ ] Unit tests pass: `./gradlew :wegoapk:testPlaystoreDebugUnitTest`
- [ ] Smoke tests pass: `./scripts/smoke-test.sh`
- [ ] Final grep `assets\.wego` in `.kt`/`.java` returns only `config_defaults.json` and `FlightBookingCard.kt:580` (intentionally kept / flagged as follow-up).
- [ ] PR description flags FlightBookingCard.kt:580 as a follow-up.

---

## Applicable Rules

Based on the task content, the following coding rules apply:

| Rule | Reason |
| --- | --- |
| `docs/ai-rules/critical-thinking.md` | Always-apply. Several ticket assumptions were stale (audit gap on `mytrips`) — verify before editing |
| `docs/ai-rules/detekt-compliance.md` | Verification requires `./gradlew detekt` to pass with 0 issues |
| `docs/ai-rules/coderabbit-compliance.md` | PR will go through CodeRabbit review |
| `docs/ai-rules/code-review.md` | Pre-commit code review checklist |
| `docs/ai-rules/android-best-practices.md` | Light touch — only edits are inside `@Preview` blocks and comments; no runtime behavior changes |

Always-apply rules (no detection needed): `critical-thinking.md`.

Task-specific rules deliberately **not applicable** here:
- `mvvm-rules.md` — no ViewModel/UI architecture changes
- `performance-optimization.md` — no runtime changes
- `ui-component-validation.md` — no new UI components (only preview placeholders)

---

## Open assumptions to validate during coding

1. **Compose Previews accept arbitrary URLs without breaking IDE preview rendering.** Verified theoretically (Coil/Glide gracefully handle 404s in previews) but worth confirming if any preview-only test asserts the URL.
2. **None of the `@Preview` URL strings are referenced by tests or screenshots.** A quick grep for `545061328.jpg` and `JED.jpg` will confirm.
3. **Removing commented-out URLs in `BookingStatusUi.kt` (lines 391–425) doesn't accidentally remove uncommented code.** Need to re-read context around those lines before deleting.
