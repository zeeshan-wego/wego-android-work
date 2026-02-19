## Current State
- **Phase:** 5 (Done)
- **Task:** MOBILE-8090 - Create separate package for staging build
- **Branch:** feature/mobile-8090-staging-package-suffix
- **PR:** https://github.com/wego/wego-android-n/pull/1930
- **Last Action:** All verifications passed, PR created

## Files Changed
| File | Change |
|------|--------|
| `wegoapk/build.gradle` | Added `applicationIdSuffix ".staging"` + `firebaseCrashlytics` block to debug buildType |
| `wegoapk/src/main/AndroidManifest.xml` | Replaced 3 hardcoded `com.wego.android` refs with `${applicationId}` |
| `wegoapk/src/debug/google-services.json` | **New** — Staging Firebase config (both `com.wego.android` and `com.wego.android.staging` clients) |
| `wegoapk/src/debug/agconnect-services.json` | **New** — AGConnect config with staging package name |

## Firebase Actions
- Registered `com.wego.android.staging` in staging Firebase project (`wego-mobile-apps-staging`)
- App ID: `1:14941031996:android:7440592f9fe81c0bf7fd39`
- Downloaded staging `google-services.json` via Firebase CLI

## Verification Results
| # | Test | Result |
|---|------|--------|
| 1 | Debug APK package is `com.wego.android.staging` | PASS |
| 2 | Release APK package is `com.wego.android` | PASS |
| 3 | Both APKs installed side-by-side on same device | PASS |
| 4 | Crashlytics initializes for `com.wego.android.staging` on staging Firebase | PASS |
| 5 | Unit tests pass | PASS |

## Q&A Log
- Q: Build type approach? → A: Add applicationIdSuffix to existing debug buildType
- Q: Different app name/icon? → A: Already have different icons for staging
- Q: Firebase on staging? → A: Staging Firebase project exists with `com.wego.android` registered, but no google-services.json in project
- Q: Class.forName() calls? → Verified SAFE (Java namespace ≠ applicationId)
- Q: Crashlytics config? → Only in release block, added to debug block too
- Q: Can we automate Firebase setup? → Yes, Firebase CLI used to register app + download config
- Q: AGConnect build failure? → Created debug-specific agconnect-services.json with staging package name
