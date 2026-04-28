# MOBILE-8185: Migrate away from deprecated edge-to-edge APIs on Android 15+

**Date:** 2026-04-23 | **Developer:** muthuraman@wego.com | **Platform:** Android_Frontend

**What:** (in progress — Play Console flagged v7.47.0 for calling deprecated `Window.setStatusBarColor` / `setNavigationBarColor`; on Android 15+ these APIs are silent no-ops.)

**Fix:** (in progress — guard every Wego invocation with `SDK_INT < VANILLA_ICE_CREAM` (API 35) inside 5 shared helpers + 2 new `setStatusBarColorCompat` / `setNavigationBarColorCompat` extension helpers consumed by ~18 direct call sites across hotels, hotelsv2, flights, homebase, libbase modules.)
