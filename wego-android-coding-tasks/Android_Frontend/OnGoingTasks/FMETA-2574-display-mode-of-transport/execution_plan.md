# Execution Plan: [FMETA-2574] Display Mode of Transport

**Branch:** `feature/fmeta-2574-display-mode-of-transport`
**Jira:** https://wegomushi.atlassian.net/browse/FMETA-2574

---

## Summary

Display transport mode (flight/train/bus) across three surfaces in the flights feature: autocomplete icons, search result card logos, and flight detail segment display. Driven by two new API fields: `stationType` on airports and `transportType` on segments.

---

## Approach

- **Minimal surface area**: Changes are scoped to the data models, two autocomplete adapters, and `FlightDetailsUiUtils.kt`. The search result card adapter requires no changes — existing dual-logo logic and Cloudinary already handle train/bus logos correctly.
- **Interface-first**: Add `getTransportType()` to the `FlightSegment` interface so all implementations are forced to comply. Do the same for `FlightAirport`/`getStationType()`.
- **Backward-compatible**: New fields default to null — all-flight trips behave exactly as before.
- **No hardcoded strings**: Transport type labels ("Train", "Bus") will use localisation string resources.

---

## Model Execution Strategy

Two models are used. Orchestration is **automatic** — the main Sonnet session spawns a Haiku
agent for Phase 3A, then handles Phase 3B itself. You just approve the agent tool call.

```
Phase 3A — Haiku agent (spawned automatically)
  Steps 1–4 + model tests (10 mechanical file changes)

Phase 3B — Sonnet main session
  Step 5 + util tests (FlightDetailsUiUtils.kt logic + edge-case tests)

Phase 3C — Haiku test-runner agent (background, spawned after 3B)
  ./gradlew :flights:testPlaystoreDebugUnitTest --rerun-tasks
```

**Why the split at Step 5:** `FlightDetailsUiUtils.kt` requires understanding the segment loop
context, the backward-compatibility constraint, and the exact placement of `hasMixedTransport()`
relative to the loop. Getting this wrong causes silent regressions on all-flight trips.
Everything before it is pattern-matching on known structures.

---

## Phase 3A — Haiku Agent Prompt (self-contained)

> This section is the verbatim prompt passed to the Haiku agent. It contains everything
> the agent needs — no session context required.

---

**AGENT TASK: FMETA-2574 Phase 3A — Mechanical layer (10 file changes)**

Project root: `/Users/bhimz/claude-workspace/agent-01/wego-android-n`
Branch: `feature/fmeta-2574-display-mode-of-transport` (already checked out)
Your job: make exactly the changes below. Read each file before editing. Do not add
anything beyond what is specified. Follow existing code style in each file.
After all edits, run: `./gradlew :flights:testPlaystoreDebugUnitTest --rerun-tasks`
Report PASS or FAIL with details.

---

**Change 1 — ConstantsLib.java**
File: `libbase/src/main/java/com/wego/android/ConstantsLib.java`

Find the `Places` interface (~line 1487). Inside it, after `String TYPE_AIRPORT = "airport";`, add:
```java
String STATION_TYPE_AIRPORT = "airport";
String STATION_TYPE_TRAIN = "train_station";
String STATION_TYPE_BUS = "bus_station";
```

Then find the closing brace of the outermost `ConstantsLib` class and, just before it, add a
new top-level interface:
```java
interface TransportType {
    String FLIGHT = "FLIGHT";
    String TRAIN = "TRAIN";
    String BUS = "BUS";
}
```

---

**Change 2 — strings.xml**
File: `localisation/src/main/res/values/strings.xml`

Find any existing `<string name="lbl_...">` entry and add nearby:
```xml
<string name="lbl_transport_train">Train</string>
<string name="lbl_transport_bus">Bus</string>
```

---

**Change 3 — FlightAirport.java (interface)**
File: `flights/src/main/java/com/wego/android/data/models/interfaces/FlightAirport.java`

Add before the closing `}` of the interface:
```java
@Nullable
String getStationType();
```
Add import at top: `import androidx.annotation.Nullable;`

---

**Change 4 — FlightSegment.java (interface)**
File: `flights/src/main/java/com/wego/android/data/models/interfaces/FlightSegment.java`

Add before the closing `}` of the interface (after the existing `@Nullable String getId();`):
```java
@Nullable
String getTransportType();
```
`@Nullable` import already exists in this file.

---

**Change 5 — JacksonFlightAirport.java**
File: `flights/src/main/java/com/wego/android/data/models/JacksonFlightAirport.java`

Add field after existing fields:
```java
String stationType;
```

Add getter (implement interface method):
```java
@Override
@Nullable
public String getStationType() {
    return stationType;
}
```
Add import: `import androidx.annotation.Nullable;`

---

**Change 6 — JacksonFlightSegment.java**
File: `flights/src/main/java/com/wego/android/data/models/JacksonFlightSegment.java`

Add field after `String id;`:
```java
String transportType;
```

Add getter after `public String getCabin()`:
```java
@Override
@Nullable
public String getTransportType() {
    return transportType;
}
```

In the copy constructor (`JacksonFlightSegment(String input)`), after
`this.cabin = segment.cabin;`, add:
```java
this.transportType = segment.transportType;
```

`@Nullable` and `@Override` imports already exist in this file.

---

**Change 7 — FlightSearchLocationAdapter.java**
File: `flights/src/main/java/com/wego/android/features/flightchooselocation/FlightSearchLocationAdapter.java`

Replace this block (around line 90):
```java
if(ConstantsLib.Places.TYPE_AIRPORT.equalsIgnoreCase(item.getType())){
    holder.ivLocationType.setImageResource(R.drawable.ic_flight);
}else{
   holder.ivLocationType.setImageResource(R.drawable.ic_location_pin);
}
```
With:
```java
String stationType = item.getStationType();
if (ConstantsLib.Places.STATION_TYPE_TRAIN.equalsIgnoreCase(stationType)) {
    holder.ivLocationType.setImageResource(R.drawable.ic_train);
} else if (ConstantsLib.Places.STATION_TYPE_BUS.equalsIgnoreCase(stationType)) {
    holder.ivLocationType.setImageResource(R.drawable.ic_bus);
} else if (ConstantsLib.Places.TYPE_AIRPORT.equalsIgnoreCase(item.getType())) {
    holder.ivLocationType.setImageResource(R.drawable.ic_flight);
} else {
    holder.ivLocationType.setImageResource(R.drawable.ic_location_pin);
}
```

NOTE: `ic_train` and `ic_bus` drawables may not exist yet. If Android Studio reports a
resource error at build time, use `ic_flight` as a temporary placeholder and add a
`// TODO FMETA-2574: replace with ic_train` comment. Do NOT fail the task over missing drawables.

---

**Change 8 — FlightChooseLocationStickyListAdapter.java**
File: `flights/src/main/java/com/wego/android/features/flightchooselocation/FlightChooseLocationStickyListAdapter.java`

Replace this block (around line 122):
```java
if (ConstantsLib.Places.TYPE_AIRPORT.equalsIgnoreCase(currentItem.getType())) {
    holder.ivLocationType.setImageResource(R.drawable.ic_flight);
} else {
    holder.ivLocationType.setImageResource(R.drawable.ic_map_pin_new_form);
}
```
With:
```java
String stationType = currentItem.getStationType();
if (ConstantsLib.Places.STATION_TYPE_TRAIN.equalsIgnoreCase(stationType)) {
    holder.ivLocationType.setImageResource(R.drawable.ic_train);
} else if (ConstantsLib.Places.STATION_TYPE_BUS.equalsIgnoreCase(stationType)) {
    holder.ivLocationType.setImageResource(R.drawable.ic_bus);
} else if (ConstantsLib.Places.TYPE_AIRPORT.equalsIgnoreCase(currentItem.getType())) {
    holder.ivLocationType.setImageResource(R.drawable.ic_flight);
} else {
    holder.ivLocationType.setImageResource(R.drawable.ic_map_pin_new_form);
}
```

Same drawable caveat as Change 7.

---

**Change 9 — JacksonFlightSegmentTest.kt (NEW FILE)**
Path: `flights/src/test/java/com/wego/android/data/models/JacksonFlightSegmentTest.kt`

```kotlin
package com.wego.android.data.models

import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class JacksonFlightSegmentTest {

    private val gson = Gson()

    @Test
    fun `transportType is deserialized correctly when value is FLIGHT`() {
        val json = """{"transportType": "FLIGHT"}"""
        val segment = gson.fromJson(json, JacksonFlightSegment::class.java)
        assertEquals("FLIGHT", segment.transportType)
    }

    @Test
    fun `transportType is deserialized correctly when value is TRAIN`() {
        val json = """{"transportType": "TRAIN"}"""
        val segment = gson.fromJson(json, JacksonFlightSegment::class.java)
        assertEquals("TRAIN", segment.transportType)
    }

    @Test
    fun `transportType is null when field is absent from JSON`() {
        val json = """{"airlineCode": "EK"}"""
        val segment = gson.fromJson(json, JacksonFlightSegment::class.java)
        assertNull(segment.transportType)
    }
}
```

---

**Change 10 — JacksonFlightAirportTest.kt (NEW FILE)**
Path: `flights/src/test/java/com/wego/android/data/models/JacksonFlightAirportTest.kt`

```kotlin
package com.wego.android.data.models

import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class JacksonFlightAirportTest {

    private val gson = Gson()

    @Test
    fun `stationType is deserialized correctly when value is airport`() {
        val json = """{"code": "DXB", "stationType": "airport"}"""
        val airport = gson.fromJson(json, JacksonFlightAirport::class.java)
        assertEquals("airport", airport.stationType)
    }

    @Test
    fun `stationType is deserialized correctly when value is train_station`() {
        val json = """{"code": "MKX", "stationType": "train_station"}"""
        val airport = gson.fromJson(json, JacksonFlightAirport::class.java)
        assertEquals("train_station", airport.stationType)
    }

    @Test
    fun `stationType is null when field is absent from JSON`() {
        val json = """{"code": "CAI"}"""
        val airport = gson.fromJson(json, JacksonFlightAirport::class.java)
        assertNull(airport.stationType)
    }
}
```

---

**END OF AGENT PROMPT**

---

## Files to Change

### Phase 3A — Haiku (mechanical layer)

| File | Module | Change |
|------|--------|--------|
| `libbase/src/main/java/com/wego/android/ConstantsLib.java` | `libbase` | Add `STATION_TYPE_TRAIN/BUS` to `Places`; new `TransportType` interface |
| `localisation/src/main/res/values/strings.xml` | `localisation` | Add `lbl_transport_train`, `lbl_transport_bus` |
| `data/models/interfaces/FlightAirport.java` | `flights` | Add `@Nullable String getStationType()` |
| `data/models/interfaces/FlightSegment.java` | `flights` | Add `@Nullable String getTransportType()` |
| `data/models/JacksonFlightAirport.java` | `flights` | Add `stationType` field + getter |
| `data/models/JacksonFlightSegment.java` | `flights` | Add `transportType` field + getter + copy constructor |
| `features/flightchooselocation/FlightSearchLocationAdapter.java` | `flights` | Icon logic using `stationType` |
| `features/flightchooselocation/FlightChooseLocationStickyListAdapter.java` | `flights` | Same icon logic |
| `data/models/JacksonFlightSegmentTest.kt` (new) | `flights` | `transportType` deserialization tests |
| `data/models/JacksonFlightAirportTest.kt` (new) | `flights` | `stationType` deserialization tests |

> Drawables `ic_train.xml` and `ic_bus.xml` are user-provided. Place in
> `flights/src/main/res/drawable/` before Phase 3A begins. If not yet available,
> Haiku uses placeholder references (`ic_flight` temporarily) and leaves a `// TODO: replace` comment.

### Phase 3B — Sonnet (logic layer)

| File | Module | Change |
|------|--------|--------|
| `util/FlightDetailsUiUtils.kt` | `flights` | Add `hasMixedTransport()`; modify `addAdditionalStops()` |
| `util/FlightDetailsUiUtilsTest.kt` | `flights` | Add `hasMixedTransport()` test cases |

### Assets (user-provided, not generated)

| File | Module | Change |
|------|--------|--------|
| `flights/src/main/res/drawable/ic_train.xml` | `flights` | New train icon |
| `flights/src/main/res/drawable/ic_bus.xml` | `flights` | New bus icon |

---

## Detailed Implementation Steps

> **How to use this section:**
> Steps 1–4 → run as a Haiku agent (spawn via Agent tool with `model: "haiku"`) or switch manually with `/model claude-haiku-4-5-20251001`.
> Steps 5–6 → run in the main Sonnet session.
> Step 7 → test-runner agent (Haiku, background).

### Step 1: Add Constants  `[HAIKU]`

**`ConstantsLib.java`** — extend the existing `Places` interface with station type values, and add a new `TransportType` interface:

```java
interface Places {
    // existing...
    String STATION_TYPE_AIRPORT = "airport";
    String STATION_TYPE_TRAIN = "train_station";
    String STATION_TYPE_BUS = "bus_station";
}

interface TransportType {
    String FLIGHT = "FLIGHT";
    String TRAIN = "TRAIN";
    String BUS = "BUS";
}
```

### Step 2: Add Localisation Strings  `[HAIKU]`

**`localisation/src/main/res/values/strings.xml`** — add:
```xml
<string name="lbl_transport_train">Train</string>
<string name="lbl_transport_bus">Bus</string>
```

### Step 3: Update Data Models  `[HAIKU]`

**`interfaces/FlightAirport.java`** — add:
```java
@Nullable
String getStationType();
```

**`JacksonFlightAirport.java`** — add field + getter:
```java
String stationType;

@Override
@Nullable
public String getStationType() {
    return stationType;
}
```

**`interfaces/FlightSegment.java`** — add:
```java
@Nullable
String getTransportType();
```

**`JacksonFlightSegment.java`** — add field, getter, copy-constructor assignment:
```java
// field
String transportType;

// getter
@Override
@Nullable
public String getTransportType() {
    return transportType;
}

// in copy constructor (JacksonFlightSegment(String input)):
this.transportType = segment.transportType;
```

### Step 4: Update Autocomplete Adapters  `[HAIKU]`

Both `FlightSearchLocationAdapter.java` (line ~90) and `FlightChooseLocationStickyListAdapter.java` (line ~122) have the same icon logic. Replace in both:

```java
// Before:
if (ConstantsLib.Places.TYPE_AIRPORT.equalsIgnoreCase(item.getType())) {
    holder.ivLocationType.setImageResource(R.drawable.ic_flight);
} else {
    holder.ivLocationType.setImageResource(R.drawable.ic_location_pin);
}

// After:
String stationType = item.getStationType();
if (ConstantsLib.Places.STATION_TYPE_TRAIN.equalsIgnoreCase(stationType)) {
    holder.ivLocationType.setImageResource(R.drawable.ic_train);
} else if (ConstantsLib.Places.STATION_TYPE_BUS.equalsIgnoreCase(stationType)) {
    holder.ivLocationType.setImageResource(R.drawable.ic_bus);
} else if (ConstantsLib.Places.TYPE_AIRPORT.equalsIgnoreCase(item.getType())) {
    holder.ivLocationType.setImageResource(R.drawable.ic_flight);
} else {
    holder.ivLocationType.setImageResource(R.drawable.ic_location_pin);
}
```

Note: `stationType` takes priority over `type` for icon selection. If `stationType` is `airport`, it falls through to the `type` check which handles it.

### Step 5: Update Flight Detail Segment Display  `[SONNET]`

**`FlightDetailsUiUtils.kt`** — add helper function before `addAdditionalStops`:

```kotlin
private fun hasMixedTransport(segments: List<FlightSegment>): Boolean {
    return segments.any {
        val t = it.transportType
        t != null && !t.equals(ConstantsLib.TransportType.FLIGHT, ignoreCase = true)
    }
}
```

Modify `addAdditionalStops()` — replace the `aircraftType` block (lines ~169-173) with:

```kotlin
val legHasMixedTransport = hasMixedTransport(segments)
val transportType = segment.transportType
if (legHasMixedTransport && transportType != null &&
    !transportType.equals(ConstantsLib.TransportType.FLIGHT, ignoreCase = true)
) {
    if (sb.toString().isNotEmpty()) sb.append(", ")
    val label = when {
        transportType.equals(ConstantsLib.TransportType.TRAIN, ignoreCase = true) ->
            activity.getString(com.wego.android.localisation.R.string.lbl_transport_train)
        transportType.equals(ConstantsLib.TransportType.BUS, ignoreCase = true) ->
            activity.getString(com.wego.android.localisation.R.string.lbl_transport_bus)
        else -> transportType
    }
    sb.append(label)
} else if (!TextUtils.isEmpty(segment.aircraftType)) {
    if (sb.toString().isNotEmpty()) sb.append(", ")
    sb.append(segment.aircraftType)
}
```

`hasMixedTransport` is called once per leg (outside the segment loop) for efficiency.

### Step 6: Place New Drawable Assets  `[USER ACTION]`

- `flights/src/main/res/drawable/ic_train.xml` — provided by user
- `flights/src/main/res/drawable/ic_bus.xml` — provided by user

---

## What Is NOT Changing

- **`PLFlightSearchResultsAdapter.kt`**: No changes. The existing `setupAirlineLogos()` already handles 1 or 2 airline codes, and Cloudinary returns correct logos for train/bus operator codes. The API will include the train/bus operator code in `airlineCodes` for mixed itineraries.
- **`JacksonPlace.java` and `AutoSuggestResponse.kt`**: Already have `stationType`. No changes needed.
- **Logo fetching logic**: `CloudinaryImageUtilLib` unchanged — it handles all operator types.

---

## Test Plan

> Test-runner agent (Haiku, background) is spawned after Phase 3B completes.
> Command: `./gradlew :flights:testPlaystoreDebugUnitTest --rerun-tasks`

### `FlightDetailsUiUtilsTest.kt` — new test cases for `hasMixedTransport()`  `[SONNET]`

| Scenario | Expected |
|----------|----------|
| All segments have `transportType = "FLIGHT"` | `false` |
| All segments have `transportType = null` | `false` |
| One segment has `transportType = "TRAIN"` | `true` |
| One segment has `transportType = "BUS"` | `true` |
| Mixed: one FLIGHT + one TRAIN | `true` |
| Empty segment list | `false` |

### `JacksonFlightSegmentTest.kt` (new) — JSON deserialization  `[HAIKU]`

| Scenario | Expected |
|----------|----------|
| JSON with `transportType: "FLIGHT"` | `getTransportType() == "FLIGHT"` |
| JSON with `transportType: "TRAIN"` | `getTransportType() == "TRAIN"` |
| JSON without `transportType` field | `getTransportType() == null` |

### `JacksonFlightAirportTest.kt` (new) — JSON deserialization  `[HAIKU]`

| Scenario | Expected |
|----------|----------|
| JSON with `stationType: "airport"` | `getStationType() == "airport"` |
| JSON with `stationType: "train_station"` | `getStationType() == "train_station"` |
| JSON without `stationType` field | `getStationType() == null` |

---

## Documentation Updates

No API spec or ERD changes (this is a UI feature consuming existing API contracts).

---

## Acceptance Criteria

- [ ] Autocomplete shows train icon for `train_station` entries
- [ ] Autocomplete shows bus icon for `bus_station` entries
- [ ] Autocomplete still shows flight icon for regular airports
- [ ] Search result card shows correct operator logo(s) via Cloudinary
- [ ] Mixed itinerary card shows two logos (flight operator + train/bus operator)
- [ ] Flight detail shows "Train" / "Bus" label instead of `aircraftType` for non-FLIGHT segments
- [ ] Flight detail shows `aircraftType` unchanged for all-flight trips
- [ ] All existing tests pass
- [ ] New tests pass

---

## Execution Tracking

- **Started:** (to be filled)
- **Developer:** bima@wego.com
- **Branch:** feature/fmeta-2574-display-mode-of-transport
- **Collaborators:** (none)
