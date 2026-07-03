# CES — Core Event Specification for Module 10

## Event Naming Rule

All events use the namespace:

`geospatial.<aggregate>.<event_name>.v1`

## Events

### geospatial.address.normalized.v1
Published when an address is normalized.

Payload:
- tenant_id
- address_id
- source_address_hash
- normalization_provider
- confidence_score
- actor_id
- occurred_at

### geospatial.address.geocoded.v1
Published when an address is converted to coordinates.

Payload:
- tenant_id
- address_id
- location_point_id
- provider_key
- confidence_score
- accuracy_meters
- occurred_at

### geospatial.location_point.captured.v1
Published when a location point is captured from user input, mobile GPS, browser geolocation, admin entry, or provider integration.

Payload:
- tenant_id
- location_point_id
- actor_id
- source_type
- accuracy_meters
- captured_at
- occurred_at

### geospatial.distance.calculated.v1
Published when a distance or matrix result is calculated.

Payload:
- tenant_id
- route_estimate_id
- origin_location_point_id
- destination_location_point_id
- travel_mode
- distance_meters
- duration_seconds
- provider_key
- confidence_score
- occurred_at

### geospatial.service_area.evaluated.v1
Published when a service-area decision is made.

Payload:
- tenant_id
- service_area_id
- location_point_id
- evaluation_result
- evaluation_reason_code
- actor_id optional
- occurred_at

### geospatial.geofence.evaluated.v1
Published when check-in, check-out, or execution location is evaluated against a geofence.

Payload:
- tenant_id
- geofence_rule_id
- location_point_id
- reference_entity_type
- reference_entity_id
- result
- distance_from_boundary_meters
- occurred_at

### geospatial.live_location.session_started.v1
Published when a live-location sharing session starts.

### geospatial.live_location.session_updated.v1
Published when a live-location session receives a valid update.

### geospatial.live_location.session_expired.v1
Published when a live-location session expires.

### geospatial.location_trust.signal_created.v1
Published when Module 10 identifies a location anomaly or trust signal.

Payload:
- tenant_id
- signal_id
- actor_id
- signal_type
- severity
- confidence_score
- reference_entity_type optional
- reference_entity_id optional
- occurred_at

## Event Rules

- Events must never expose raw provider API response payloads.
- Events must include tenant_id.
- Events must be immutable.
- Sensitive coordinates may be redacted, rounded, hashed, or referenced by ID according to CCS policy.
- Trust signals are advisory; enforcement belongs to Module 06.
