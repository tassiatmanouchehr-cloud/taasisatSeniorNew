# CCS — Core Configuration Specification for Module 10

## Configuration Scope

All configuration is tenant-scoped unless explicitly marked as platform-level.

## Required Configuration Keys

### geospatial.provider.primary_geocoder
Controls the primary geocoding provider.

Allowed examples:
- google_maps
- mapbox
- nominatim
- internal

### geospatial.provider.primary_router
Controls route and ETA provider.

### geospatial.provider.fallback_policy
Defines fallback behavior when primary provider fails.

Allowed values:
- fail_closed
- fallback_to_secondary
- fallback_to_cached
- fallback_to_haversine_low_confidence

### geospatial.coordinate.precision_policy
Defines how precise coordinates may be stored and exposed.

### geospatial.address.normalization_required
Whether structured normalization is required before request creation.

### geospatial.service_area.default_mode
Allowed values:
- radius
- polygon
- city
- region
- unrestricted

### geospatial.service_area.default_radius_meters
Default service radius when radius mode is used.

### geospatial.geofence.checkin_radius_meters
Default accepted radius for check-in validation.

### geospatial.geofence.checkout_radius_meters
Default accepted radius for check-out validation.

### geospatial.live_location.enabled
Enables or disables live-location sessions.

### geospatial.live_location.max_session_minutes
Maximum session lifetime.

### geospatial.live_location.update_interval_seconds
Minimum accepted interval between location updates.

### geospatial.location_retention.precise_coordinates_days
Retention period for precise coordinates.

### geospatial.location_retention.live_location_days
Retention period for live-location traces.

### geospatial.privacy.expose_precise_location_to_requester
Controls whether requester can see precise provider location.

Allowed values:
- never
- during_active_booking
- during_active_execution
- tenant_policy

### geospatial.trust.spoof_detection_enabled
Enables anomaly-signal generation.

### geospatial.cache.distance_matrix_ttl_seconds
Cache duration for distance matrix results.

## Configuration Rules

- Configuration changes must be audited.
- Provider keys/secrets are never stored in CCS documents; they belong in secure secret storage.
- Changes affecting privacy, retention, or geofence enforcement must create an audit record.
