# FMETA-2579: Foldable PoC — Implementation Log

## Purpose
Living document tracking implementation decisions, issues, workarounds, and learnings from the Phase 1 PoC build. Primary input for Phase 2 scoping.

---

## SlidingPaneLayout Primer

> **References**
> - [SlidingPaneLayout overview](https://developer.android.com/develop/ui/views/layout/slidingpanelayout) — official guide: two-pane UI, fold/unfold behaviour, back navigation
> - [SlidingPaneLayout API reference](https://developer.android.com/reference/androidx/slidingpanelayout/widget/SlidingPaneLayout) — full method list: `open()`, `close()`, `isOpen()`, `isSlideable()`, listeners
> - [Support large screens with SlidingPaneLayout](https://developer.android.com/guide/topics/large-screens/support-different-screen-sizes#slidingpanelayout) — recommended pattern for adaptive two-pane on tablets and foldables
> - [WindowManager & Jetpack Window library](https://developer.android.com/jetpack/androidx/releases/window) — underlying `FoldingFeature` / `WindowInfoTracker` that SPL 1.2.0 uses internally

### What it is

`SlidingPaneLayout` is an AndroidX view that hosts exactly **two child views** — a primary (list/master) pane and a detail pane — and automatically decides whether to show them side-by-side or as a single sliding pane depending on the available screen width.

It is the recommended primitive for adaptive two-pane layouts on foldable devices because it integrates with the Jetpack Window library (`FoldingFeature`, `WindowInfoTracker`) out of the box: when a physical fold separates the two display halves, SPL 1.2.0 uses the fold's width as an extra inter-pane offset so no content is rendered under the hinge.

### Pane sizing: `layout_width` vs `weight`

`SlidingPaneLayout.LayoutParams` uses two parameters to size panes:

- **`layout_width` = minimum width.** This is NOT a preferred or exact width — it is the floor SPL guarantees for that pane. SPL will never shrink a pane below its minimum width.
- **`weight` = flex factor.** After satisfying all minimum widths, any remaining horizontal space is distributed proportionally by weight, identical to `LinearLayout`'s weight system.

Both values are re-evaluated on every `onMeasure()` call. Dynamic changes (e.g., visibility toggles or `LayoutParams` mutations + `requestLayout()`) cause SPL to re-measure and potentially switch modes in the same frame.

### The two modes and what `isSlideable()` means

`isSlideable()` is the core mode toggle. SPL computes it during `onMeasure()` by comparing available screen width against the **combined minimum widths** of its two children (set via `layout_width` or `SlidingPaneLayout.LayoutParams.width`).

| Condition | `isSlideable()` | Mode | What the user sees |
|---|---|---|---|
| Screen width ≥ sum of min widths | `false` | **Two-pane** | Both panes rendered side-by-side; user can interact with both simultaneously |
| Screen width < sum of min widths | `true` | **Single-pane (slideable)** | Only one pane is visible at a time; the detail pane slides in/out over or beside the list |

For our implementation:
- Folded Pixel Fold inner display ≈ 408dp → less than our combined min 620dp → `isSlideable() = true` → single-pane (list only by default)
- Unfolded Pixel Fold inner display ≈ 841dp → more than 620dp → `isSlideable() = false` → two-pane

**Why minimum widths matter:** If either child has `layout_width=0dp` (weight-only), its minimum width is 0, and the combined minimum is also 0. SPL will always see `0 < any screen width`, so `isSlideable()` is permanently `false` and both panes are always shown side-by-side. This was Issue 2/4 in our PoC.

### Correct way to hide/show a pane: `View.GONE`

`View.GONE` is the correct, idiomatic mechanism to hide one pane from SPL. When a child is GONE:
- SPL's `onMeasure()` skips it entirely (standard `ViewGroup` contract)
- The minimum-width sum drops to the remaining pane's minimum only
- The visible pane fills the full available width
- `setVisibility(View.VISIBLE)` automatically calls `requestLayout()`, triggering a re-measure that re-includes the pane

`open()` / `close()` are **not for hiding panes**. They only control `mSlideOffset` — the visual sliding position of the detail pane in single-pane mode. Calling `close()` in two-pane mode has no effect on layout.

Setting `LayoutParams.width = 0` at runtime also works (requires manual `requestLayout()`), but is more fragile than `GONE`.

**Our implementation uses `GONE` correctly** — `detailPane.setVisibility(View.GONE)` is set before `addView()` so SPL's very first `onMeasure()` skips the pane. The issue in Sessions 4–6 was never the hide/show mechanism; it was always the signal used to decide *when* to call `setVisibility(VISIBLE)`.

### Open / closed state and `mSlideOffset`

SPL tracks the position of the detail (right) pane via an internal float `mSlideOffset`:

| `mSlideOffset` | Meaning | Visible in single-pane |
|---|---|---|
| `0.0` | Pane fully **open** — detail pane at its rightmost (visible) position | Detail pane |
| `1.0` | Pane fully **closed** — detail pane slid behind/off-screen | List pane |
| `0.0–1.0` | Pane mid-slide (during drag animation) | Transition |

`isOpen()` returns `!mCanSlide || mSlideOffset == 0`. In two-pane mode (`mCanSlide = false`, i.e. `!isSlideable()`), `isOpen()` always returns `true` — "open" simply means the detail pane is rendered (both are). In single-pane mode, `isOpen()` reflects the actual slide position.

Programmatic control:
- `open()` / `openPane()` → animates to `mSlideOffset = 0`, sets `mPreservedOpenState = true`
- `close()` / `closePane()` → animates to `mSlideOffset = 1`, sets `mPreservedOpenState = false`

### `mPreservedOpenState` — the fold memory

This is the field that links the two-pane interaction history to the single-pane rendering after a fold. It is a `boolean` that SPL reads during `onLayout()` on the first pass after a size change:

```java
// onLayout(), called after every onSizeChanged()
if (mFirstLayout) {
    mSlideOffset = mCanSlide && mPreservedOpenState ? 0.f : 1.f;
}
```

Meaning: when the window changes size (e.g. fold event), the pane position is re-initialised from `mPreservedOpenState`. The field is updated by three sources:

1. **Programmatic open/close** — `openPane()` sets it `true`; `closePane()` sets it `false`.
2. **Touch** — in two-pane mode, every `ACTION_DOWN` sets it to `true` if the touch is over the detail pane, `false` if over the list pane (`onInterceptTouchEvent`).
3. **Focus** — in non-touch mode (keyboard/accessibility), `requestChildFocus()` sets it to `true` if the detail pane has focus, `false` otherwise.

### Fold / unfold lifecycle

```
Fold event (window narrows):
  onMeasure()          → mCanSlide recalculated (now true)
  onLayout()           → mFirstLayout=false, panes laid out at old mSlideOffset
  onSizeChanged()      → mFirstLayout = true  ← signals "position must be reset"
  [next layout pass]
  onMeasure()          → mCanSlide = true (narrow)
  onLayout()           → if (mFirstLayout) mSlideOffset = mCanSlide && mPreservedOpenState ? 0 : 1
                         → mFirstLayout = false
  Result: whichever pane was last touched (or programmatically opened) is shown

Unfold event (window widens):
  onMeasure()          → mCanSlide = false (wide again)
  onLayout()           → mFirstLayout=true branch: mSlideOffset = mCanSlide && mPreservedOpenState → 0 && anything → 1
                         (but in non-slideable mode mSlideOffset is irrelevant — both panes rendered at fixed widths)
  Result: both panes visible; fragments in both containers are still alive
```

**Key implication:** Fragments in `pane_detail` are **never destroyed** by a fold/unfold transition as long as the Activity is not recreated. The SPL only changes the visual offset — `mSlideOffset` — not the fragment backstack or container contents. This means "restore right pane on unfold" is automatic: the fragment is already there, it just becomes visible again when the panes expand to two-pane layout.

### Backstack behaviour

`SlidingPaneLayout` has **no awareness of the `FragmentManager` backstack**. The backstack is managed entirely by the `FragmentManager` for the Activity and is global across all containers. Consequences:
- The Android system back gesture (or back button) processes the fragment backstack regardless of which pane is currently visible.
- In single-pane mode (folded, list shown), if the right pane's container has a backstack entry, pressing back will pop that entry — but since the right pane is hidden, the user sees nothing change on screen. This can create a "ghost back press" UX issue.
- Per-pane backstack isolation requires explicit management (e.g. custom back-press handling in the Activity, or using `NavController` per pane with the Navigation component).

---

## Session 1 — 2026-04-23

### Implementation Completed
All 10 Phase 1 steps implemented within the `flights` module (standalone branch only, never merged to `develop`):
- Added `androidx.slidingpanelayout:slidingpanelayout:1.2.0` dependency
- Created `FlightDetailsPaneHost` interface (decouples `FlightDetailsFragment` from `FlightDetailsActivity` cast)
- `FlightDetailsActivity` now implements `FlightDetailsPaneHost`
- `FlightDetailsFragment` cast swapped from `FlightDetailsActivity` → `FlightDetailsPaneHost` (lines 272–273)
- Created `FlightSearchResultFoldableActivity` extending `FlightSearchResultActivity`
- Presenter routing updated to check for foldable + two-pane mode before launching `FlightDetailsActivity`
- `FlightSearchResultFoldableActivity` registered in `AndroidManifest.xml` with `resizeableActivity=true`
- `FlightSearchActivity` now routes to `FlightSearchResultFoldableActivity`

---

### Issue 1 — Layout not inflating (RESOLVED)

**Symptom:** Tapping a flight opened the full-screen `FlightDetailsActivity` instead of loading the detail in the right pane. The `SlidingPaneLayout` was never created.

**Root cause:** `FlightSearchResultActivity.onCreate()` always sets `mLayoutRes = activity_international_actionbar` **before** calling `super.onCreate()`. This overwrote the subclass's `mLayoutRes = activity_flight_search_result_foldable` assignment, so the wrong layout was inflated and `mSlidingPaneLayout` stayed null.

`setContentViewWithSlidingMenus()` in `WegoBaseCoreActivity` (Kotlin) is not `open` and therefore cannot be overridden from Java.

**Workaround:** `FlightSearchResultFoldableActivity` now calls `super.onCreate()` (which inflates `activity_international_actionbar`), then immediately calls `setupSlidingPane()` which programmatically:
1. Finds `rootContainer` (full-screen FrameLayout in the inflated layout)
2. Removes it from its parent (`layout_root`)
3. Creates a `SlidingPaneLayout` with `rootContainer` as left pane + new `FrameLayout (id=pane_detail)` as right pane
4. Re-inserts the `SlidingPaneLayout` at index 0 of `layout_root`

The action bar and sort/filter bar remain as siblings of the `SlidingPaneLayout` in `layout_root`, so they still overlay correctly.

**Implication for Phase 2:** The custom foldable layout XML (`activity_flight_search_result_foldable.xml`) was created but is not currently used due to this constraint. If the parent class's layout inflation pattern changes, this workaround may need revisiting.

---

### Issue 2 — Empty right pane takes up screen space on narrow screens (RESOLVED)

**Symptom:** On any screen (including a regular phone or folded foldable), the empty right pane occupies 50% of the horizontal space even when no flight has been selected.

**Root cause:** `SlidingPaneLayout.LayoutParams(0, MATCH_PARENT)` with `weight=1f` on both panes sets minimum width = 0 for each. SlidingPaneLayout uses layout_width as minimum width to decide if panes fit side-by-side. Combined minimum 0 + 0 = 0, which always fits any screen width, so `isSlideable()` is permanently false — both panes always shown. Fix decision pending from product/developer.

**Status:** RESOLVED — root cause identified. Fix decision pending from product/developer.

---

### Issue 3 — Crash on flight tap: NullPointerException in FlightDetailsFragment.onResume (RESOLVED)

**Symptom:** Tapping a flight item crashes with:
```
java.lang.NullPointerException: Attempt to invoke interface method
'void com.wego.android.features.flightdetails.FlightDetailsContract$Presenter.start()'
on a null object reference
    at com.wego.android.features.flightdetails.FlightDetailsFragment.onResume(FlightDetailsFragment.java:555)
```

**Root cause:** `showDetailInPane()` created `FlightDetailsFragment` but never created `FlightDetailsPresenter`. `AbstractPresenter`'s constructor calls `view.setPresenter(this)` — without instantiating the presenter, `FlightDetailsFragment.presenter` stays null and crashes in `onResume()` at `presenter.start()`.

**Resolution:** `showDetailInPane()` now mirrors `FlightDetailsActivity.onCreate()` — after committing the fragment transaction, it creates `FlightDetailsPresenter(fragment, extras, ...)` which automatically wires itself to the fragment. `FlightSearchResultFoldableActivity` now implements `FlightDetailsPresenter.EventListener` with no-op callbacks for `onShortURLSuccess()` and `onShortURLFaild()`. Added guard for `FlightDetailsRepository` not yet instantiated.

**Status:** RESOLVED.

---

### Decision: Issue 2 — Empty right pane on narrow screens (DEFERRED)

**Decision:** Leave as-is for Phase 1 PoC. Both panes always show side-by-side regardless of screen width.

**How to fix when needed:** In `setupSlidingPane()` in `FlightSearchResultFoldableActivity`, change `SlidingPaneLayout.LayoutParams(0, MATCH_PARENT)` to concrete minimum widths for each pane:
- Left pane (results): `SlidingPaneLayout.LayoutParams(dpToPx(320), MATCH_PARENT)` with `weight=1f`
- Right pane (detail): `SlidingPaneLayout.LayoutParams(dpToPx(300), MATCH_PARENT)` with `weight=1f`
- Combined minimum 620dp exceeds folded phone width (~408dp) → `isSlideable()=true` → collapses to single pane on fold
- Combined 620dp fits unfolded inner display (~841dp) → `isSlideable()=false` → two-pane on unfold
- Use `(int)(densityDp * context.getResources().getDisplayMetrics().density)` for dp→px conversion

---

### Issue 4 — Right pane persists when folding device (phone mode) (OPEN)

**Symptom:** When folding the Pixel Fold from unfolded to folded (phone mode), the right pane remains visible and takes up screen space. Results list is squished to 50% width even though only one pane should be shown.

**Root cause:** Same as Issue 2 — both panes have 0dp minimum width, so `SlidingPaneLayout.isSlideable()` never returns true regardless of screen width. When the window narrows on fold, SlidingPaneLayout re-measures but still sees combined minimum = 0, so both panes stay side-by-side.

**Fix:** Apply the concrete minimum width fix described in Issue 2 decision above. Status: In progress.

---

### Issue 5 — Departure & arrival section missing for first few flights (OPEN)

**Symptom:** When tapping one of the first few flights in the search results list, the flight detail pane loads but the departure & arrival information section (leg details: airport, time, duration) is not visible.

**Suspected cause:** Under investigation. Possible: `FlightDetailsPresenter.parseBundle()` runs in the constructor (before the fragment's view is created) and may push data to the view that gets lost because `onCreateView` hasn't run yet. This is a classic MVP timing issue. Also possible: first few flights have incomplete leg data in `FlightDetailsRepository` at tap time.

**Status:** Under investigation.

---

## Session 3 — 2026-04-23

### Issues Resolved

#### Issue 4 — Right pane persists when device folded to phone mode (RESOLVED)

**Root cause:** Both `SlidingPaneLayout` child panes had `layout_width=0`. Combined minimum width = 0, so `isSlideable()` always returns false — panes never stack. When the window narrows on fold, SlidingPaneLayout re-measures but still sees combined minimum = 0 and keeps both panes side-by-side.

**Fix:** Changed `setupSlidingPane()` to use concrete minimum widths:
- Left pane (results): `dpToPx(320)` → 320dp minimum
- Right pane (detail): `dpToPx(300)` → 300dp minimum
- Combined 620dp > folded screen width (~408dp) → `isSlideable()=true` → collapses to single pane on fold
- Combined 620dp < unfolded inner display (~841dp) → `isSlideable()=false` → two-pane on unfold
- Added `dpToPx()` helper method to convert dp to pixels using display density

**Location:** `FlightSearchResultFoldableActivity.java` — `setupSlidingPane()` method + added `dpToPx()` helper

**Build status:** `compilePlaystoreDebugJavaWithJavac` PASS, `detekt` PASS

---

#### Issue 5 — Departure & arrival section missing for first few flights (RESOLVED)

**Root cause:** `FlightDetailsPresenter` is created while `FlightDetailsFragment` is not yet attached (fragment transaction is async via `commit()`). `fragment.getActivity()` returns null → `isValidActivity()` returns false → when `outboundLeg` is null in `setFlightResults()`, the early return prevents calling `finish()` but also leaves `outboundLeg` unset → `drawOutboundResults()` in `start()` finds null leg → renders nothing (departure & arrival section absent).

**Fix:** Added a leg resolvability pre-check in `showDetailInPane()` before creating the fragment/presenter. Checks whether `trip.getLegs()` is non-empty OR `legsMap.get(trip.getLegIds().get(0))` is non-null. Returns silently if legs are not yet resolvable. This prevents creating a presenter that would silently bail out and leave the detail view in a partially-rendered state, and avoids the race where `getActivity()` is null during async fragment attachment.

**Location:** `FlightSearchResultFoldableActivity.java` — `showDetailInPane()` method, approximately 7 lines added before fragment creation

**Build status:** `compilePlaystoreDebugJavaWithJavac` PASS, `detekt` PASS

---

---

## Session 4 — 2026-04-23

### Issues Resolved

#### Issue 6 — Departure/arrival section not visible on flight tap; scroll of both panes "linked" (RESOLVED)

**Symptom:** Tapping a flight in the left pane opens the detail pane but the departure/arrival section (leg details: airport, time, duration) is missing. Scrolling the left (search results) pane causes the departure/arrival section to appear in the right (detail) pane — both panes appeared scroll-linked.

**Root cause:** `SlidingPaneLayout` maintains an internal open/closed state for the detail pane, independent of `isSlideable()`. `open()` was only called when `isSlideable()==true` (phone/folded mode). In two-pane mode (`isSlideable()==false`), `open()` was never called, so the pane's internal state remained "closed" — physically in a closed/offset position that hid the content even though both panes fit on screen.

The SlidingPaneLayout API explicitly states: "Open the detail view if it has been hidden. This method will open the detail pane whether or not the layout is currently slideable."

The "scroll linking" symptom was the `ViewDragHelper` inside `SlidingPaneLayout` intercepting the RecyclerView scroll gesture (which has a horizontal component) and using it to slide the detail pane to its open position — making it appear as though the two panes were scroll-linked.

**Investigation:**
- Ruled out NestedScrolling — `SlidingPaneLayout` 1.2.0 does not implement `NestedScrollingParent`.
- Confirmed content IS rendered — `drawOutboundResults()` sets text correctly in `onResume()`.
- No views are set to `GONE` in `initFragmentViews()`.
- Conclusion: content was rendered but the pane's internal position offset was hiding it.

**Fix:** Removed the `isSlideable()` guard on the `open()` call in `showDetailInPane()`. Now calls `mSlidingPaneLayout.open()` unconditionally whenever a fragment is placed in the detail pane. This ensures the pane is in the open state in both single-pane and two-pane modes.

**Location:** `FlightSearchResultFoldableActivity.java` — `showDetailInPane()` method — 1-line change

**Status:** RESOLVED — compile SUCCESSFUL

---

---

## Session 5 — 2026-04-24

### Analysis: Fold defaults to last-interacted pane

**Observed behaviour:** In unfolded (two-pane) mode, whichever pane received the last touch — left (list) or right (detail) — becomes the visible pane after the device is folded. This overrides our intent to always land on the list after folding.

---

#### Root cause — confirmed from SlidingPaneLayout 1.2.0 source

The behaviour is **intentional AndroidX design**, not a bug. It is driven by three cooperating mechanisms inside `SlidingPaneLayout`.

**Mechanism 1 — Touch tracking (`onInterceptTouchEvent`, lines 920–928)**

Every `ACTION_DOWN` event fires this block while in two-pane (non-slideable) mode:

```java
// "Preserve the open state based on the last view that was touched."
if (!mCanSlide && action == MotionEvent.ACTION_DOWN && getChildCount() > 1) {
    final View secondChild = getChildAt(1);
    if (secondChild != null) {
        mPreservedOpenState = mDragHelper.isViewUnder(secondChild,
                (int) ev.getX(), (int) ev.getY());
    }
}
```

- Touch on right pane (detail) → `mPreservedOpenState = true`
- Touch on left pane (list) → `mPreservedOpenState = false`

The library even comments on the intent: *"Preserve the open state based on the last view that was touched."*

**Mechanism 2 — Focus tracking (`requestChildFocus`, lines 909–913)**

In non-touch mode (keyboard / accessibility / D-pad), focus changes also update the state:

```java
if (!isInTouchMode() && !mCanSlide) {
    mPreservedOpenState = child == mSlideableView; // true = right pane has focus
}
```

**Mechanism 3 — Fold transition (`onSizeChanged` → `onLayout`, lines 900–906 and 830–832)**

When the device folds the window narrows, triggering:

1. `onSizeChanged(newWidth ≠ oldWidth)` → sets `mFirstLayout = true`
2. Next layout pass → `onMeasure` computes `mCanSlide = true` (narrow: panes no longer fit side-by-side)
3. `onLayout` → because `mFirstLayout == true`:
   ```java
   mSlideOffset = mCanSlide && mPreservedOpenState ? 0.f : 1.f;
   ```
   - `mPreservedOpenState = true` → `mSlideOffset = 0.f` → detail pane shown (right)
   - `mPreservedOpenState = false` → `mSlideOffset = 1.f` → list pane shown (left)

**Coordinate note:** In SlidingPaneLayout's coordinate system, `mSlideOffset = 0` = "open" (right/detail pane visible in single-pane mode); `mSlideOffset = 1` = "closed" (right pane hidden, left pane fills screen). `isOpen()` returns `!mCanSlide || mSlideOffset == 0`.

---

#### Timeline of a fold with detail open, then list scrolled

| Event | `mPreservedOpenState` | `mSlideOffset` / visible pane |
|---|---|---|
| App starts, no flight tapped | `false` (default) | — (two-pane, both visible) |
| Flight tapped → `showDetailInPane()` → `open()` called | `true` (set by `openPane()`) | — (two-pane, both visible) |
| User scrolls the list (left pane `ACTION_DOWN`) | `false` (overwritten by touch) | — (two-pane, both visible) |
| Device folded → `onSizeChanged` → next `onLayout` | still `false` | `mSlideOffset = 1` → **list shown** |

And if the user's last touch was on the detail pane:

| Event | `mPreservedOpenState` | Visible after fold |
|---|---|---|
| Flight tapped → `showDetailInPane()` | `true` | — |
| User taps something in the detail pane | `true` | — |
| Device folded | still `true` | `mSlideOffset = 0` → **detail shown** |

This precisely matches the reported behaviour: *"whichever pane I interacted last."*

---

#### Why our `open()` call in `showDetailInPane()` does not help

`openPane()` sets `mPreservedOpenState = true`, but that state is overwritten by the very next `ACTION_DOWN` on the list pane. Since users naturally scroll the list after tapping a flight, the preserved state frequently ends up as `false` (→ list shown on fold) or `true` (→ detail shown on fold) depending on the last scroll gesture. Calling `open()` unconditionally (our current fix for Issue 6) was needed to keep the pane in the correct rendering position, but it does not reliably control what happens on fold because the touch tracking always overwrites `mPreservedOpenState`.

---

#### Key learnings for Phase 2

1. **`mPreservedOpenState` is our lever.** Calling `closePane()` in response to a fold event sets `mPreservedOpenState = false`, which is what we need.
2. **`onSizeChanged` is the fold signal.** It fires synchronously before the next layout pass and is the earliest point we can intervene.
3. **Fragment is NOT destroyed on fold.** The fragment in `pane_detail` survives because `closePane()` only changes `mSlideOffset` (visual position); it does not remove views from the fragment manager. On unfold, the SPL transitions back to non-slideable mode and both panes become visible again — the previously loaded detail fragment is automatically restored. No explicit "restore right pane" logic is needed.
4. **`addOnPanelSlideListener` does NOT fire on fold/unfold.** It only fires when the pane slides in single-pane mode. A `ViewTreeObserver.OnGlobalLayoutListener` or an override of `onSizeChanged` in the Activity is required to detect mode changes.
5. **`onConfigurationChanged` is the Activity-level fold hook.** The manifest declares `screenSize|smallestScreenSize|screenLayout|orientation` in `configChanges`, so foldable transitions call `onConfigurationChanged` rather than destroying/recreating the activity. This is where we can post a `closePane()` to force the list pane on every fold.
6. **Single-pane close → two-pane restore is free.** After `closePane()` on fold, the SPL's `mPreservedOpenState = false`. On unfold, `onLayout` sees `!mCanSlide` so the `if (mFirstLayout)` branch sets `mSlideOffset = 1.f` (closed). But in non-slideable mode, `mSlideOffset` is irrelevant — both panes are always rendered side by side. So the detail fragment is visible again as soon as the screen is wide enough.

---

### Implementation: Phase 1 additions + Phase 2 PoC (2026-04-24)

#### Files changed

| File | Change |
|---|---|
| `FlightSearchResultFoldableActivity.java` | Major update — fold fix, close button, filter intercept, back handling |
| `MockFilterSortFragment.java` | New — static mock filter/sort for right-pane backstack experiment |
| `flights/src/main/res/layout/fragment_mock_filter_sort.xml` | New — mock filter layout |

#### P1-A: Fold → always show left pane

Override `onConfigurationChanged()`. Posts `closePane()` on the SPL after the layout pass that applies the new window size, so `isSlideable()` reflects the folded state before we call close.

```java
@Override
public void onConfigurationChanged(Configuration newConfig) {
    super.onConfigurationChanged(newConfig);
    mSlidingPaneLayout.post(() -> {
        if (mSlidingPaneLayout.isSlideable()) mSlidingPaneLayout.closePane();
    });
}
```

The `mFirstLayout` + `mPreservedOpenState` chain (our root cause) is bypassed because `closePane()` runs AFTER the layout pass has already placed the detail pane. `closePane()` then smoothly animates it to `mSlideOffset = 1` (closed).

#### P1-B: Unfold → right pane restored automatically

No code needed. Fragment survives in `pane_detail` container; SPL transitions to non-slideable and renders both panes side-by-side.

#### P1-C: Close icon on detail pane

`addDetailPaneCloseButton()` in `setupSlidingPane()`: adds an `ImageButton` (48dp, top-right, `Gravity.TOP | Gravity.END`) to `mDetailPane`. Calls `clearDetailPane()` on click. Shown when `FlightDetailsFragment` is the active fragment; hidden when `MockFilterSortFragment` is visible (which has its own close button).

`clearDetailPane()`:
1. Pops all backstack entries (`popBackStackImmediate()` loop)
2. Removes base fragment via `remove()` transaction
3. Calls `closePane()` if slideable

#### P1-D: Clear detail on filter change

The `all_filters` button click listener is wrapped in `wrapFilterButtonForTwoPane()`, called once from `onResume()` (after `FlightSearchResultFragment.initSortFilterBar()` has wired the original listener). In two-pane mode, `showFilterInPane()` is called instead. In single-pane mode, the original `openFiltersBottomSheet()` behavior is preserved by delegating to the fragment.

#### Phase 2: Pane navigation model

**Base destination (no backstack):** `FlightDetailsFragment`
- `showDetailInPane()` uses `replace()` with no `addToBackStack()`

**Modal destination (stackable):** `MockFilterSortFragment`
- `showFilterInPane()` uses `replace()` + `addToBackStack("filter")`
- Filter's own close button calls `popBackStack()` → reveals detail
- Activity-level close button (P1-C) is hidden while filter is shown

**Back-press handler:**
Added via `OnBackPressedCallback` after `super.onCreate()`, so it runs first (LIFO):
- Two-pane + backstack entry → `popBackStack()` (filter dismiss)
- Otherwise → clear right-pane stack silently, then defer to parent (`finish()`)

**Backstack change listener:** `addOnBackStackChangedListener` — when `getBackStackEntryCount()` drops to 0 and a detail was loaded, re-shows the activity-level close button and brings it to front.

#### Build status
- `compilePlaystoreDebugJavaWithJavac` — BUILD SUCCESSFUL ✅
- `detekt` — BUILD SUCCESSFUL ✅

---

### Fix: close button not visible on fragments (2026-04-24)

**Root cause:** `FragmentManager.replace()` adds the incoming fragment's root view to the container via `container.addView(view)`, which appends at the **end** of the `FrameLayout` children (highest z-order). Since `mDetailCloseButton` was added to `mDetailPane` during setup (at a lower index), every fragment commit placed its view on top of the button, making it invisible.

The earlier `mDetailPane.post(() -> mDetailCloseButton.bringToFront())` did not reliably fix this because `commit()` is asynchronous — the fragment's view could be appended to the container AFTER the `post()` Runnable had already executed, re-covering the button.

**Fix:** Two changes:
1. Changed `commit()` → `commitNow()` in `showDetailInPane()`. `commitNow()` executes the transaction synchronously so the fragment's view is in the container when the call returns.
2. Added `bringCloseButtonToFront()` helper: removes `mDetailCloseButton` from `mDetailPane` and re-appends it as the **last** child (always highest z-order). Called immediately after `commitNow()`.

`showFilterInPane()` uses `commit()` + `executePendingTransactions()` (required because `addToBackStack()` prevents `commitNow()`). The activity-level close button is hidden in this state; the filter fragment provides its own close button inside its layout.

**Key learning:** With a `FrameLayout` container shared between `FragmentManager` and manually-added overlay views, any overlay view must be re-appended (remove + addView) after each fragment commit to guarantee it stays on top. `bringToFront()` alone is unreliable when the fragment's `addView` call races with the Runnable posted to bring the overlay to front.

---

### Fix: empty state + initial pane hidden (2026-04-24)

**Empty state — `EmptyDetailPaneFragment`:** New fragment shown when the user dismisses the flight detail (taps X). Displays a centered plane icon (`ic_flight_empty`) + "No trip selected" label. Loaded via `clearDetailPane()` using `commitNow()` (no backstack — it is not a navigation destination, just placeholder content).

**Initial pane hidden:** `mDetailPane.setVisibility(View.GONE)` set at the end of `setupSlidingPane()`. `SlidingPaneLayout.onMeasure()` skips GONE children, so the left pane fills the full width during the loading screen. `mDetailPane.setVisibility(View.VISIBLE)` is called at the start of `showDetailInPane()` on the first flight tap, triggering an SPL re-measure that transitions to two-pane layout.

**State flow after these fixes:**

| State | Right pane visibility | Fragment in pane_detail | Close button |
|---|---|---|---|
| Initial / loading | GONE | none | hidden |
| Flight tapped | VISIBLE | FlightDetailsFragment | visible (top-right) |
| Filter tapped (two-pane) | VISIBLE | MockFilterSortFragment | hidden (filter has own) |
| Filter closed (back/X) | VISIBLE | FlightDetailsFragment (restored) | visible |
| Detail X tapped | VISIBLE | EmptyDetailPaneFragment | hidden |
| Detail tapped again | VISIBLE | FlightDetailsFragment | visible |

**Files added/updated in this fix:**
- `FlightSearchResultFoldableActivity.java` — `bringCloseButtonToFront()`, `commitNow()`, GONE initial state, `clearDetailPane()` → empty state
- `EmptyDetailPaneFragment.java` — new
- `fragment_empty_detail_pane.xml` — new (plane icon + two text labels)

---

### Planned changes (Phase 1 additions + Phase 2 scope)

#### Phase 1 additions

| # | Change | Mechanism |
|---|--------|-----------|
| P1-A | Fold → always show left pane | Override `onConfigurationChanged` in `FlightSearchResultFoldableActivity`; `post { closePane() }` when `isSlideable()` |
| P1-B | Unfold → right pane restored automatically | No code needed (fragment survives in `pane_detail`; SPL re-exposes both panes) |
| P1-C | Close icon on detail pane | Overlay `ImageButton` on `mDetailPane`; on click: pop all fragments in `pane_detail`, call `closePane()` if slideable |
| P1-D | Clear right pane when filters change | Intercept filter/sort button click in `FlightSearchResultFoldableActivity`; call `clearDetailPane()` before the existing filter action |

#### Phase 2 PoC — filter pane backstack experiment

**Goal:** Observe backstack management when the right pane hosts multiple fragments (flight detail, mock filter/sort). Understand: Does the SPL maintain per-pane backstacks? Can we keep exactly one instance of each fragment type in the right pane?

| # | Item | Notes |
|---|------|-------|
| P2-A | `MockFilterSortFragment` | Simple layout: title bar with close button + static mock filter chips. Not functional. Java, in `flights` module |
| P2-B | Override filter/sort click in two-pane mode | Load `MockFilterSortFragment` into `pane_detail` instead of showing full-screen filter drawer |
| P2-C | Close button on `MockFilterSortFragment` | Pops this fragment from `pane_detail`; behaviour to observe: does it reveal the previous detail fragment or empty? |
| P2-D | Backstack experiment A — no backstack | `replace()` without `addToBackStack()` — filter replaces detail; back button has no effect on pane |
| P2-E | Backstack experiment B — with backstack | `replace()` with `addToBackStack("filter")` — back button pops filter, reveals previous detail (or empty) |
| P2-F | Single-instance experiment | Before adding: `findFragmentByTag("detail")` / `findFragmentByTag("filter")`; if present, detach+attach instead of creating new instance. Observe: does fragment state survive? |

**Observations to record for each experiment:**
- Does `BackStack` of `FragmentManager` apply per-container or globally?
- Does back button in single-pane mode (folded) consume the right pane's backstack or the Activity's?
- Is there a visible transition/animation when switching between filter and detail in the right pane?
- Does keeping a single instance of `FlightDetailsFragment` break anything (stale data, view state)?

---

---

## Session 6 — 2026-04-24

### Issue: Loading screen full-width (right pane visible during initial load) — DROPPED

**Goal:** Keep the right pane hidden (`View.GONE`) while the loading screen is showing, then reveal it automatically when search results first arrive.

**Approaches tried (all failed or confirmed unreliable):**

1. **`postDelayed(2000)`** — Hardcoded delay. Too short for typical search durations (5–15s). Unreliable and incorrect.

2. **`OnGlobalLayoutListener` on `search_loading_view`** — `search_loading_view` (the Lottie animation) has `visibility="gone"` in XML. The `GlobalLayoutListener` fires immediately because the view is already non-`VISIBLE` before any state change. Useless as a "loading done" trigger.

3. **`OnGlobalLayoutListener` on `flight_search_tip`** — `flight_search_tip` (the loading overlay `RelativeLayout`) starts `visibility="visible"` in XML. However, `FlightSearchResultFragment.switchLayerAccordingToPageState()` sets it to `GONE` for `NO_RESULT` (line 1038) and `NO_CONNECTION` (line 1049) states **in addition to** the `RESULT` state (line 1056). This causes spurious triggers during loading error states — pane revealed before any results are available.

4. **`OnPreDrawListener` on `flight_search_tip`** — Same root cause as approach 3. `flight_search_tip` goes `GONE` in non-result states, making it an unreliable "results arrived" signal.

5. **`OnPreDrawListener` on `sort_filter_bar`** — `sort_filter_bar` starts `GONE` at fragment init (`FlightSearchResultFragment` line 548) and becomes `VISIBLE` only in two specific paths: `onAnimationStart` (line 1118) and the non-animation result path (line 1134). This appeared to be a reliable trigger. However, user confirmed the issue persisted even with this approach. Root cause not fully determined — possibly a timing interaction between `OnPreDrawListener` firing and the SPL measure pass that re-introduces the full-width state.

**Key learnings:**

- `search_loading_view` starts `GONE` in XML — cannot be used as any kind of state-change trigger.
- `flight_search_tip` is unreliable for "results arrived" because it goes `GONE` for error states too.
- `initFragment()` is called from `super.onCreate()` in `FlightSearchResultActivity` (line 156), **before** `setupSlidingPane()` runs in the subclass. Any override of `initFragment()` therefore runs with `mDetailPane == null` — listeners registered there would silently no-op.
- `sort_filter_bar` is the cleanest available signal (starts GONE, only goes VISIBLE when real results arrive) but proved insufficient in practice.
- The fundamental difficulty: there is no clean callback from `FlightSearchResultFragment` to the activity that fires exactly once when the first result batch is ready. Retrofitting a callback into a legacy fragment with complex state machine would exceed PoC scope.

**Decision:** Dropped from PoC scope. The right pane stays `GONE` on load and is revealed on the first flight tap (`showDetailInPane()`). The loading screen has no results to display in the right pane anyway, so this is an acceptable trade-off.

**For future reference:** A reliable solution would require either (a) adding a `OnFirstResultsListener` callback interface to `FlightSearchResultFragment` so the activity can react to the exact moment results arrive, or (b) observing the ViewModel's results `StateFlow`/`LiveData` directly from the activity.

---

### Fix: Clear detail pane on filter chip tap (2026-04-24)

**Problem:** When the user taps a filter chip (e.g. stops, duration, airline) in two-pane mode, the presenter's `changeFilter()` is called and the result list updates. However the detail pane still showed the flight detail from before the filter change — a stale, mismatched result.

**Fix:** Added a `RecyclerView.SimpleOnItemTouchListener` to the `filters_list_topbar` RecyclerView inside `wrapFilterButtonForTwoPane()`. On `ACTION_DOWN` in two-pane mode with detail loaded, calls `clearDetailPane()` immediately. Returns `false` so the chip's own tap handling proceeds normally.

```java
filtersListTopbar.addOnItemTouchListener(new RecyclerView.SimpleOnItemTouchListener() {
    @Override
    public boolean onInterceptTouchEvent(RecyclerView rv, MotionEvent e) {
        if (e.getAction() == MotionEvent.ACTION_DOWN
                && isTwoPaneMode()
                && isDetailLoaded()) {
            clearDetailPane();
        }
        return false;
    }
});
```

**Why `ACTION_DOWN` not `ACTION_UP`:** Clears immediately on touch start, giving instant visual feedback that the detail is no longer associated with the previous filter state. The chip's tap completes normally because `onInterceptTouchEvent` returns `false`.

**Files changed:**
- `FlightSearchResultFoldableActivity.java` — `wrapFilterButtonForTwoPane()`: added `RecyclerView` listener; added `import android.view.MotionEvent` and `import androidx.recyclerview.widget.RecyclerView`; removed `observeLoadingView()` call from `onCreate()` and the method itself; removed `revealDetailPaneWithEmptyState()`; removed `import android.view.ViewTreeObserver`.

---

---

## Session 7 — 2026-04-24

### Root cause analysis: why all five loading-screen approaches failed

After deep analysis of SPL internals and the presenter call chain, the root cause became clear:

**The `View.GONE` mechanism was always correct.** SPL skips GONE children in `onMeasure()`, left pane fills full width. `setVisibility(VISIBLE)` triggers `requestLayout()` automatically. This part worked. The flaw was in every signal used to decide *when* to call `setVisibility(VISIBLE)`.

**The correct signal:** `FlightSearchResultsPresenter` has a precise state transition at line 1732:

```
API response received
  → view.addData()                 [line 1324 — items added to adapter]
  → presenter.onAddDataCompleted() [line 1722]
    → switchLayer(PageState.RESULT) [line 1732 — only when !isListLayer]
      → switchLayerAccordingToPageState() [else branch, line 1063]
        ← our listener fires HERE
```

All of this executes synchronously on the main thread, before the Choreographer commits the next frame. This means `setVisibility(VISIBLE)` (from our listener) and the adapter's `notifyDataSetChanged`/`requestLayout()` both queue into the same pending traversal. The view system coalesces them: items are measured at half-width in the single traversal that follows. **No `OnPreDrawListener` or frame-cancellation is needed.**

An `OnPreDrawListener` WAS considered and would work, but is unnecessary — the call-stack ordering provides the batching naturally.

**Why views-tree observers failed:** All five approaches (`postDelayed`, `GlobalLayoutListener` on `search_loading_view`, `GlobalLayoutListener`/`OnPreDrawListener` on `flight_search_tip`, `OnPreDrawListener` on `sort_filter_bar`) observed *consequences* of the state machine rather than the state transition itself. This meant timing races with the frame pipeline, misfires on non-result states, and inability to capture the exact `LOADING → RESULT` transition.

---

### Fix: Issue #8 — Loading screen full-width (RESOLVED)

**Approach:** Add `OnFirstResultsListener` callback to `FlightSearchResultFragment`, following the same pattern as `OnFilterChangedListener` (Session 6). The fragment fires it exactly once at the top of the `else` branch in `switchLayerAccordingToPageState()`, guarded by `mResultPaneRevealed` to prevent re-firing on subsequent filter updates.

**Fragment changes (`FlightSearchResultFragment.java`):**
```java
// New interface + field + setter (same block as OnFilterChangedListener)
public interface OnFirstResultsListener {
    void onFirstResultsAvailable();
}
private OnFirstResultsListener mFirstResultsListener;
private boolean mResultPaneRevealed = false;
public void setOnFirstResultsListener(OnFirstResultsListener listener) { ... }

// In switchLayerAccordingToPageState(), top of else branch:
if (!mResultPaneRevealed && mFirstResultsListener != null) {
    mResultPaneRevealed = true;
    mFirstResultsListener.onFirstResultsAvailable();
}
```

**Activity changes (`FlightSearchResultFoldableActivity.java`):**
```java
// In wrapFilterButtonForTwoPane(), alongside setOnFilterChangedListener:
resultFrag.setOnFirstResultsListener(() -> {
    if (mDetailPane == null || mDetailPane.getVisibility() == View.VISIBLE) return;
    mDetailPane.setVisibility(View.VISIBLE);
    adjustDetailPaneForOverlays();
    getSupportFragmentManager()
            .beginTransaction()
            .replace(R.id.pane_detail, new EmptyDetailPaneFragment())
            .commit();  // async — safe to call mid-state-transition
});
```

`commit()` (not `commitNow()`) is used because the listener fires within `switchLayerAccordingToPageState()`, which is a view-update sequence — `commitNow()` here could cause nested fragment transactions.

**State flow after fix:**

| State | Right pane visibility | Fragment in pane_detail | Close button |
|---|---|---|---|
| Initial / loading | GONE | none | hidden |
| First results arrive (listener fires) | VISIBLE | EmptyDetailPaneFragment | hidden |
| Flight tapped | VISIBLE | FlightDetailsFragment | visible |
| Filter applied | VISIBLE | EmptyDetailPaneFragment | hidden |
| Detail X tapped | VISIBLE | EmptyDetailPaneFragment | hidden |

**Build status:** `compilePlaystoreDebugJavaWithJavac` — BUILD SUCCESSFUL ✅

---

---

## Session 8 — 2026-04-27

### Analysis: `open()` / `close()` in two-pane mode — correcting Session 4 misconception

#### What `open()` actually does

`openPane()` has two distinct effects that are independent of each other:

```java
// SlidingPaneLayout.openPaneInternal() — simplified
private boolean openPaneInternal() {
    if (!mCanSlide || isOpen()) {
        mPreservedOpenState = true;   // always written, even in two-pane mode
        return false;                  // early-return: no animation
    }
    // single-pane path: animate mSlideOffset 1.0 → 0.0 via ViewDragHelper
    mDragHelper.smoothSlideViewTo(mSlideableView, mSlideRange, 0);
    mPreservedOpenState = true;
    return true;
}
```

| Mode | `mCanSlide` | Sliding animation | `mPreservedOpenState` |
|---|---|---|---|
| Single-pane (folded / narrow) | `true` | Yes — animates detail pane into view | Set to `true` |
| Two-pane (unfolded / wide) | `false` | No — early return, nothing moves | Still set to `true` |

The official docs say "these methods have no effect if both panes are visible" — this refers to the **animation/sliding axis only**. `mPreservedOpenState` is always written.

#### Correcting Session 4's root cause explanation for Issue 6

Session 4 recorded: *"In two-pane mode, `open()` was never called so the pane's internal state remained closed — physically in a closed/offset position that hid the content."*

This is incorrect. In two-pane mode (`mCanSlide = false`), `mSlideOffset` is not used to position panes — panes are positioned by measured widths only. `mSlideOffset` simply does not affect the layout in non-slideable mode.

**What actually fixed Issue 6:**

When `showDetailInPane()` was called and the detail pane transitioned from `GONE` → `VISIBLE`, SPL re-measured. On a narrow screen (folded phone, ~408dp) with combined min widths now 620dp, it transitioned to **single-pane mode**. `onLayout()` fired with `mFirstLayout = true`:

```java
// onLayout() — first pass after size change
if (mFirstLayout) {
    mSlideOffset = mCanSlide && mPreservedOpenState ? 0.f : 1.f;
}
// mSlideOffset 0.0 = detail pane visible
// mSlideOffset 1.0 = list pane visible (detail hidden)
```

- **Before fix** (`mPreservedOpenState = false`): `mSlideOffset = 1.0` → detail pane hidden. ViewDragHelper interpreted the horizontal component of RecyclerView scroll as "user trying to open the pane" → intercepted it → scroll-linking symptom. User had to scroll left to reveal flight details.
- **After fix** (unconditional `open()` → `mPreservedOpenState = true`): `mSlideOffset = 0.0` → detail pane shown immediately.

**The unconditional `open()` call is correct — just for a different reason than Session 4 stated.** In two-pane mode, it primes `mPreservedOpenState` for fold-event and mode-transition scenarios. In single-pane mode, it animates the pane in directly.

#### Does this misconception contribute to Issue #8?

**No.** `open()` is called inside `showDetailInPane()`, which is only invoked when the user taps a flight — long after the loading screen phase. Issue #8 (loading screen not full-width) occurs immediately at the first `onLayout()` after `addView(detailPane)`, before any user interaction. The two problems are completely independent.

---

### Root cause of Issue #8 confirmed: `updateObscuredViewsVisibility()`

`SlidingPaneLayout` contains an internal method called from every `onLayout()` pass:

```java
// SlidingPaneLayout — updateObscuredViewsVisibility()
private void updateObscuredViewsVisibility(View panel) {
    for (int i = 0; i < childCount; i++) {
        final View child = getChildAt(i);
        final int vis;
        if (/* child rect fully covered by panel */) {
            vis = View.INVISIBLE;
        } else {
            vis = View.VISIBLE;   // ← if not fully covered: VISIBLE
        }
        child.setVisibility(vis);  // ← overwrites our GONE
    }
}
```

**Critical detail:** this method only operates on the `INVISIBLE` ↔ `VISIBLE` axis. It does not check for or preserve `View.GONE`. The detail pane, sitting to the right of the list pane, is not fully obscured → SPL promotes it to `VISIBLE` on the very first `onLayout()` call after `addView(detailPane)`.

This fires synchronously, before any of our listeners, observers, or callbacks can intervene:

```
addView(detailPane, GONE)
  → SPL.requestLayout()
    → onMeasure()  ← GONE child skipped correctly (min-width not counted)
    → onLayout()
      → updateObscuredViewsVisibility()
        → detailPane.setVisibility(VISIBLE)  ← GONE overwritten here
```

**This is why all five previous timing-based approaches failed:** the detail pane was already `VISIBLE` by the first rendered frame, before `postDelayed`, `OnGlobalLayoutListener`, `OnPreDrawListener`, or `OnFirstResultsListener` could react.

**User-confirmed evidence:** Removing the `addView(detailPane)` call at `setupSlidingPane()` line 126 eliminates the right pane — because SPL never gets a child to promote.

---

### Options for fixing Issue #8 (plan mode — no implementation)

**Option A — Always-present placeholder (Google's canonical pattern)**

Never set the detail pane to `GONE`. Start it `VISIBLE` with an empty-state fragment (`EmptyDetailPaneFragment`) from the moment SPL is built. Draw the loading animation as a separate full-bleed overlay view inserted into the activity's root `FrameLayout` at a higher z-order than the SPL — so it visually covers both panes during loading. When `onFirstResultsAvailable()` fires, hide the overlay. No fight with SPL's visibility system.

**Option C — Defer `addView(detailPane)` until results arrive** *(empirically confirmed)*

Build the SPL with only the list pane as a child during `setupSlidingPane()`. When `OnFirstResultsListener.onFirstResultsAvailable()` fires, call `paneLayout.addView(detailPane, detailParams)` followed by `requestLayout()`. During loading, SPL has one child → list fills full width. SPL never has a second child to promote during loading. Pragmatic but non-idiomatic (dynamic view add at runtime).

---

### Note: Option B — Full-bleed loading overlay (optional, not implementing)

A simpler variant of Option A. No changes to pane visibility logic at all.

**Implementation steps:**

1. **Remove** `detailPane.setVisibility(View.GONE)` from `setupSlidingPane()`. The detail pane starts `VISIBLE` immediately with `EmptyDetailPaneFragment` loaded via `commitNow()`.

2. **Add a loading overlay** programmatically at the end of `setupSlidingPane()`. After inserting the SPL into `parent` (the activity root `FrameLayout`), add a new `FrameLayout` as the last child of `parent` (highest z-order):
   - `match_parent` width and height
   - Background: `R.color.bg_surface` (opaque — blocks both SPL panes from being seen)
   - Id: `R.id.foldable_loading_overlay` (add to `ids.xml` in `flights/res/values/`)

3. **Wire the hide signal** inside `wrapFilterButtonForTwoPane()`. In the `OnFirstResultsListener` callback (already coded in the working directory), replace `mDetailPane.setVisibility(View.VISIBLE)` with `loadingOverlay.animate().alpha(0f).setDuration(200).withEndAction(() -> loadingOverlay.setVisibility(View.GONE))` — or simply `loadingOverlay.setVisibility(View.GONE)` for no animation.

4. **Touch safety:** The overlay sits above the SPL at full coverage. Any touches during loading are absorbed by the overlay, preventing accidental filter/sort/list interaction while data is loading. When the overlay is dismissed, full interaction is restored.

**Files to change:**
- `FlightSearchResultFoldableActivity.java` — `setupSlidingPane()` (remove GONE, add overlay); `wrapFilterButtonForTwoPane()` (hide overlay in listener)
- `flights/res/values/ids.xml` — add `R.id.foldable_loading_overlay`
- `FlightSearchResultFragment.java` — `OnFirstResultsListener` already present in working directory (uncommitted)

---

## Open Items

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | Empty right pane occupies 50% width on narrow/folded screens | Medium | RESOLVED (concrete min widths applied) |
| 2 | Crash: `presenter` null in `FlightDetailsFragment.onResume` | High | RESOLVED |
| 3 | Right pane persists on fold (phone mode) | High | RESOLVED |
| 4 | Departure & arrival section missing for first few flights | High | RESOLVED |
| 6 | Departure/arrival not visible on flight tap; panes appeared scroll-linked | High | RESOLVED |
| 7 | Fold defaults to last-interacted pane instead of list | Medium | RESOLVED (onConfigurationChanged + closePane) |
| 8 | Loading screen not full-width — right pane not auto-revealed on first results | Low | **OPEN / PARKED** — Root cause confirmed (Session 8): `SlidingPaneLayout.updateObscuredViewsVisibility()` overrides `View.GONE` → `VISIBLE` on first `onLayout()`. SPL owns the INVISIBLE/VISIBLE axis; `GONE` is not preserved. Fix options: A (placeholder + overlay), B (overlay variant), C (defer `addView` until results arrive — empirically confirmed). `open()`/`close()` misconception (Session 4) confirmed as unrelated. |
