# Foldable Device Support — PoC Summary

**What this is:** A quick experiment to understand what it would take to make the Wego app look great on foldable phones.
**Who ran it:** Bima (Android Platform team)
**When:** April 2026
**Status:** Experiment complete. Not shipped — kept on a separate branch for review.

---

## What We Were Trying to Find Out

Foldable phones can unfold into a tablet-sized screen. We wanted to know:

- Can we take advantage of that bigger screen in the flight search flow?
- How much work would it actually take?
- What would break, and what would we get for free?

We kept the scope tight — flight search only, no design handoff required, no shipping to users.

---

## What We Built

A proof-of-concept of a **two-panel view** on the flight search results screen:

- **Left panel** — the list of flight results (same as today)
- **Right panel** — flight details, shown in-place when a user taps a result

On a regular (non-foldable) phone, or when the foldable is folded, the app works exactly as it does today — nothing changes for those users.

When the phone is unfolded, both panels appear side by side. Folding the phone back collapses it back to the normal view automatically, with no crashes or visual glitches.

---

## How We Got There — Step by Step

1. **Set up the two-panel framework** — We used an official Android component (provided by Google) that handles the side-by-side layout and the fold/unfold animation automatically. This was the right tool for the job.

2. **Wired up the search results list** — The existing search results screen slotted directly into the left panel with almost no changes.

3. **Connected flight details to the right panel** — Normally, tapping a flight opens a whole new screen. On a wide/unfolded screen, we intercept that tap and load the details into the right panel instead. On a narrow/folded screen, it still opens the full screen as before.

4. **Handled folding and unfolding** — We added logic so that folding the device always snaps back to the results list (not to whatever panel you last touched). Unfolding restores both panels automatically.

5. **Added a close button** — Users can dismiss the flight detail from the right panel with an X button, returning to the empty "no trip selected" state.

6. **Cleared stale results** — If a user changes their filter after viewing a flight, the right panel clears automatically so it doesn't show outdated information.

7. **Ran a navigation experiment** — We tested what happens when the right panel needs to show more than one thing (e.g. filter options on top of flight details). The experiment confirmed it works, but wiring it to the real filter controls is a separate phase of work.

---

## What We Learned

### Things that worked well (lower effort than expected)

- The fold/unfold animation is **completely free** — the Android component handles it automatically. We wrote zero animation code.
- Flight detail content **survives a fold** — when you unfold the phone, the detail you were looking at is still there. Also free.
- The changes to the flight results list were **minimal** — a few lines to route a tap differently on wide screens. The existing screen was reused as-is.

### Things that took more work than expected

- **A quirk in our existing code** prevented us from using the standard approach to set up the two-panel layout. We had to work around it, which added debugging time and created some fragility. A clean production version would fix this first.
- **Flight detail content is tightly coupled** to the screen it normally lives in. We had to replicate some setup logic to make it work in the right panel instead.
- **Keeping a button visible** on top of a panel required a workaround due to how Android stacks content. Any team building on this needs to know about this pattern.

### One thing still open

- **During the loading screen** (before results arrive), both panels are visible and split the screen. Ideally, the loading screen should be full-width and the right panel should only appear once results are ready. We identified the root cause and three ways to fix it, but parked it for now since the loading screen is a short transient state with no content to show in the right panel anyway.

---

## What This Tells Us About Production Readiness

| Question | Answer |
|---|---|
| Is foldable support possible without a full rewrite? | Yes |
| Is it free / trivial? | No — but the core is manageable |
| What's the biggest blocker? | A quirk in the existing flight search code that needs fixing before a clean implementation is possible |
| Can we ship this branch? | No — it is a standalone experiment, not production-ready |
| What's next if we want to productionise it? | Fix the code quirk, resolve the loading screen, then tackle Phase 2 (filter panel) |

---

## Phase 2 — What's Deferred

The right panel currently only shows flight details. The original goal also included showing the **Sort & Filter options** in the right panel (so users don't have to open a drawer). That part was scoped out and set aside:

- Effort estimate: approximately 3 weeks of engineering work
- Main risk: the filter panel has a lot of moving parts and untangling it is the bulk of the work
- The experiment confirmed the navigation model works — Phase 2 just needs real filter content wired in

---

*Full technical report (for engineers): see `poc-report.md` in this folder.*
*Full session-by-session log: see `implementation-log.md` in this folder.*
