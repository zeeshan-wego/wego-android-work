# Execution Plan: MOBILE-8090 — Create Separate Package for Staging Build

**Branch:** `feature/mobile-8090-staging-package-suffix`

## Summary

Add `applicationIdSuffix ".staging"` to the debug buildType so staging and production APKs can coexist on the same device. Fix hardcoded package name references in the manifest that would break with the suffix. Configure Firebase Crashlytics for staging builds by placing staging `google-services.json` and enabling Crashlytics on debug buildType.

## Firebase Discovery (from CLI)

| | Production (`wego-smart-lock`) | Staging (`wego-mobile-apps-staging`) |
|---|---|---|
| **Project number** | 551606652723 | 14941031996 |
| **Registered Android package** | `com.wego.android` | `com.wego.android` |
| **`google-services.json` in project** | Yes (`wegoapk/google-services.json`) | **Not present** |
| **Crashlytics config in build** | Yes (`release` block only) | N/A |

**Root cause of Crashlytics not working on staging:**
1. Only production `google-services.json` exists — staging builds send Firebase data to production project (or nowhere)
2. `firebaseCrashlytics { mappingFileUploadEnabled true }` is only in the `release` buildType, not `debug`

## Approach

The `applicationIdSuffix` changes the Android application ID (what the OS uses to identify the app) but does NOT change the Java/Kotlin namespace. So:
- `Class.forName("com.wego.android.*.SomeActivity")` — **SAFE**, class names don't change
- `${applicationId}` in manifests — **SAFE**, auto-adapts
- Hardcoded `"com.wego.android"` in manifests — **MUST FIX**, won't match staging package

## Files to Change

### 1. `wegoapk/build.gradle` (line ~51)
- Add `applicationIdSuffix ".staging"` to the debug buildType
- Result: debug builds → `com.wego.android.staging`, release → `com.wego.android`
- Add `firebaseCrashlytics { mappingFileUploadEnabled false }` to the debug buildType (debug builds are not minified, so no mapping file needed — but this enables Crashlytics reporting)

### 2. `wegoapk/src/main/AndroidManifest.xml`

**Line 31-33 — Custom permission definition:**
```xml
<!-- Before -->
<permission android:name="com.wego.android.permission.C2D_MESSAGE" ... />

<!-- After -->
<permission android:name="${applicationId}.permission.C2D_MESSAGE" ... />
```

**Line 36 — Uses-permission:**
```xml
<!-- Before -->
<uses-permission android:name="com.wego.android.permission.C2D_MESSAGE" />

<!-- After -->
<uses-permission android:name="${applicationId}.permission.C2D_MESSAGE" />
```

**Line 227 — PushReceiver category:**
```xml
<!-- Before -->
<category android:name="com.wego.android" />

<!-- After -->
<category android:name="${applicationId}" />
```

### 3. `wegoapk/src/debug/google-services.json` (AUTOMATED via Firebase CLI)

Download staging Firebase config using:
```bash
firebase apps:sdkconfig ANDROID "1:14941031996:android:e409b2648aa2e5a6f7fd39" --project wego-mobile-apps-staging
```
Save output to `wegoapk/src/debug/google-services.json`.

**However:** After adding `applicationIdSuffix ".staging"`, the staging app's package becomes `com.wego.android.staging`. The staging Firebase project currently only has `com.wego.android` registered. So we need to:
1. **Register `com.wego.android.staging`** as a new Android app in the staging Firebase project via CLI
2. **Re-download** the `google-services.json` (it will include both package names)
3. Place it at `wegoapk/src/debug/google-services.json`

### 4. Firebase App Registration (AUTOMATED via Firebase CLI)

```bash
firebase apps:create ANDROID "Wego Staging (Debug)" --package-name com.wego.android.staging --project wego-mobile-apps-staging
```

Then re-download the config which will now include both `com.wego.android` and `com.wego.android.staging` client entries.

The existing `wegoapk/google-services.json` (production) stays as the fallback for release builds.

## Items Verified as SAFE (No Changes Needed)

| Item | Location | Why Safe |
|------|----------|----------|
| FileProvider authority | wegoapk manifest line 258 | Uses `${applicationId}.provider` |
| Class.forName() calls | ActivityHelperBase.java, CommonUtils.kt, etc. | Java namespace ≠ applicationId |
| Deep link schemes | Various manifests | Use `wego://`, `https://`, not package-based |
| Commented-out code | Manifest lines 67, 168, 184 | Not active |
| `<queries>` self-reference | Manifest line 485 | Allows staging to discover production app — desirable |
| BuildConfig fields | libbase/build.gradle | Already split by buildType (STAGING_* vs production) |
| Auth deep links | wegoauth manifest | Uses host-based routing, not package-based |
| App icons | libbase/src/debug/res/ | Already different per buildType |

## Execution Order

1. Create and checkout branch
2. Modify `wegoapk/build.gradle` — add `applicationIdSuffix` + `firebaseCrashlytics` to debug
3. Fix hardcoded package references in `wegoapk/src/main/AndroidManifest.xml`
4. Register `com.wego.android.staging` in staging Firebase project (via CLI)
5. Download staging `google-services.json` and place at `wegoapk/src/debug/google-services.json`
6. Build and verify

## Test Plan

1. Build `playstoreDebug` variant — verify it produces APK with `com.wego.android.staging` package
2. Build `playstoreRelease` variant — verify it still uses `com.wego.android`
3. Install both APKs on same device — verify side-by-side installation works
4. Verify staging icons appear on debug build
5. Run unit tests: `./gradlew :wegoapk:testPlaystoreDebugUnitTest`
6. Verify `google-services.json` at `wegoapk/src/debug/` points to staging Firebase project
7. Verify Crashlytics reports from staging build to staging Firebase project

## Acceptance Criteria

- [ ] Debug builds use applicationId `com.wego.android.staging`
- [ ] Release builds continue using `com.wego.android`
- [ ] Both APKs installable side-by-side
- [ ] Manifest permission/category references use `${applicationId}`
- [ ] Staging `google-services.json` placed at `wegoapk/src/debug/google-services.json`
- [ ] `com.wego.android.staging` registered in staging Firebase project
- [ ] Crashlytics enabled for debug buildType
- [ ] Crashlytics reports from staging builds to staging Firebase project
- [ ] No runtime crashes from the package name change
