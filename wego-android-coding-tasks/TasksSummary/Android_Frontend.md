# Android_Frontend Tasks Summary

## Week Ending: May 1, 2026

| Task | Owner | Started | Completed | Description | Weekly Summary |
|------|-------|---------|-----------|-------------|----------------|
| MOBILE-8192 [Android] Replace GlobalScope.launch with lifecycle-aware scopes | zeeshan@wego.com | Apr 28 | - | Convert `Authenticator.refreshToken` to suspend; `BaseAuthActivity.trackLoginSignup` → `lifecycleScope`; `wegoPromo` composable → `rememberCoroutineScope()`; add unit tests | [Link](../../WeeklySummaries/Week-Ending-2026-05-01/2026-04-28_Android_Frontend_MOBILE-8192-replace-globalscope-with-lifecycle-aware-scopes.md) |
| MOBILE-8206 Parallelise independent home screen sections to reduce TTI | zeeshan@wego.com | Apr 28 | Apr 28 | Remove `isSectionLoading` queue gate in `SectionsViewModel`; `loadData()` dispatches all sections in one pass so existing Rx `subscribeOn(io)` runs them concurrently; add unit tests for fan-out + ordering | [Link](../../WeeklySummaries/Week-Ending-2026-05-01/2026-04-28_Android_Frontend_MOBILE-8206-parallelise-home-sections.md) |

## Week Ending: April 24, 2026

| Task | Owner | Started | Completed | Description | Weekly Summary |
|------|-------|---------|-----------|-------------|----------------|
| MOBILE-8185 Edge-to-edge deprecated API migration (Android 15+) | muthuraman@wego.com | Apr 23 | - | Scope B: guard 34 Wego call sites with SDK<35 check; 5 helper edits + 2 new compat extensions + ~18 direct-site migrations + 2 new test files | [Link](../../WeeklySummaries/Week-Ending-2026-04-24/2026-04-23_Android_Frontend_MOBILE-8185-edge-to-edge-deprecated-apis.md) |
