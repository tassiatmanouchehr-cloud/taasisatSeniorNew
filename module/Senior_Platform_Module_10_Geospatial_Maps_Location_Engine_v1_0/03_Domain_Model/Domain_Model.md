# Domain Model

## Core Entities

### LocationPoint
Represents a latitude/longitude pair with source, accuracy, timestamp, and tenant scope.

Required fields:
- location_point_id
- tenant_id
- latitude
- longitude
- accuracy_meters
- source_type
- captured_at
- precision_level
- created_by_actor_id

### StructuredAddress
Represents normalized address data.

Required fields:
- address_id
- tenant_id
- owner_actor_id optional
- country_code
- region
- city
- district optional
- street optional
- building optional
- postal_code optional
- formatted_address
- location_point_id optional
- verification_status

### ServiceArea
Represents where a provider, company, tenant, or marketplace actor can serve.

Supported types:
- radius
- polygon
- city
- region
- country
- imported_zone
- custom_grid

### RouteEstimate
Represents a computed path or distance result.

Required fields:
- route_estimate_id
- tenant_id
- origin_location_point_id
- destination_location_point_id
- travel_mode
- distance_meters
- duration_seconds
- provider_key
- confidence_score
- calculated_at
- expires_at

### GeofenceRule
Defines acceptable geographic boundaries for check-in, check-out, execution, or verification.

### LiveLocationSession
Represents a time-limited location sharing session.

### LocationTrustSignal
Represents a non-final risk signal produced by Module 10 and consumed by Trust/Compliance.

## Data Classification

Precise coordinates, live location, home addresses, and movement history are classified as sensitive operational data.
