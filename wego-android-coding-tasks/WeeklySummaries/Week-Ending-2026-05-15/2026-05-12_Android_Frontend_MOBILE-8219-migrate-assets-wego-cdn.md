# MOBILE-8219: Cleanup assets.wego.com hardcoded references

**Date:** 2026-05-12 | **Developer:** zeeshan@wego.com | **Platform:** Android_Frontend

**Ticket:** https://wegomushi.atlassian.net/browse/MOBILE-8219

**What:** Hardcoded `assets.wego.com` URLs scattered across `@Preview` Compose blocks and stale comments polluted repo-wide greps and would muddy the eventual asset CDN migration once the new host is confirmed by backend/infra.

**Fix:** Replaced 31 `@Preview` URL literals across 4 files with neutral `example.com/preview/...` placeholders, deleted 6 stale legacy-URL comments, refreshed 8 affected `detekt` baseline fingerprints. `config_defaults.json` deliberately left untouched (deferred until new CDN host confirmed). Detekt + unit tests + smoke tests all green.
