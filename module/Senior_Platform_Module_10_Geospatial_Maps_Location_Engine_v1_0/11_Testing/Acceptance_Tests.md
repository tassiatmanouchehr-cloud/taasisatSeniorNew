# Acceptance Tests

## Tenant Isolation
- A tenant cannot read another tenant's saved addresses.
- A tenant cannot use another tenant's service-area polygons.
- Distance cache keys must be tenant-scoped.

## Address and Geocoding
- Valid address can be normalized.
- Invalid address returns structured error.
- Low-confidence geocode is flagged.
- Manual coordinate override is audited.

## Distance and ETA
- Distance result includes provider, mode, confidence, and expiry.
- Routing provider failure follows configured fallback policy.
- Cached matrix result respects TTL.

## Service Areas
- Point inside radius returns allowed.
- Point outside radius returns denied.
- Point inside polygon returns allowed.
- Boundary cases are deterministic and documented.

## Geofence
- Check-in inside allowed radius succeeds.
- Check-in outside allowed radius fails or flags according to policy.
- Low-accuracy GPS can produce warning rather than hard failure according to CCS.

## Live Location
- Session cannot start if disabled.
- Session expires automatically.
- Updates faster than configured interval are throttled.
- Expired session rejects updates.

## Privacy
- Requester cannot see precise provider location unless policy permits.
- Support precise-location access creates audit record.
- Retention cleanup removes expired live-location traces.

## Trust Signals
- Impossible movement creates advisory signal.
- Stale GPS creates advisory signal.
- Module 10 does not apply sanctions.
