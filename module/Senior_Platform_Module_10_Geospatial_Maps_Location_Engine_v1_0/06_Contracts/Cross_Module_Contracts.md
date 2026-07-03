# Cross-Module Contracts

## Module 01 Request Engine

Consumes:
- normalize_address
- geocode_address
- validate_location_point
- resolve_timezone

Provides:
- request location reference IDs

Rule: Module 01 must not store provider-specific geocoding responses.

## Module 02 Matching Engine

Consumes:
- calculate_distance
- calculate_eta
- evaluate_service_area
- nearby_candidates_query_support

Rule: Module 02 owns ranking; Module 10 only provides geospatial facts.

## Module 03 Booking & Assignment Engine

Consumes:
- validate_booking_distance_feasibility
- calculate_assignment_eta
- evaluate_provider_service_area

Rule: Booking decisions must cite route estimate IDs where location feasibility influenced assignment.

## Module 04 Service Execution Engine

Consumes:
- create_geofence_rule
- evaluate_checkin_location
- evaluate_checkout_location
- start_live_location_session
- update_live_location_session
- expire_live_location_session

Rule: Service execution state transitions remain in Module 04.

## Module 06 Trust, Safety & Compliance Engine

Consumes:
- location_trust_signal_created events
- geofence evaluation results
- spoof detection signals

Rule: Module 10 does not suspend, penalize, ban, or sanction actors.

## Module 08 Identity, Roles, Profiles & Access Engine

Consumes/Provides:
- saved addresses
- profile service areas
- actor location permissions

Rule: Module 08 owns identity and profile records; Module 10 owns location intelligence.

## Module 09 Search, Discovery & Filtering Engine

Consumes:
- spatial index references
- nearby query primitives
- distance filters
- service-area filters

Rule: Search scoring and discovery UX are Module 09 responsibilities.
