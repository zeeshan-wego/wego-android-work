# FMETA-2579: Foldable Device Support — PoC Report

**Branch:** [`feature/fmeta-2579-foldable-poc`](https://github.com/wego/wego-android-n/tree/feature/fmeta-2579-foldable-poc)
**Author:** bima@wego.com
**Date:** 2026-04-27
**Status:** PoC complete (Phase 1 + Phase 2 experiment). Standalone branch — not merged to `develop`.

---

## Table of Contents

1. [Goal](#1-goal)
2. [Required Libraries](#2-required-libraries)
3. [Architecture Overview](#3-architecture-overview)
4. [Implementation Approach](#4-implementation-approach)
5. [PoC Walkthrough](#5-poc-walkthrough)
6. [Issues Encountered & Resolutions](#6-issues-encountered--resolutions)
7. [SlidingPaneLayout Internals — Key Learnings](#7-slidingpanelayout-internals--key-learnings)
8. [Open Items](#8-open-items)
9. [Summary: Findings, Notes & Gotchas](#9-summary-findings-notes--gotchas)
10. [Phase 2 Scope (Deferred)](#10-phase-2-scope-deferred)
11. [References](#11-references)

---

## 1. Goal

Run a focused experiment to answer two questions:

1. **Can we add foldable device support to the Wego Android app without a major rewrite?**
2. **What does a master-detail pattern look like in the flight search result flow, and where does the existing code need to change?**

The scope was deliberately narrow:
- Flight search result flow only (not hotels, home, etc.)
- No design reference — use good judgement on layout
- No new module — integrate within the existing `flights` module
- Keep on a standalone branch; never merge to `develop`

**Target user flow on a foldable (unfolded):**
- Left pane → search result list
- Right pane → flight details on tap (replacing Sort & Filter, which is deferred to Phase 2)
- Fold/unfold → smooth automatic transition, no crash

**Out of scope for this PoC:**
- Sort & Filter in the right pane (Phase 2)
- Booking flow changes (continues in a new Activity as before)
- Design polish / Wego Design System compliance

---

## 2. Required Libraries

### `androidx.slidingpanelayout:slidingpanelayout:1.2.0`

**What it is:** An AndroidX layout component that hosts exactly two child views — a primary (list) pane and a detail pane — and automatically decides whether to render them side-by-side or as a single sliding pane based on available screen width.

**Why we chose it:** It is Google's recommended primitive for adaptive two-pane layouts on foldable devices [1]. Version 1.2.0 integrates with Jetpack WindowManager (`FoldingFeature`) out of the box [2], so the fold/unfold transition is handled automatically without extra WindowManager code.

**How it decides the layout mode:**

`SlidingPaneLayout` computes the mode in `onMeasure()` by comparing the available screen width against the **sum of the minimum widths** of its two children (set via `layout_width` in XML or `SlidingPaneLayout.LayoutParams.width` programmatically):

```
Available width ≥ sum of minimum widths → Two-pane (non-slideable)
Available width  < sum of minimum widths → Single-pane (slideable)
```

`isSlideable()` returns the current mode. `weight` distributes leftover space proportionally (like `LinearLayout`).

**Key API:**

| Method | What it does |
|---|---|
| `isSlideable()` | `true` = single-pane (narrow/folded), `false` = two-pane (wide/unfolded) |
| `open()` | In single-pane: animates detail pane into view. In two-pane: no visual effect, but sets `mPreservedOpenState = true` (important for fold transitions — see §7) |
| `close()` | In single-pane: animates list pane back into view. In two-pane: no-op |
| `isOpen()` | In single-pane: reflects which pane is visible. In two-pane: always `true` |
| `addPanelSlideListener()` | Fires during sliding animation only — does NOT fire on fold/unfold |

The official guide notes: > "SlidingPaneLayout always lets you manually call `open()` and `close()` to transition between the list and detail panes on phones. These methods have no effect if both panes are visible and don't overlap." [1]

**Fold/unfold lifecycle:**

```
Fold event (window narrows):
  onMeasure()     → mCanSlide recalculated (now true — single-pane)
  onSizeChanged() → mFirstLayout = true
  onLayout()      → mSlideOffset = mCanSlide && mPreservedOpenState ? 0.f : 1.f
                    (0 = detail visible, 1 = list visible)

Unfold event (window widens):
  onMeasure()  → mCanSlide = false (two-pane again)
  onLayout()   → both panes rendered at fixed widths; mSlideOffset irrelevant
```

Fragments in the detail pane survive fold/unfold — only the visual position changes.

**Minimum widths we used:**

| Pane | Minimum width | Rationale |
|---|---|---|
| List (left) | 320 dp | Enough for search result cards |
| Detail (right) | 300 dp | Enough for flight details |
| Combined | 620 dp | Exceeds folded Pixel Fold inner display (~408 dp) → single-pane on fold |
| | | Fits unfolded inner display (~841 dp) → two-pane on unfold |

---

## 3. Architecture Overview

### Before — Existing flight search flow

```
FlightSearchActivity (Java)
  └── startActivity → FlightSearchResultActivity (Java)    ← entry point
        └── FlightSearchResultFragment (Java)              ← host: sort/filter bar + list
              ├── FlightSearchResultListFragment            ← result list
              ├── SortOptionsBottomSheet (Kotlin)           ← sort: shown as BottomSheet
              └── FlightFilterBottomSheet (Kotlin)          ← filter: BottomSheetDialogFragment

On flight tap (FlightSearchResultsPresenter ~line 1818):
  startActivityForResult → FlightDetailsActivity (Java)
                             └── FlightDetailsFragment (Java)
```

**Key constraints discovered:**
- All search result and details code is **Java**. Filter/sort wrappers are Kotlin.
- `FlightSearchResultActivity.onCreate()` always overrides `mLayoutRes` before `super.onCreate()`, preventing subclasses from setting a custom layout via that mechanism.
- `setContentViewWithSlidingMenus()` in `WegoBaseCoreActivity` (Kotlin) is not `open` and cannot be overridden from Java.
- `FlightDetailsFragment` had a hard cast to `FlightDetailsActivity` to access `getEmailMeButton()`.

---

### After — Foldable path

The foldable Activity replaces the standard one as the entry point (PoC branch only). The existing `FlightSearchResultActivity` and `FlightDetailsActivity` remain untouched for the narrow-screen path.

```
FlightSearchActivity (Java)
  └── startActivity → FlightSearchResultFoldableActivity (Java)   ← NEW entry point
        │
        ├── [left pane]  FlightSearchResultFragment (Java)        ← reused unchanged
        │     ├── FlightSearchResultListFragment
        │     ├── SortOptionsBottomSheet (Kotlin)    ← single-pane path only
        │     └── FlightFilterBottomSheet (Kotlin)   ← single-pane path only
        │
        └── [right pane] pane_detail FrameLayout
              ├── EmptyDetailPaneFragment             ← default: no flight selected
              ├── FlightDetailsFragment (Java)        ← loaded on flight tap (two-pane)
              └── MockFilterSortFragment (Java)       ← Phase 2 experiment

On flight tap:
  Wide screen  (unfolded, isSlideable=false) → showDetailInPane()
                                               → FlightDetailsFragment in right pane (no new Activity)
  Narrow screen (folded,  isSlideable=true)  → startActivityForResult
                                               → FlightDetailsActivity (unchanged)

On device fold while detail is visible:
  onConfigurationChanged() → closePane() → list pane shown
On device unfold:
  Both panes restored automatically; detail fragment already alive in pane_detail
```

**New files introduced:**

| File | Type | Purpose |
|---|---|---|
| `FlightSearchResultFoldableActivity.java` | Activity | Hosts the SlidingPaneLayout; entry point for foldable |
| `FlightDetailsPaneHost.java` | Interface | Decouples `FlightDetailsFragment` from a hard cast to `FlightDetailsActivity` |
| `EmptyDetailPaneFragment.java` | Fragment | "No trip selected" placeholder in the right pane |
| `MockFilterSortFragment.java` | Fragment | Phase 2 experiment: mock filter/sort in the right pane |

---

### Full structure diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  FlightSearchResultFoldableActivity                                          │
│                                                                              │
│  ── action bar (full-width, above SlidingPaneLayout) ──────────────────────  │
│  ── sort / filter bar (full-width, above SlidingPaneLayout) ───────────────  │
│                                                                              │
│  ┌─────────────────── SlidingPaneLayout ─────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ┌─────────────────────────┐    ┌──────────────────────────────────┐  │  │
│  │  │       LEFT PANE         │    │          RIGHT PANE              │  │  │
│  │  │    (always visible)     │    │   (hidden until results arrive)  │  │  │
│  │  │                         │    │                                  │  │  │
│  │  │  FlightSearchResult     │    │  ┌────────────────────────────┐  │  │  │
│  │  │  Fragment               │    │  │  EmptyDetailPaneFragment   │  │  │  │
│  │  │  ├ ResultListFragment   │    │  │  (default — no selection)  │  │  │  │
│  │  │  ├ SortOptions (*)      │    │  └────────────────────────────┘  │  │  │
│  │  │  └ FilterBottomSheet(*) │    │            ── or ──              │  │  │
│  │  │                         │    │  ┌────────────────────────────┐  │  │  │
│  │  │  (*) narrow screen only │    │  │  FlightDetailsFragment     │  │  │  │
│  │  │                         │    │  │  (on flight tap)           │  │  │  │
│  │  └─────────────────────────┘    │  └────────────────────────────┘  │  │  │
│  │                                 │            ── or ──              │  │  │
│  │  min-width: 320 dp              │  ┌────────────────────────────┐  │  │  │
│  │                                 │  │  MockFilterSortFragment    │  │  │  │
│  │                                 │  │  (Phase 2 experiment)      │  │  │  │
│  │                                 │  └────────────────────────────┘  │  │  │
│  │                                 │                                  │  │  │
│  │                                 │  min-width: 300 dp               │  │  │
│  │                                 └──────────────────────────────────┘  │  │
│  │                                                                        │  │
│  │  Unfolded (~841 dp) : combined 620 dp fits → both panes side-by-side  │  │
│  │  Folded   (~408 dp) : combined 620 dp > 408 dp → single-pane          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Implementation Approach

### Why not a custom XML layout

The cleanest approach would be to define the `SlidingPaneLayout` in an XML file and inflate it via `mLayoutRes` — this is also Google's recommended pattern [1]. It was **not possible** because `FlightSearchResultActivity.onCreate()` unconditionally overwrites `mLayoutRes = activity_international_actionbar` before calling `super.onCreate()`, and the inflation method cannot be overridden from a Java subclass.

**Workaround used:** `FlightSearchResultFoldableActivity` calls `super.onCreate()` (which inflates the standard layout), then immediately calls `setupSlidingPane()`, which:

1. Finds `rootContainer` (the full-screen `FrameLayout` in the inflated layout)
2. Removes it from its parent (`layout_root`)
3. Creates a `SlidingPaneLayout` programmatically with `rootContainer` as the left pane and a new `FrameLayout` as the right pane
4. Re-inserts the `SlidingPaneLayout` at the original index in `layout_root`

The action bar and sort/filter bar remain as siblings of the `SlidingPaneLayout` in `layout_root`, so they still overlay correctly.

### Interface introduced: `FlightDetailsPaneHost`

`FlightDetailsFragment` previously hard-cast `getActivity()` to `FlightDetailsActivity` to call `getEmailMeButton()`. A minimal interface was introduced to decouple it:

```java
public interface FlightDetailsPaneHost {
    View getEmailMeButton();
}
```

`FlightDetailsActivity` implements it (existing method, just added `implements`). `FlightSearchResultFoldableActivity` also implements it (returns `null` — email share is non-critical for the PoC). `FlightDetailsFragment` checks `instanceof FlightDetailsPaneHost` instead of `instanceof FlightDetailsActivity`.

### Entry point

`FlightSearchActivity` was modified to route to `FlightSearchResultFoldableActivity` instead of `FlightSearchResultActivity`. This is a PoC-only change on the standalone branch.

---

## 5. PoC Walkthrough

### Phase 1 — Core two-pane layout (completed)

**Step 1 — Dependencies**

Added `androidx.slidingpanelayout:slidingpanelayout:1.2.0` to `gradle/libs.versions.toml` and `flights/build.gradle`.

**Step 2 — `FlightDetailsPaneHost` interface**

New file: `FlightDetailsPaneHost.java`. Decouples `FlightDetailsFragment` from `FlightDetailsActivity`. Both `FlightDetailsActivity` and the new `FlightSearchResultFoldableActivity` implement it.

**Step 3 — `FlightSearchResultFoldableActivity`**

New Activity extending `FlightSearchResultActivity`. The core of the PoC. Key methods:

```java
// Programmatically wraps the existing layout in a SlidingPaneLayout
private void setupSlidingPane() { ... }

// Returns true when SPL is in two-pane (non-slideable) mode
public boolean isTwoPaneMode() {
    return !mSlidingPaneLayout.isSlideable();
}

// Called by the presenter instead of startActivityForResult in two-pane mode
public void showDetailInPane(Bundle extras) { ... }
```

**Step 4 — Presenter routing**

`FlightSearchResultsPresenter.java` (~line 1818) — added a fork: if the host activity is `FlightSearchResultFoldableActivity` and `isTwoPaneMode()`, call `showDetailInPane(bundle)` instead of launching `FlightDetailsActivity`:

```java
if (activity instanceof FlightSearchResultFoldableActivity
        && ((FlightSearchResultFoldableActivity) activity).isTwoPaneMode()) {
    ((FlightSearchResultFoldableActivity) activity).showDetailInPane(detailBundle);
} else {
    // existing narrow-screen path — unchanged
    ((Fragment) getView()).startActivityForResult(intent, REQ_CODE);
}
```

**Step 5 — Manifest registration**

`FlightSearchResultFoldableActivity` registered in `flights/AndroidManifest.xml` with `resizeableActivity="true"` and `configChanges="screenSize|smallestScreenSize|screenLayout|orientation"` (so fold events call `onConfigurationChanged` instead of recreating the Activity).

**Step 6 — Entry point swap**

`FlightSearchActivity.java` routes to `FlightSearchResultFoldableActivity`.

---

### Phase 1 additions — UX polish (completed)

After device testing, several UX issues were identified and fixed:

**Fold → show list pane (P1-A)**

Override `onConfigurationChanged()`. Posts `closePane()` after the layout pass that applies the new window size:

```java
@Override
public void onConfigurationChanged(Configuration newConfig) {
    super.onConfigurationChanged(newConfig);
    mSlidingPaneLayout.post(() -> {
        if (mSlidingPaneLayout.isSlideable()) mSlidingPaneLayout.closePane();
    });
}
```

Without this, folding defaults to whichever pane the user last touched (SPL's `mPreservedOpenState` behaviour — see §7).

**Close button on detail pane (P1-C)**

An `ImageButton` overlay is added to `pane_detail` during setup. It sits at the top-right, always as the last child (highest z-order) of the `FrameLayout`. On tap: pops the backstack, removes the base fragment, calls `closePane()` if slideable.

Because `FragmentManager.replace()` appends the incoming fragment's view as the last child (highest z-order), the close button must be **re-appended** after each `commitNow()` — `bringToFront()` alone is insufficient since `commitNow()` is synchronous and the fragment's view re-covers the button.

**Empty state (P1)**

`EmptyDetailPaneFragment` — displayed when the detail pane has no selection ("No trip selected" + plane icon). Shown after the close button is tapped or when a filter change clears the previous detail.

**Clear detail on filter change (P1-D)**

`OnFilterChangedListener` added to `FlightSearchResultFragment`. Fired from `FlightSearchResultsPresenter` after `changeFilter()`. The activity calls `clearDetailPane()` when a filter changes in two-pane mode, preventing a stale detail from showing alongside an updated result list.

Filter chip taps (the horizontal chip bar) are also intercepted via `RecyclerView.SimpleOnItemTouchListener` on `ACTION_DOWN`, clearing the detail immediately for instant visual feedback.

---

### Phase 2 experiment — Right-pane navigation model (completed)

Goal: observe how the `FragmentManager` backstack behaves when the right pane hosts multiple fragment destinations.

**`MockFilterSortFragment`** — a static placeholder fragment with a title bar, close button, and mock filter chips. Not functional. Added to demonstrate the filter-in-pane navigation pattern.

**Navigation model implemented:**

| Destination | Method | Backstack |
|---|---|---|
| Flight details | `showDetailInPane()` — `replace()`, no backstack | Base (no entry) |
| Mock filter/sort | `showFilterInPane()` — `replace()` + `addToBackStack("filter")` | Stackable on top of detail |

**Key observation from the experiment:**

The `FragmentManager` backstack is **global across all containers** in the Activity. In single-pane (folded) mode, if the right pane container has a backstack entry and the user presses back, the entry is popped — but since the right pane is hidden, nothing appears to change on screen ("ghost back press"). Per-pane backstack isolation requires explicit management via a custom `OnBackPressedCallback` or the Jetpack Navigation Component [3].

Our custom `OnBackPressedCallback` handles this:
- Two-pane + backstack entries → pop filter, reveal detail
- Otherwise → clear right-pane stack silently, then `finish()` the Activity

---

## 6. Issues Encountered & Resolutions

| # | Issue | Root cause | Resolution |
|---|---|---|---|
| 1 | Foldable layout not inflating — wrong Activity launched | `FlightSearchResultActivity.onCreate()` overwrites `mLayoutRes` before subclass runs | Switched from XML layout to programmatic `SlidingPaneLayout` setup in `setupSlidingPane()` after `super.onCreate()` |
| 2 | Empty right pane takes 50% width even when no flight selected | Both SPL children had `layout_width=0dp` (weight-only) → combined minimum = 0 → `isSlideable()` always `false` | Changed to concrete minimum widths: 320dp (list) + 300dp (detail) = 620dp combined |
| 3 | Crash: `NullPointerException` in `FlightDetailsFragment.onResume` | `FlightDetailsPresenter` not created → `presenter` field null → `presenter.start()` crashes | `showDetailInPane()` now mirrors `FlightDetailsActivity.onCreate()` — creates `FlightDetailsPresenter` before `commitNow()` |
| 4 | Right pane persists on fold (phone mode, squished layout) | Same root cause as issue 2 — combined min = 0 → never single-pane | Same fix as issue 2 (concrete min widths) |
| 5 | Departure & arrival section missing for first few flights | Race condition: `FlightDetailsPresenter` created before fragment is attached → `getActivity()` null → `isValidActivity()` false → silent bail | Added leg-resolvability pre-check in `showDetailInPane()` before creating fragment/presenter |
| 6 | Departure/arrival not visible on flight tap; panes appear scroll-linked | `mPreservedOpenState = false` on GONE→VISIBLE transition → after mode switch to single-pane, `mSlideOffset = 1.0` (list shown); `ViewDragHelper` intercepted RecyclerView horizontal scroll as a pane-open gesture | Call `open()` unconditionally after `commitNow()` → sets `mPreservedOpenState = true` → `mSlideOffset = 0.0` on transition |
| 7 | Fold defaults to last-touched pane instead of list pane | SPL's `onInterceptTouchEvent()` writes `mPreservedOpenState` based on which pane received the last `ACTION_DOWN` touch, then fold reads it | Override `onConfigurationChanged()`: post `closePane()` after layout, which sets `mPreservedOpenState = false` regardless of last touch |
| 8 | Right pane visible during loading (loading screen not full-width) | `SlidingPaneLayout.updateObscuredViewsVisibility()` promotes `View.GONE` → `VISIBLE` on first `onLayout()` — SPL owns the INVISIBLE/VISIBLE axis and does not preserve user-set `GONE` | **OPEN / PARKED** — three fix options identified (see §8) |

---

## 7. SlidingPaneLayout Internals — Key Learnings

These behaviours are non-obvious and are not prominently documented.

### `mPreservedOpenState` — the fold memory

SPL tracks which pane should be visible after a fold event in a boolean field `mPreservedOpenState`. It is updated by three sources:

1. **`open()` / `close()`** — `openPane()` sets it `true`; `closePane()` sets it `false`
2. **Touch** — every `ACTION_DOWN` in two-pane mode sets it to `true` if the detail pane was touched, `false` if the list pane was touched
3. **Focus (non-touch mode)** — `requestChildFocus()` updates it based on which pane received focus

On fold, `onLayout()` reads it: `mSlideOffset = mCanSlide && mPreservedOpenState ? 0 : 1`.

**Implication:** Calling `close()` in `onConfigurationChanged()` — after the layout pass has applied the new window size — reliably forces the list pane on every fold, regardless of what the user last touched.

### `open()` / `close()` in two-pane mode

> "These methods have no effect if both panes are visible and don't overlap." [1]

This refers to the **animation/sliding axis only** — in two-pane mode, nothing moves visually. However, both methods always write `mPreservedOpenState`, which controls which pane is shown after a subsequent fold event. Calling `open()` unconditionally after loading a fragment into the detail pane is correct — it primes the fold-memory so that if the user folds with a detail visible, the detail pane is shown (not the list).

### `View.GONE` on a SPL child is not safe

SPL's internal `updateObscuredViewsVisibility()` method is called from every `onLayout()`. It only operates on the `INVISIBLE` ↔ `VISIBLE` axis — it does not check for or preserve `GONE`. Any child that is not fully obscured by another pane will be promoted to `VISIBLE` on the very first layout pass, regardless of what the developer set.

The official guide's recommended solution for the "empty right pane on launch" problem is a placeholder fragment that is always present [1]:

> "The `android:name` attribute on `FragmentContainerView` adds the initial fragment to the detail pane, ensuring that users on large-screen devices don't see an empty right pane when the app first launches." [1]

**Consequence for our PoC:** `View.GONE` cannot be used to hide the detail pane during loading — SPL overrides it during its own first layout pass. See §8 for fix options.

### Fragment backstack is global — not per-pane

`FragmentManager` has a single backstack across all fragment containers in an Activity. In single-pane mode, popping a backstack entry for a fragment in the hidden right pane results in a "ghost back press" — the pop succeeds but the user sees nothing change. Per-pane navigation isolation requires explicit `OnBackPressedCallback` management or the Jetpack Navigation Component's `AbstractListDetailFragment` [3].

### `addPanelSlideListener` does not fire on fold/unfold

`PanelSlideListener` fires only when the pane is physically sliding (in single-pane mode). It does not fire when the window resizes due to a fold event. Use `onConfigurationChanged()` to detect fold transitions.

### Close button z-order with `FragmentManager`

`FragmentManager.replace()` appends the incoming fragment's root view as the **last child** of the container `FrameLayout` (highest z-order). Any overlay view (e.g. a close button) added to the same `FrameLayout` before the fragment transaction will be rendered below the fragment's view. The solution: after `commitNow()`, explicitly remove and re-add the overlay button — this makes it the new last child and guarantees it renders on top.

---

## 8. Open Items

### Issue #8 — Loading screen not full-width

**Current behaviour:** On an unfolded foldable, the right pane (detail) is visible during the search loading screen, splitting the screen 50/50 before any results have arrived.

**Root cause:** `SlidingPaneLayout.updateObscuredViewsVisibility()` promotes `View.GONE` → `VISIBLE` on the first `onLayout()` call after `addView(detailPane)`. SPL owns child visibility on the `INVISIBLE`/`VISIBLE` axis and does not preserve developer-set `GONE`.

Google's recommended approach avoids this by never hiding the pane — a placeholder fragment is always present [1]:

> "ensuring that users on large-screen devices don't see an empty right pane when the app first launches" [1]

**Three fix options:**

| Option | Description | Effort | Risk |
|---|---|---|---|
| **A** | Always-present placeholder + full-bleed loading overlay drawn above SPL | Medium | Low — idiomatic [1] |
| **B** | Pane always VISIBLE; loading overlay sibling view covers both panes until results arrive | Low | Low |
| **C** | Defer `addView(detailPane)` until results arrive via `OnFirstResultsListener` | Low | Medium — non-idiomatic, verify on real foldable |

Option C is empirically confirmed to work (removing `addView` eliminates the right pane). Option A is Google's canonical pattern [1].

**Decision:** Parked for this PoC. Acceptable trade-off — the loading screen is a transient state with no actionable content for the right pane. Fix required before production use.

---

## 9. Summary: Findings, Notes & Gotchas

### What works well

- **Fold/unfold transition is free.** `SlidingPaneLayout` re-measures on window resize and smoothly transitions between single-pane and two-pane. No WindowManager code required for the basic case.
- **Fragments survive fold/unfold.** The detail fragment in `pane_detail` is never destroyed by a fold event. The view is preserved. "Restore right pane on unfold" is automatic.
- **The presenter routing change is minimal.** Three lines in `FlightSearchResultsPresenter.java` — an `instanceof` check and a method call — route to the right pane on wide screens with zero change to the existing narrow-screen path.
- **`FlightDetailsPaneHost` decoupling is clean.** A two-line interface eliminates the hard cast in `FlightDetailsFragment` with no functional change to the existing flow.

### What required significant work

- **The parent class XML inflation constraint.** The inability to use a custom layout XML forced the programmatic `setupSlidingPane()` workaround. This is the single biggest source of complexity in the PoC and the root of several downstream issues. A production implementation should resolve this constraint (extract the layout inflation or migrate to a non-overriding base).
- **`FlightDetailsPresenter` lifecycle coupling.** The presenter must be created before `commitNow()` — this mirrors `FlightDetailsActivity.onCreate()` logic that had to be replicated in the foldable Activity. Tight MVP coupling makes reuse harder than it should be.
- **Fragment z-order management.** The close button overlay needing explicit re-append after every fragment transaction is a fragile pattern. Any future fragment additions to the right pane must follow the same convention.

### Gotchas

1. **`isSlideable()` changes on fold — but not synchronously.** `onConfigurationChanged()` fires before the layout pass. Always post pane operations (`closePane()`) so they run after `isSlideable()` has been updated by the new measurement.

2. **`View.GONE` does not work as a pane visibility toggle in SPL.** SPL's `updateObscuredViewsVisibility()` will always overwrite it on the first layout pass. Use SPL's own `open()`/`close()` in single-pane mode; use an overlay view or a deferred `addView()` for the loading screen scenario.

3. **`open()` in two-pane mode is not pointless.** It sets `mPreservedOpenState = true`, which controls which pane is shown after a fold. Always call `open()` when loading a flight detail into the right pane, even if `isSlideable()` is currently `false`.

4. **Combined minimum width determines the foldable breakpoint.** Get this wrong (e.g. using `layout_width=0dp` on both panes) and `isSlideable()` will never return `true` regardless of screen width. Set concrete minimum widths that straddle the folded and unfolded display widths of your target device.

5. **FragmentManager backstack is global.** In single-pane mode, popping a backstack entry for the hidden right pane produces no visible change ("ghost press"). Always intercept back presses with `OnBackPressedCallback` and handle the right pane's stack explicitly.

6. **`FlightDetailsPresenter` must be created before `commitNow()`.** `AbstractPresenter`'s constructor calls `view.setPresenter(this)`. `commitNow()` drives the fragment to `RESUMED` synchronously, which calls `presenter.start()`. If the presenter hasn't been created by then, it crashes.

7. **The action bar and sort/filter bar remain full-width overlays.** Since the SPL is inserted as a sibling (not parent) of these bars, they span both panes. The detail pane must have its top padding adjusted at runtime (`adjustDetailPaneForOverlays()`) to push content below the overlaying bars. This must be re-applied whenever the detail pane is revealed.

### Effort assessment vs. initial estimate

| Phase | Estimated SP | Actual complexity notes |
|---|---|---|
| Phase 1 core | 13 SP | The layout inflation constraint added ~2 sessions of unexpected debugging |
| Phase 1 UX polish | Included | Close button z-order, fold defaults, filter-chip clear — each straightforward once root causes were understood |
| Phase 2 experiment | 12 SP (deferred) | Navigation model experiment completed as a lightweight mock (`MockFilterSortFragment`) — backstack behavior confirmed |

### Recommended next steps for production

1. **Resolve the layout inflation constraint** in `FlightSearchResultActivity` / `WegoBaseCoreActivity` to allow a proper XML-defined `SlidingPaneLayout`. This unlocks Google's canonical pattern [1] and eliminates the fragile programmatic setup.
2. **Fix Issue #8** (loading screen full-width) using Option A or B.
3. **Phase 2** — replace `MockFilterSortFragment` with real sort/filter content in the right pane (see §10).
4. **Evaluate `AbstractListDetailFragment`** (`androidx.navigation:navigation-fragment`) as a long-term replacement for the custom pane management [3] — it handles backstack isolation, placeholder destinations, and the loading pattern correctly out of the box.

---

## 10. Phase 2 Scope (Deferred)

Phase 2 brings sort/filter into the right pane (12 SP estimated):

| Item | Notes | SP |
|---|---|---|
| `fragment_flight_sort_filter_pane.xml` | Plain Fragment layout (no bottom sheet chrome) for the filter/sort content | 2 |
| `FlightSortFilterPaneFragment.kt` | Real implementation replacing `MockFilterSortFragment`; intercept sort/filter taps; dual path: right pane in two-pane mode, existing bottom sheet in single-pane | 8 |
| Extend `showFilterInPane()` | Wire to real `FlightSortFilterPaneFragment` | 2 |

**Key risk in Phase 2:** The sort/filter bottom sheet (`FlightFilterBottomSheet`) has ~60 wired listeners and a complex state machine. Extracting it into a plain Fragment without the bottom sheet wrapper is the bulk of the Phase 2 work.

---

## 11. References

[1] Google Android Developers — *Create a two-pane layout with SlidingPaneLayout*
https://developer.android.com/develop/ui/views/layout/slidingpanelayout

[2] AndroidX Release Notes — *SlidingPaneLayout 1.2.0*
https://developer.android.com/jetpack/androidx/releases/slidingpanelayout

[3] AndroidX Navigation — *AbstractListDetailFragment*
https://developer.android.com/reference/androidx/navigation/fragment/AbstractListDetailFragment

[4] Google Android Developers — *Support large screens with SlidingPaneLayout*
https://developer.android.com/guide/topics/large-screens/support-different-screen-sizes

---

*Full implementation log, including all session-by-session decisions, root cause analyses, and code snippets: see [`implementation-log.md`](./implementation-log.md) in this task folder.*
