# Security and Privacy

## Sensitive Data Categories

- precise latitude/longitude
- home or service addresses
- live location traces
- movement history
- geofence validation outcomes
- route history
- location trust signals

## Privacy Controls

- coordinate precision reduction
- location reference IDs instead of raw coordinates in events
- configurable retention
- purpose-limited access
- role-scoped visibility
- requester/provider reveal policies
- live-location session expiry
- audit trails for sensitive reads

## Spoofing and Anomaly Hooks

Module 10 may produce trust signals for:

- impossible travel speed
- stale GPS timestamp
- low accuracy radius
- emulator indicator
- inconsistent IP region
- repeated identical coordinates
- sudden coordinate jumps
- check-in far from destination
- route ETA inconsistency

These signals are not punishments. Enforcement belongs to Module 06.

## Provider Security

- API keys must be stored in secret storage.
- Provider responses must be minimized before storage.
- Provider-specific metadata must not leak into marketplace domain events.
- Provider failover must not bypass tenant privacy rules.

## Data Retention

Live location traces should have the shortest retention period compatible with operational, legal, and dispute-resolution needs.
