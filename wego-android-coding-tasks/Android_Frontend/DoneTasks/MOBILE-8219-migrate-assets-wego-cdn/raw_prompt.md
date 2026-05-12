# [Wego Android] Migrate from assets.wego.com to new asset CDN — update remote-config defaults & Firebase values

**Jira Ticket:** https://wegomushi.atlassian.net/browse/MOBILE-8219
**Type:** Story
**Status:** To Do
**Assignee:** Zeeshan Arif
**Project:** Mobile (MOBILE)

---

## Summary

Migrate the Wego Android app off the legacy `assets.wego.com` host onto the new asset CDN. Every asset URL on Android is already routed through Firebase Remote Config via `WegoConfig.instance.getString(...)`, so the work reduces to:

1. Update the bundled defaults in `libbase/src/main/res/raw/config_defaults.json`.
2. Update the corresponding values in Firebase Remote Config (staging + production).
3. Sanity-clean a handful of `@Preview` literals in Compose previews.

---

## Background

Audit of `assets.wego.com` references in `wego-android-n`:

| Category | Count | Files |
| --- | --- | --- |
| Remote-config defaults JSON (top-level keys) | **10 keys** (9 String + 1 JSON) | `libbase/.../config_defaults.json` |
| Remote-config defaults JSON (embedded JSON values) | **2 flagUrl** in `contact_phone_details` + **7 icon_url** in activities/payment-methods list | same file |
| Hardcoded runtime literals (Kotlin/Java) | **0** | — |
| `@Preview`-only literals (debug-only) | **6 files** | various Compose previews |
| Comment-only references | 3 | non-functional |
| Host-detection / URL rewriting (`contains("assets.wego")`) | **0** | `CloudinaryImageUtilLib.java` is domain-agnostic |
| Wear OS module (`wegowear`) hardcoded URLs | **0** | — |

> **Architecture note:** Android uses `WegoConfig` (`libbase/.../data/configs/WegoConfig.java`) backed by `FirebaseRemoteConfig` (`libbase/.../util/RemoteConfig.java`). Local defaults ship as `libbase/src/main/res/raw/config_defaults.json`. Keys are declared in `ConstantsLib.FirebaseRemoteConfigKeys` (lines ~3142–3255). The naming convention is `b_` for backend-shared keys and `a_` for Android-specific keys. There is **no separate Wear OS defaults file** — the Wear module reuses the main pipeline.

---

## Goal

After this ticket is closed:

1. **No** `assets.wego.com` URL ships in the next Android binary as a runtime default — neither as a top-level remote-config key default nor inside an embedded JSON default.
2. **Every Firebase Remote Config key** that points at the legacy host is updated to the new asset host in **both staging and production**.
3. **No regression** in image loading on any surface (hotel/flight provider logos, airline logos, payment-method icons, activities category icons, customer-support flags, destination images).

---

## Firebase Remote Config keys to update

Update these on Firebase Remote Config Console for **both staging and production**, **and** update the corresponding default in `config_defaults.json`.

| # | Key | Type | Current default (legacy host) | `config_defaults.json` line |
| --- | --- | --- | --- | --- |
| 1 | `provider_logo_base_url` | String | `https://assets.wego.com/image/upload/f_webp,q_auto/c_fit,w_150,h_46/providers/rectangular_logos/` | L16 |
| 2 | `provider_logo_base_url_recommended` | String | `https://assets.wego.com/image/upload/f_webp,q_auto/c_fit,w_450,h_138/providers/rectangular_logos/` | L17 |
| 3 | `b_cities_image_base_url` | String | `https://assets.wego.com/image/upload/destinations/cities/` | L45 |
| 4 | `b_country_image_base_url` | String | `https://assets.wego.com/image/upload/destinations/country-thumbnail/` | L47 |
| 5 | `b_alliance_image_base_url` | String | `https://assets.wego.com/image/upload/v1555059367/flights/airlines_square/` | L53 |
| 6 | `b_wa_categories_url` | String | `https://assets.wego.com/image/upload/v1600771099/mobile-apps/activities-categories/` | L54 |
| 7 | `a_payment_logos_base_url` | String | `https://assets.wego.com/image/upload/c_scale,h_25,f_webp,q_auto:good,w_45/payment_logos/` | L60 |
| 8 | `a_airline_rectangular_logo_base_url` | String | `https://assets.wego.com/image/upload/c_fit,f_webp,q_auto,w_120,h_40/flights/airlines_rectangular/` | L61 |
| 9 | `a_airline_square_logo_base_url` | String | `https://assets.wego.com/image/upload/c_fit` _(transform params truncated — runtime value comes from Firebase override)_ | L62 |
| 10 | `b_bow_payment_method_logo_url` | String | `https://assets.wego.com/image/upload/v1657021559/mobile-apps/payment_logos/` | L154 |
| 11 | `contact_phone_details` | JSON | JSON string containing **2 embedded** `flagUrl` values pointing at `assets.wego.com/.../customer-support/cs-egypt.png` and `cs-worldwide.png` | L149 |

### Embedded JSON defaults inside `config_defaults.json`

Beyond the top-level keys, the defaults file itself contains embedded `assets.wego.com` URLs in two JSON-typed values:

* `contact_phone_details` (L149) — 2 × `flagUrl` (customer-support flag icons)
* Activities / payment-methods list — **7 ×** `icon_url` at lines 274, 290, 306, 326, 346, 362, 378. All currently point at `https://assets.wego.com/image/upload/v1618472861/mobile-apps/activities-categories/trains.png`.

These must be updated to the new asset host as part of the same JSON edit.

---

## Acceptance Criteria

### AC1 — Firebase Remote Config values updated

* [ ] Update values for all 10 string keys + 1 JSON key (#1–#11) on **Firebase Remote Config — staging environment**.
* [ ] Same updates published to **Firebase Remote Config — production environment**.
* [ ] For `contact_phone_details`: update **both** embedded `flagUrl` values inside the JSON string.

### AC2 — `config_defaults.json` migrated

File: `libbase/src/main/res/raw/config_defaults.json`

* [ ] L16 `provider_logo_base_url` → new host.
* [ ] L17 `provider_logo_base_url_recommended` → new host.
* [ ] L45 `b_cities_image_base_url` → new host.
* [ ] L47 `b_country_image_base_url` → new host.
* [ ] L53 `b_alliance_image_base_url` → new host.
* [ ] L54 `b_wa_categories_url` → new host.
* [ ] L60 `a_payment_logos_base_url` → new host.
* [ ] L61 `a_airline_rectangular_logo_base_url` → new host.
* [ ] L62 `a_airline_square_logo_base_url` → new host. _(Note: existing default is truncated — confirm with team whether to restore full transform params or keep minimal; production value comes from Firebase override either way.)_
* [ ] L149 `contact_phone_details` → both embedded `flagUrl` values updated to new host.
* [ ] L154 `b_bow_payment_method_logo_url` → new host.
* [ ] Lines 274, 290, 306, 326, 346, 362, 378 — all 7 `icon_url` entries in the embedded activities/payment-methods list → new host.

### AC3 — Host-detection regression check

`libbase/.../util/CloudinaryImageUtilLib.java` operates on path patterns (`/upload/`, `cdn-cgi/image/`) — domain-agnostic. A repo-wide `grep -rn 'contains.*assets' --include="*.kt" --include="*.java"` returns zero hits.

* [ ] No-op verification: re-run `grep -rn '"assets.wego' --include="*.kt" --include="*.java"` and confirm no host-detection logic was introduced after the audit.

### AC4 — `@Preview` literal cleanup (low priority, ship-with-binary cosmetic)

These do not affect runtime users but ship as string literals in the debug binary and pollute future `assets.wego` greps. Update to the new host:

* [ ] `hotels/.../bow/ui/booking/CheckInCheckOutSection.kt` — lines 202, 204, 210, 212, 218, 220, 226, 228, 234, 236 (inside `CheckInCheckOutSectionPreview`).
* [ ] `hotels/.../bow/ui/booking/BookingSuccessTop.kt` — lines 637, 639, 645, 647, 653, 655, 661, 663, 669, 671.
* [ ] `hotels/.../bow/ui/booking/HotelDetailPaymentSummarySection.kt` — lines 905, 907, 913, 915, 921, 923.
* [ ] `flights/.../flytoanywhere/ui/compose/CityDestinationCardView.kt:303` — preview image literal.
* [ ] After update, refresh `config/detekt/baseline.xml` if any `MaxLineLength` IDs change.

### AC5 — Comment-only references (housekeeping)

Optional but reduces noise in future searches:

* [ ] `libbase/.../util/WegoSettingsUtilLib.java:67` — commented-out legacy URL.
* [ ] `flights/.../data/models/JacksonFlightRoute.java:37` — commented-out example.
* [ ] `multicity/.../features/details/MulticityFlightDetailsPresenter.java:103` — commented-out example.

### AC6 — Verification

* [ ] Unit tests pass: `./gradlew :wegoapk:testPlaystoreDebugUnitTest`
* [ ] Detekt clean: `./gradlew detekt`
* [ ] Smoke tests pass: `./scripts/smoke-test.sh`
* [ ] Build a Play debug APK and manually verify the following image surfaces render correctly **with Firebase pointed at the new host** AND **with Firebase manually reverted to the legacy host** (proves backwards-compat through the transition window):

    * Hotel SRP — provider rectangular logos (`provider_logo_base_url[_recommended]`).
    * Flight results — airline square + rectangular logos (`b_alliance_image_base_url`, `a_airline_square_logo_base_url`, `a_airline_rectangular_logo_base_url`).
    * BOW (hotels + flights) — payment-method icons (`b_bow_payment_method_logo_url`, `a_payment_logos_base_url`).
    * Activities home / categories (`b_wa_categories_url`).
    * Customer-support contact list — flag icons (`contact_phone_details`).
    * Home destinations — city/country thumbnails (`b_cities_image_base_url`, `b_country_image_base_url`).

* [ ] Repo-wide grep after change: `grep -rn 'assets.wego' --include="*.kt" --include="*.java" --include="*.json" --include="*.xml"` returns only test fixtures, detekt baseline entries (until refreshed), and acceptable comment-only references.

### AC7 — Documentation

- [ ] Update the Firebase Remote Config change log (or wherever the team tracks remote-config changes) with the new values and the deploy date.

---

## Sub-Tasks (suggested breakdown)

| # | Sub-task | Estimate |
| --- | --- | --- |
| 1 | Update Firebase Remote Config values for 11 keys on staging + production (AC1) | ~20–30 min, no engineering |
| 2 | Update `config_defaults.json` — 10 top-level keys + 2 embedded `flagUrl` + 7 embedded `icon_url` (AC2) | ~30 min |
| 3 | Update `@Preview` literals across hotels/flights modules (AC4) | ~30 min |
| 4 | Cleanup of comment-only references (AC5) | ~10 min |
| 5 | Manual sanity pass on debug APK across the 6 image surfaces (AC6) | ~1 h |

Total estimate: **~2.5–3 hours of engineering** plus the Firebase Remote Config updates.

---

## Out of Scope

* Backend-driven asset URLs (URLs returned at runtime by APIs — hotel images, room images, flight booking payloads). These migrate when the backend migrates.
* Test fixtures (`**/test/**/*.json`, mock JSON files). Non-runtime; refresh whenever backend test fixtures are updated.
* Decommissioning the `assets.wego.com` host itself — owned by backend/infra team.
* Creating new Firebase Remote Config keys — none are needed (every surface is already wired).

---

## Dependencies

* **Backend / Infra team:** confirm the new asset CDN hostname and the target window for decommissioning `assets.wego.com`. The legacy host **must remain available** until adoption of the new Android release is high — otherwise users on older versions, or users who haven't completed a Firebase Remote Config fetch since the migration, will see broken images.
* **Designers / Product:** no change expected; this is a CDN swap with no visual difference.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Users on legacy `config_defaults.json` (first launch / offline launch) hit broken URLs after host decommission | Low | Low | AC2 updates the bundled defaults so even the offline path uses the new host once this build ships |
| Firebase Remote Config value missed for one key → silent fallback to bundled default | Low | Low | AC2 ensures the bundled default is also on the new host; both paths are safe |
| `@Preview` literals not updated → spurious `assets.wego` grep hits forever | Low | Trivial | AC4 covers the 4 files |
| Wear OS regression | Very Low | Low | Audit confirmed no hardcoded asset URLs in `wegowear`; it reuses main app config |

---

## Definition of Done

* All AC1–AC7 checkboxes ticked.
* PR merged to `develop`.
* Verified on a Play debug build that all listed image surfaces render correctly on the new asset host (with Firebase pointing to the new host).
* Verified on a Play debug build that all listed image surfaces _still render_ if Firebase is manually pointed back at the legacy host — proves backwards-compat through the transition.
* Firebase Remote Config change log updated.

---

## References

* Android remote-config: `libbase/src/main/java/com/wego/android/data/configs/WegoConfig.java`, `libbase/src/main/java/com/wego/android/util/RemoteConfig.java`
* Android keys declaration: `libbase/src/main/java/com/wego/android/ConstantsLib.java` → `interface FirebaseRemoteConfigKeys`
* Android defaults: `libbase/src/main/res/raw/config_defaults.json`
* Cloudinary URL rewriter (domain-agnostic): `libbase/src/main/java/com/wego/android/util/CloudinaryImageUtilLib.java`

---

*Fetched from Jira on 2026-05-12*
