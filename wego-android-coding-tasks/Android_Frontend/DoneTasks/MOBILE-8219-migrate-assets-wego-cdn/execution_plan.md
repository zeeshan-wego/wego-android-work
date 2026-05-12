# Execution Plan — MOBILE-8219

**Branch:** `feature/mobile-8219-cleanup-assets-wego-references`
**Jira:** https://wegomushi.atlassian.net/browse/MOBILE-8219
**Started:** 2026-05-12
**Developer:** zeeshan@wego.com

---

## Summary

Housekeeping pass over `wego-android-n` to remove all hardcoded `https://assets.wego.com/...` URL string literals from non-runtime code paths — `@Preview` Compose functions and commented-out code. Live runtime defaults in `libbase/src/main/res/raw/config_defaults.json` are **intentionally left untouched** because the new CDN host has not been confirmed by backend/infra.

This is preparation work for the eventual host migration: once the new CDN host is confirmed, the `config_defaults.json` + Firebase Remote Config update will be a single, focused change — no extra grep noise from `@Preview` strings to wade through.

---

## Approach & Trade-offs

### Approach
Replace all live-code `assets.wego.com` URL string literals (in `@Preview` blocks) with `https://example.com/preview/...` placeholders. Delete commented-out `assets.wego.com` URL lines that exist only as stale documentation. Leave a clean repo where `grep 'assets.wego' *.kt *.java` returns only `config_defaults.json` and one known follow-up (`FlightBookingCard.kt:580`).

### Trade-offs considered

| Trade-off | Chosen path | Rejected alternative |
| --- | --- | --- |
| What URL host to use in `@Preview` placeholders? | `example.com` — RFC-reserved, never resolves, signals "fake" clearly | `placehold.co` (external dep), empty string (might break Compose preview rendering), `localhost` (looks intentional) |
| Delete commented-out URLs or rewrite host? | Delete the legacy-URL comment lines (they're stale "what it used to be" docs after the URL moved to config) | Rewrite to `// <new-host>/...` — creates churn for no value since the comment is already redundant with the live code on the line above |
| Touch `mytrips/.../FlightBookingCard.kt:580` (hardcoded runtime URL) | **Defer** to a follow-up PR. Will be flagged in `pr-description.md` | Refactor inline — risks runtime regression and crosses module boundaries (mytrips → libbase config keys); deserves its own PR with manual QA |
| Touch `config_defaults.json` host migration? | **No** — user explicitly said keep `assets.wego.com` for now | Migrate to a placeholder like `[NEW_CDN_HOST]` — risky, requires build-time substitution mechanism |

---

## Files to change

### A. `@Preview` literal cleanup (4 files, 31 occurrences)

Replace pattern:
- Hotels JPG: `https://assets.wego.com/image/upload/v1619752572/Partner/hotels/1331161/545061328.jpg`
  → `https://example.com/preview/hotel.jpg`
- City JPG: `https://assets.wego.com/image/upload/c_fill,f_auto,fl_lossy,g_auto,h_600,q_auto:low,w_600/v1/flights/cities_images/JED.jpg`
  → `https://example.com/preview/city.jpg`

| File | Lines | Count |
| --- | --- | --- |
| `hotels/src/main/java/com/wego/android/bow/ui/booking/CheckInCheckOutSection.kt` | 202, 204, 210, 212, 218, 220, 226, 228, 234, 236 | 10 |
| `hotels/src/main/java/com/wego/android/bow/ui/booking/BookingSuccessTop.kt` | 637, 639, 645, 647, 653, 655, 661, 663, 669, 671 | 10 |
| `hotels/src/main/java/com/wego/android/bow/ui/booking/HotelDetailPaymentSummarySection.kt` | 905, 907, 913, 915, 921, 923, 929, 931, 937, 939 | 10 |
| `flights/src/main/java/com/wego/android/features/flytoanywhere/ui/compose/CityDestinationCardView.kt` | 303 | 1 |

**Strategy:** Use `Edit` with `replace_all=true` per file since each file uses one URL literal repeated many times.

### B. Comment-only cleanup (6 files, 15 occurrences)

**B1 — Delete stale `// "https://assets.wego.com/..."` lines (3 files from ticket):**

| File | Line | Action |
| --- | --- | --- |
| `libbase/src/main/java/com/wego/android/util/WegoSettingsUtilLib.java` | 67 | Delete the single commented line (the live `getString(PAYMENT_LOGOS_BASE_URL)` on line 66 already documents the source) |
| `flights/src/main/java/com/wego/android/data/models/JacksonFlightRoute.java` | 37 | Delete the single commented line |
| `multicity/src/main/java/com/wego/android/features/details/MulticityFlightDetailsPresenter.java` | 103 | Delete the single commented line |

**B2 — Replace `assets.wego.com` inside commented-out `@Preview` blocks (3 files, new finds):**

These are large commented-out preview-template blocks that contain `assets.wego.com` URLs. Deleting the whole block is risky (devs may use them as templates). Replacing only the URLs is safer and serves the same "clean grep" goal.

| File | Lines | Action |
| --- | --- | --- |
| `hotels/src/main/java/com/wego/android/bow/ui/home/PaymentSummarySection.kt` | 1110 | Delete this single commented-out parameter line (it sits inside otherwise-live code) |
| `hotels/src/main/java/com/wego/android/bow/ui/home/HotelDetailsSection.kt` | 533 | Replace URL within comment with `https://example.com/preview/hotel.jpg` (preserves the surrounding commented-out template) |
| `hotels/src/main/java/com/wego/android/bow/ui/booking/BookingStatusUi.kt` | 391, 393, 399, 401, 407, 409, 415, 417, 423, 425 | Replace URL within comments with `https://example.com/preview/hotel.jpg` (preserves template) |

---

## Files NOT touched (and why)

| File | Why |
| --- | --- |
| `libbase/src/main/res/raw/config_defaults.json` | User: keep `assets.wego.com` until new CDN confirmed |
| `mytrips/.../FlightBookingCard.kt:580` | Hardcoded runtime URL — touching this is a separate scope (own PR, needs manual QA across My Trips airline logo rendering) |
| `libbase/.../CloudinaryImageUtilLib.java` | Already host-agnostic (path-pattern based, not host-pattern based) |
| `config/detekt/baseline.xml` | Only refresh if a `MaxLineLength` ID changes — all replacements are shorter than originals, so no new line-length issues expected. Verify after edits |

---

## Test plan

### Pre-edit verification
```bash
# Confirm baseline grep counts
grep -rn 'assets\.wego' --include="*.kt" --include="*.java" \
  | grep -v '/test/' | grep -v '/build/' | wc -l
# Expected: ~75 occurrences (config_defaults.json + scope files + FlightBookingCard.kt)
```

### Post-edit verification

1. **Detekt clean:**
   ```bash
   ./gradlew detekt
   ```
   Expected: 0 issues. If `MaxLineLength` changes appear, refresh `config/detekt/baseline.xml`.

2. **Unit tests pass:**
   ```bash
   ./gradlew :wegoapk:testPlaystoreDebugUnitTest
   ```

3. **Smoke tests pass:**
   ```bash
   ./scripts/smoke-test.sh
   ```

4. **Final grep is clean:**
   ```bash
   grep -rn 'assets\.wego' --include="*.kt" --include="*.java" \
     | grep -v '/test/' | grep -v '/build/'
   ```
   Expected output: only `mytrips/.../FlightBookingCard.kt:580` (intentionally deferred). Zero hits in `hotels/`, `flights/`, `multicity/`, `libbase/`.

5. **Compose preview sanity (optional, IDE):**
   Open `CheckInCheckOutSection.kt`, `BookingSuccessTop.kt`, `HotelDetailPaymentSummarySection.kt`, `CityDestinationCardView.kt` in Android Studio and confirm `@Preview` blocks still render (with image placeholders instead of broken-image icons). Skippable if Android Studio isn't open — Compose Previews don't affect the binary.

### What we deliberately don't need to test

- **Runtime image loading.** No runtime code path touches the modified strings — they're all `@Preview`-scoped or commented-out. The runtime image URLs all flow through `WegoConfig.instance.getString(...)` and `config_defaults.json` (untouched).
- **Firebase Remote Config behavior.** This PR does not change any remote-config plumbing.

---

## Documentation updates

None for this PR. Specifically:

- **No API doc updates** — no API endpoints touched.
- **No ERD updates** — no DB changes.
- **No `CHANGELOG.md` entry** — pure housekeeping, doesn't change behavior.
- **Jira ticket** — task-flow Phase 4 archives the original description and updates the ticket with `ticket.md` content automatically.

---

## Acceptance criteria

- [ ] All 31 occurrences of `assets.wego.com` in live `@Preview` blocks (across 4 files) replaced with `example.com/preview/...` placeholders.
- [ ] 3 single-line stale URL comments deleted (WegoSettingsUtilLib, JacksonFlightRoute, MulticityFlightDetailsPresenter).
- [ ] 1 single-line commented-out parameter deleted (PaymentSummarySection.kt:1110).
- [ ] 11 occurrences of `assets.wego.com` inside commented-out `@Preview` templates (HotelDetailsSection 1 + BookingStatusUi 10) replaced with `example.com/preview/hotel.jpg`.
- [ ] `./gradlew detekt` passes with 0 issues.
- [ ] `./gradlew :wegoapk:testPlaystoreDebugUnitTest` passes.
- [ ] `./scripts/smoke-test.sh` passes.
- [ ] Repo-wide grep `assets\.wego` in `.kt`/`.java` (excluding tests/build) returns **only** `mytrips/.../FlightBookingCard.kt:580`.
- [ ] `pr-description.md` flags `FlightBookingCard.kt:580` and the deferred `config_defaults.json` migration as follow-up work.

---

## Change Log

| Date | Time | Person | Change |
| --- | --- | --- | --- |
| 2026-05-12 | 13:30 | zeeshan@wego.com | Initial plan written |
