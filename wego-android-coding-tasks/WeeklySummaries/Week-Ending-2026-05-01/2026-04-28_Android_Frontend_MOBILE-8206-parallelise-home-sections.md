# MOBILE-8206: Parallelise independent home screen sections to reduce TTI

**Date:** 2026-04-28 | **Developer:** zeeshan@wego.com | **Platform:** Android_Frontend
**Ticket:** https://wegomushi.atlassian.net/browse/MOBILE-8206

**What:** Home sections in `SectionsViewModel` loaded strictly sequentially due to a single `isSectionLoading` boolean gate, causing 2+ s of stalled below-the-fold rendering on cold start across ~30 sections.

**Fix:** Removed the queue gate; `loadData()` now dispatches all allowed sections in a single pass and the existing Rx `subscribeOn(io)` provides the parallelism. Net **−20 lines** in `SectionsViewModel.kt`; +11 unit tests covering fan-out, stable display-order insertion, and per-section error isolation. All four local gates green (compile, detekt, lint, full `:home` tests across 96 test classes).
