---
name: no-fly-zones
description: Load when planning a patrol mission to verify that the proposed flight path does not enter restricted or sensitive airspace. Covers NM-specific hard no-fly zones, tribal land boundaries, and neighbor property constraints.
---

# No-Fly Zones for NM Ranch Operations

## When to load

- A patrol mission is being planned and airspace clearance needs to be verified.
- A reactive dispatch is proposed and the most direct path may cross a boundary.
- A new ranch or paddock is being added to the system and its airspace envelope needs to be characterized.

## Summary

Part 107 establishes the national airspace framework, but NM has several site-specific restrictions that override the default rules for ranch operations. Chaco Culture NHP and Bandelier NM are absolute no-fly zones without NPS permits that take months to obtain. Tribal lands in NM are sovereign territory; overflights of the air column are governed by FAA but takeoff/landing on tribal land requires separate tribal permission. Neighbor property overflights without permission are legal under FAA rules (airspace is federal) but can create serious relationship issues in rural NM communities where land boundaries are taken seriously.

## Key facts

**Hard no-fly zones — NM specific**:

- **Chaco Culture National Historical Park** (San Juan County, NM): NPS interim policy prohibits UAS operations without a specific NPS Special Use Permit (SUP). Permit process: 90–180 days. GPS coordinates of park boundary must be loaded into geofence before any northern NM patrol within 30 miles.
- **Bandelier National Monument** (Los Alamos/Sandoval County, NM): same NPS UAS prohibition; hard geofence required. Note: Los Alamos National Laboratory (LANL) adjacent to Bandelier has additional security airspace restrictions (TFR Class A equivalent for portions).
- **Kirtland Air Force Base** (Bernalillo County): Class D airspace; LAANC required for all flights within 5-mile ring. NM Air National Guard flight operations may create TFRs.
- **White Sands Missile Range** (Doña Ana/Otero/Sierra counties): controlled airspace; extensive NOTAM activity. Operations within 25 miles require real-time NOTAM check; range is active most weekdays.
- **Tribal nations**: Navajo Nation (northwestern NM), Pueblo of Acoma, Pueblo of Zuni, Mescalero Apache, and others. FAA Part 107 governs the airspace; tribal government governs land below. Do not take off or land on tribal property without written tribal permission. Airspace overflight is legal.

**Controlled airspace requiring authorization**:
- **Class D** airports with Part 107-relevant airspace in NM: Santa Fe Regional (SAF), Las Cruces International (LRU), Roswell Air Center (ROW), Silver City-Grant County (SVC).
- **LAANC-authorized**: check aloft.ai or Kittyhawk for real-time LAANC grid before any flight within 5 miles of listed airports.
- **Class B**: Albuquerque International Sunport (ABQ) has a large Class B structure. NM ranch operations in Bernalillo/Sandoval/Valencia counties should be verified on FAA sectional chart.

**Neighbor property**:
- FAA permits airspace overflight at safe altitudes; no federal prohibition.
- NM range culture: do not overfly neighbor cattle at low altitude without notification; can cause scatter events; damages relationship.
- Best practice: notify neighbors within 0.5 miles of planned patrol area; offer shared situational awareness data.
- Trespass concern: if drone is forced to land on neighbor property due to emergency, retrieve promptly and communicate.

**TFRs (Temporary Flight Restrictions)**:
- Wildfire TFRs are common in NM from May–October; check NOTAM system before each flight day.
- Presidential or VIP movement TFRs active occasionally around Albuquerque and Santa Fe.
- FAA TFR map: tfr.faa.gov — check daily during fire season.

## Decision rules

```
IF proposed mission path crosses Chaco NHP or Bandelier NM boundary:
  → ABORT mission planning; reroute entirely; no exception without valid NPS SUP on file

IF proposed mission is within 5 miles of a Class D airport:
  → Check LAANC authorization before launch; if unavailable or denied, abort

IF proposed mission is within 25 miles of White Sands Missile Range:
  → Check active NOTAMs; abort if range activity restricts airspace

IF mission involves overflight of Navajo Nation or Pueblo lands (low pass <100m):
  → Verify tribal permission before flight; default to airspace corridor >100m AGL if permission not confirmed

IF TFR active over the ranch county:
  → Abort all missions until TFR expires; log reason; notify RPIC

IF neighbor property boundary is within proposed patrol path:
  → Route at >150m AGL over neighbor land OR redirect path to avoid
  → Log boundary proximity for future mission planning

IF mission requires airspace verification but LAANC system is offline:
  → Do not proceed; wait for LAANC restoration or obtain voice authorization from nearest ATCT
```

## Escalation / handoff

- Any airspace violation requires immediate RPIC notification and FAA incident report.
- Tribal permission issues: rancher must handle; agent cannot negotiate tribal permissions.
- TFR violation: immediate RTH; RPIC notified; document for FAA record.

## Sources

- FAA 14 CFR Part 107.
- FAA LAANC: faa.gov/uas/programs_partnerships/data_exchange.
- NPS UAS management policy: NPS Director's Order 100.
- FAA TFR system: tfr.faa.gov.
- FAA aeronautical chart — Albuquerque sectional.
- NM Tribal Government airspace coordination: contact NM Indian Affairs Department for tribal liaison contact.
