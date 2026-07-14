# Implementation Guide

## Recommended Database Capabilities

- tenant-scoped tables
- geography/geometry support where available
- indexed coordinates
- geohash/S2/H3 support for pre-filtering
- immutable audit table
- short-retention live-location table

## Suggested Tables

- geospatial_location_points
- geospatial_structured_addresses
- geospatial_service_areas
- geospatial_service_area_memberships
- geospatial_route_estimates
- geospatial_geofence_rules
- geospatial_geofence_evaluations
- geospatial_live_location_sessions
- geospatial_live_location_updates
- geospatial_location_trust_signals
- geospatial_provider_health
- geospatial_audit_log

## API Surface

- POST /geospatial/addresses/normalize
- POST /geospatial/addresses/geocode
- POST /geospatial/location-points/validate
- POST /geospatial/routes/estimate
- POST /geospatial/service-areas/evaluate
- POST /geospatial/geofences/evaluate
- POST /geospatial/live-location/sessions
- POST /geospatial/live-location/sessions/{id}/updates
- POST /geospatial/timezone/resolve

## Implementation Order

1. Tenant-scoped location point and address model
2. Provider abstraction
3. Geocoding and reverse geocoding
4. Distance/ETA service
5. Service areas
6. Geofence validation
7. Live-location sessions
8. Privacy and retention controls
9. Trust signal hooks
10. CES/CCS integration
11. Observability and operations dashboards

## Hard Rules

- Never let business modules call Google Maps, Mapbox, OSRM, Nominatim, or any provider directly.
- Never publish precise coordinates in public events unless explicitly permitted by configuration.
- Never use approximate fallback results without confidence metadata.
- Never mix tenant spatial indexes.
