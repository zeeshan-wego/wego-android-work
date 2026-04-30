# [MOBILE-8206] Parallelise independent home screen sections to reduce TTI

**Jira:** https://wegomushi.atlassian.net/browse/MOBILE-8206
**Platform:** Android

## Problem

On home-screen cold start the user sees sections populate **one at a time**, with a long stall before the below-the-fold sections render. With ~30 sections (flights search, hotels search, weekend getaway, stories, deals, recent searches, and others) each issuing its own network call, even a modest 200 ms per section produces 2+ seconds of stalled rendering that the user perceives as a slow app.

## Solution

The home-section loading pipeline used to walk one section at a time — the next section never started until the previous one had finished. Each section's network call already runs on a background IO thread, so the slowdown was entirely in the queue, not in the network.

The queue gate is removed: the home view-model now dispatches every allowed section in a single pass, and the existing per-section IO threads do their work concurrently. Sections still appear in the same display order regardless of which one finishes first; one section's failure no longer blocks its siblings; and a scroll-driven "load more" call while a round is in flight remains a no-op.

No section APIs change, no UI behaviour changes, no analytics events are added or removed.

## Benefits

- **Faster perceived cold start.** Independent sections kick off in parallel instead of serially, eliminating multi-second stalls below the fold.
- **No regressions.** Render order, click handlers, analytics, and per-section error handling all preserved. Confirmed by 11 new unit tests covering parallel fan-out, stable insertion order, and per-section error isolation.
- **Resilience.** A single failing section can no longer prevent the rest of the home screen from loading.
- **Simpler state model.** A single boolean queue gate is replaced by a single in-flight counter; net code reduction in the home view-model.

## Acceptance Criteria

- [x] Independent home sections load concurrently rather than waiting on each other.
- [x] No regression in section ordering, click handlers, or analytics events.
- [x] Existing unit tests pass; new tests added for parallel-load completion ordering.
- [ ] Cold-start home TTI improves on a mid-tier device — **owned by QA** (out of scope for this ticket).
