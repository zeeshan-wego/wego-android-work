# [Android] Display mode of transport

**Jira Ticket:** https://wegomushi.atlassian.net/browse/FMETA-2574
**Type:** Task
**Priority:** (not specified)
**Status:** In Progress
**Assignee:** bima@wego.com

## Description

Display the icon next to the station name based on the station type.

Display the details on the cards in the search result page.

Display the details on the flights detail page.

**Note:**
Only show mode of transport when at least 1 segment is not a flight (otherwise show aircraft type).

We used the following routes for testing in the staging environment: DMX–JXD, JXD–DMX, MKX–DMX, and DMX–MKX.

For example: https://sa-beta.wegostaging.com/en/flights/searches/jxd-dmx-2026-04-25/economy/1a:0c:0i?sort=score&order=desc&payment_methods=3%2C10%2C14%2C15%2C152%2C183%2C187%2C192

## Design

- Android Light mode: https://www.figma.com/design/Ku3Kv5jSCe2lejghfd7VJy/-Android--Flights?node-id=17520-23865&t=uLNayFuGGc40rqKa-11
- Android Dark mode: https://www.figma.com/design/Ku3Kv5jSCe2lejghfd7VJy/-Android--Flights?node-id=17520-26389&t=uLNayFuGGc40rqKa-11

## API Changes

### 1. Autocomplete

**Request:** `GET /autocomplete/flights/v1/search?locale=en&site_code=AE&search_for=destination&query=makkah&min_airports=1&types[]=airport&types[]=city&types[]=world_region`

**Response:** Added `stationType` field (values: `airport` / `bus_station` / `train_station`)

```json
[{
    "id": 18691,
    "code": "MKX",
    "name": "Makkah Train Station",
    "type": "airport",
    "stationType": "train_station",
    "lat": 21.4171,
    "long": 39.7893
}]
```

### 2. Polling Result & Trip Detail Endpoint

**airports attribute:** Added `stationType` (values: `airport` / `bus_station` / `train_station`)

```json
"airports": [
    {
        "name": "Cairo Airport",
        "enName": "Cairo Airport",
        "code": "CAI",
        "cityCode": "CAI",
        "stationType": "airport"
    }
]
```

**segments attribute:** Added `transportType` (values: `FLIGHT` / `TRAIN` / `BUS`)

```json
"segments": [
    {
        "durationMinutes": 665,
        "stopoverDurationMinutes": 150,
        "departureAirportCode": "DXB",
        "arrivalAirportCode": "KWI",
        "airlineCode": "J9",
        "cabin": "economy",
        "designatorCode": "J93122",
        "departureDateTime": "2026-04-17T14:30:00.000+04:00",
        "arrivalDateTime": "2026-04-18T00:35:00.000+03:00",
        "transportType": "FLIGHT"
    }
]
```

---
*Fetched from Jira on 2026-04-15*
