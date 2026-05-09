# Foldable PoC

**Jira Ticket:** FMETA-2579
**Type:** Feature / PoC
**Priority:** TBD

## Description

Proof of Concept (PoC) for foldable device support on the Wego Android app.
The goal is to test the look and feel of the app on a foldable Android phone model and verify the effort required.

## Scope

- Use current codebase, keep on a separate branch (no integration to develop/main)
- Flight search flow only
- No design reference — keep it simple, use good judgement

## User Flow

1. User starts a one-way search from home → flights menu
2. Search results open on a foldable device in a two-pane layout:
   - **Left pane:** Search results list
   - **Right pane:** Sort & Filters menu
3. When user selects a trip from the results:
   - Replace the **right pane** with the Flight Details page
4. Remaining booking process (after details) continues in a new Activity — no need to fit it on the right pane

## Adaptive Display Requirements

- Smooth transition between single-pane and multi-pane when folding/unfolding the device
- Use the right Android components so fold/unfold transitions are handled naturally
- Only the adaptive display aspect is in scope for this PoC

## Technical Approach

- Java/Kotlin + layout XMLs
- No separate PoC module — integrate within existing flight-related modules
- Use Android adaptive layout components (Window Size Classes, SlidingPaneLayout, or similar)
