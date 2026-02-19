# MOBILE-8090: Create Separate Package for Staging Build

## Problem

Two issues with the current staging setup:

1. **Same package name** — Production and staging (debug) builds share `com.wego.android`. Android treats them as the same app, so QA cannot install both on the same device simultaneously.

2. **Crashlytics not reporting on staging** — Builds are uploaded to Firebase staging (App Distribution), but crash reports are not being captured. This is because:
   - Only one `google-services.json` exists (at `wegoapk/google-services.json`), configured for the production Firebase project only
   - No buildType-specific `google-services.json` for the staging Firebase project
   - The `firebaseCrashlytics` block is only configured on the release buildType

## Existing Staging Infrastructure

The project already has a well-established staging variant:
- **Build types:** `debug` = staging, `release` = production
- **Staging icons:** `libbase/src/debug/res/mipmap-*/` (different from production icons in `libbase/src/main/res/mipmap-*/`)
- **Staging API config:** `libbase/build.gradle` defines `STAGING_*` BuildConfig fields (API URLs, auth endpoints, third-party keys)
- **Auth deep links:** Supports both `auth.wegostaging.com` and `auth.wego.com`
- **App Center:** Separate distribution channels (`Wego-Android` for prod, `Wego-Android-Staging` for staging)
- **FileProvider:** Uses `${applicationId}.provider` — will auto-adapt to new package name
- **Separate Firebase project:** Exists for staging but not properly configured in the Android project

## Solution

### Part 1: Separate Package Name
Add `applicationIdSuffix ".staging"` to the existing **debug** buildType in `wegoapk/build.gradle` so staging builds get package `com.wego.android.staging`.

### Part 2: Fix Crashlytics for Staging
- Place staging Firebase project's `google-services.json` at `wegoapk/src/debug/google-services.json` (Android Gradle Plugin automatically picks buildType-specific configs)
- Move production `google-services.json` to `wegoapk/src/release/google-services.json` (or keep at root — root serves as fallback)
- The staging `google-services.json` must include `com.wego.android.staging` as a registered app in the staging Firebase project

**Manual step required:** Developer must download `google-services.json` from the staging Firebase project (after registering the new package `com.wego.android.staging` there).

## Requirements

1. **Add `applicationIdSuffix ".staging"`** to the debug buildType in `wegoapk/build.gradle`
2. **Create directory** `wegoapk/src/debug/` for staging-specific `google-services.json` (user provides the file from Firebase Console)
3. **Verify no hardcoded package name references break** — dynamic references (`${applicationId}`, `getPackageName()`) should auto-adapt
4. **No new build types or flavors** — only modify the existing debug buildType

## Out of Scope

- Creating a new buildType or flavor dimension
- Modifying release/production builds
- Changing icons (already different for staging)
- Changing API configuration (already different for staging)

## Acceptance Criteria

- [ ] Debug builds use applicationId `com.wego.android.staging`
- [ ] Release builds continue using `com.wego.android`
- [ ] Both debug and release APKs can be installed side-by-side on the same device
- [ ] Crashlytics reports crashes from staging builds to the staging Firebase project
- [ ] No hardcoded package name references break with the suffix
- [ ] Existing staging icons, API config, and deep links continue working

## Applicable Rules

- `coding-conventions.md` — Standard formatting and conventions
- `project-structure.md` — Correct module placement for any new files
- `critical-thinking.md` — Verify no hardcoded package references break
