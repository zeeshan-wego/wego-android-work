# [Android] Replace GlobalScope.launch with lifecycle-aware scopes

**Date:** 2026-04-28 | **Developer:** zeeshan@wego.com | **Platform:** Android_Frontend

**What:** (in progress — `GlobalScope.launch` in three production sites detaches coroutines from host lifecycle, leaking work and risking post-destruction crashes.)

**Fix:** (in progress — convert `Authenticator.refreshToken` to a suspend fun, switch `BaseAuthActivity.trackLoginSignup` to `lifecycleScope`, and use `rememberCoroutineScope()` in the `wegoPromo` composable.)
