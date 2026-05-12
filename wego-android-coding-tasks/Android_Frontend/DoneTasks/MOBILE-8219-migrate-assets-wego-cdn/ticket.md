# [MOBILE-8219] Clean up `assets.wego.com` hardcoded references (preparation for CDN migration)
**Jira:** https://wegomushi.atlassian.net/browse/MOBILE-8219

## Problem
The Android codebase contains hardcoded `https://assets.wego.com/...` URL strings in two non-runtime locations:
- **`@Preview` Compose functions** (4 files) — preview-only image URLs that ship in the debug binary and pollute future grep searches.
- **Commented-out legacy URLs** (6 files) — stale "what the URL used to be" notes from a prior migration to Firebase Remote Config, plus commented-out preview templates.

The eventual goal is to migrate **all** asset URLs off `assets.wego.com` to a new CDN, but the new CDN hostname has not been confirmed yet. Without cleaning these hardcoded references first, the eventual host swap will be muddier (more files to touch, more grep noise to wade through).

## Solution
Housekeeping pass that removes `assets.wego.com` from all non-runtime locations while **leaving runtime defaults (`config_defaults.json`) untouched** until the new CDN host is confirmed:

- Replace all `assets.wego.com` URL string literals inside live `@Preview` blocks with neutral `https://example.com/preview/...` placeholders. Compose Previews never fetch these images at render time, so the placeholders are functionally equivalent.
- Delete commented-out single-line "legacy URL" notes (3 files from the original audit).
- Replace `assets.wego.com` URLs inside commented-out preview-template blocks with the same neutral placeholders (3 files — new finds beyond the original audit).
- Refresh the affected entries in `config/detekt/baseline.xml` so the baseline fingerprints match the new strings.

Out of scope (deferred to a follow-up ticket):
- The actual host migration in `config_defaults.json` (waiting on the new CDN hostname from backend/infra).
- Firebase Remote Config console value updates (operational work, no code change).

**Now also in scope** (added after reviewer feedback): refactor the hardcoded runtime URL in `mytrips/.../FlightBookingCard.kt:580` by adding a new dedicated config key `a_mytrips_airline_logo_base_url` whose default is the exact same URL the function previously hardcoded. URL semantics are byte-identical at runtime; the ownership just moved from code to `config_defaults.json`.

## Benefits
- Future `grep 'assets.wego'` returns only `config_defaults.json` and one known follow-up — easy to spot when the actual CDN swap lands.
- Smaller blast radius for the eventual `config_defaults.json` migration PR — no `@Preview` noise to scroll past during review.
- Removes stale "what it used to be" comments that confuse new contributors reading the legacy URL alongside the live `WegoConfig.instance.getString(...)` call.

## Acceptance Criteria
- [x] All hardcoded `assets.wego.com` strings inside live `@Preview` blocks replaced with `example.com/preview/...` placeholders (4 files).
- [x] All stale single-line `// "https://assets.wego.com/..."` legacy-URL comments deleted (3 files from original audit).
- [x] All `assets.wego.com` strings inside commented-out preview-template blocks replaced or deleted (3 newly-found files).
- [x] `config/detekt/baseline.xml` entries updated so the baseline fingerprints match the new strings.
- [x] `./gradlew detekt` passes with 0 issues.
- [x] `./gradlew :wegoapk:testPlaystoreDebugUnitTest` passes (4m 15s, 580 tasks).
- [x] `./scripts/smoke-test.sh` passes (16 classes, 275s).
- [x] Repo-wide grep `assets\.wego` in `.kt`/`.java` (excluding tests + build) returns **zero** hits. `config_defaults.json` is the sole remaining `assets.wego.com` ownership.
- [x] `mytrips/.../FlightBookingCard.kt:580` runtime URL moved to a new dedicated config key (`a_mytrips_airline_logo_base_url`).

## Follow-up work
1. **Confirm new CDN hostname** with backend/infra team → then migrate `config_defaults.json` (now 12 top-level keys, including the new `a_mytrips_airline_logo_base_url` + 9 embedded JSON URLs) and update Firebase Remote Config (staging + production).
2. **Operational consideration:** Once new CDN is confirmed, decide whether to consolidate `a_mytrips_airline_logo_base_url` and `b_alliance_image_base_url` into a single key (they only differ by Cloudinary version pin: `v20190227` vs `v1555059367`).
