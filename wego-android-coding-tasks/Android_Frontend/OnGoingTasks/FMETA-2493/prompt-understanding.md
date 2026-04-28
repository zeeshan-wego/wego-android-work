# Update Baggage Filter Event Tracking to Align with dWeb Schema

**Ticket:** FMETA-2493

## Problem

The baggage filter tracking events on the Flight Details page use an outdated schema (from FMETA-1749) that doesn't match the standardized dWeb schema (FMETA-2454). This makes cross-platform analytics inconsistent.

## Goal

Replace the two separate baggage filter tracking events with a single unified `filter` + `applied` event that reports the current state of all active baggage filters as a JSON value.

## Current Behavior

When a user toggles a baggage filter on the Flight Details page, two separate tracking methods fire:
- `trackCabinBaggageFilterEvent()` → category: `flights_detail_page`, object: `baggage_filter`, action: `cabin_bag`, value: `selected`/`deselected`
- `trackCheckedBaggageFilterEvent()` → category: `flights_detail_page`, object: `baggage_filter`, action: `checked_bag`, value: `selected`/`deselected`

## Target Behavior

On every baggage filter toggle (cabin or checked), fire a single event:
- category: `flights_detail_page`
- object: `filter`
- action: `applied`
- value: JSON reflecting **all currently active** baggage filters, e.g. `{baggages: ["cabin"]}`, `{baggages: ["checked"]}`, `{baggages: ["cabin", "checked"]}`, or `{baggages: []}` when none selected

## Key Details

- On each toggle, evaluate **both** filter states and report the combined active filters
- No existing `filter` + `applied` event exists on the flight details page yet — this will be the first
- The Genzo constants `EventObject.filter` and `EventAction.applied` already exist in `FlightConstants.kt`
- The tracking fires from `FlightDetailsPresenter.java` via `WegoAnalyticsLibv3.logEventActions()`
- The filter state is tracked via `cabinBaggageFilter` and `checkedBaggageFilter` fields in the presenter

## What Changes

- `FlightDetailsPresenter.java` — replace `trackCabinBaggageFilterEvent()` and `trackCheckedBaggageFilterEvent()` with a single method that builds the JSON value from both filter states
- No UI changes, no ViewModel changes, no constants changes needed

## What Stays The Same

- `BookingOptionsAdapter` (UI) — no changes
- `FlightDetailsFragment` callback wiring — no changes
- `FlightDetailsViewModel` state management — no changes
- `FlightConstants.kt` Genzo constants — already has `filter` and `applied`
- All other tracking events — unaffected

## Applicable Rules

- `AGENTS.md` — Detekt strict mode (maxIssues=0), max line 120 chars, max method 60 lines
- `AGENTS.md` — Timber for logging, no println/Log.d
