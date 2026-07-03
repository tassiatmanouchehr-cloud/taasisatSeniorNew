# Operations Runbook

## Provider Outage

When a map/geocoding/routing provider fails:

1. Detect provider failure through health checks.
2. Apply tenant fallback policy.
3. Mark generated estimates with reduced confidence if fallback is approximate.
4. Publish operational incident event if impact crosses threshold.
5. Avoid silently changing pricing, matching, or booking decisions without confidence metadata.

## Distance Cache Corruption

1. Disable cache reads.
2. Recalculate critical route estimates.
3. Invalidate affected tenant cache namespace.
4. Audit incident resolution.

## Bad Geocoding Result

1. Allow authorized correction.
2. Store correction as normalized override.
3. Publish address corrected event if implemented.
4. Re-run affected service-area evaluations.

## High Cost Protection

- throttle distance matrix requests
- batch calculations
- cache repeated routes
- cap search radius
- prefer approximate pre-filter before expensive routing
- monitor provider quota

## Observability Metrics

- geocode success rate
- geocode confidence distribution
- route estimate latency
- provider error rate
- cache hit ratio
- live-location update volume
- geofence failure rate
- spoof signal rate
- precise location access count
