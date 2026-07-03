# Architecture — Module 10

## Logical Components

### 1. Address Normalization Service
Transforms user-entered address data into normalized, structured, tenant-scoped address records.

### 2. Geocoding Adapter Layer
Provides provider-agnostic forward and reverse geocoding using configurable providers.

### 3. Coordinate Validation Service
Validates latitude, longitude, precision, freshness, source, accuracy radius, and tenant-level allowed geography.

### 4. Spatial Index Service
Maintains indexed location keys such as geohash, S2 cell, H3 cell, or database-native geography fields.

### 5. Distance Matrix Service
Calculates straight-line, driving, walking, transit, or provider-specific travel metrics.

### 6. ETA Service
Computes estimated arrival time using configured routing provider, cached matrix data, or fallback approximations.

### 7. Service Area Engine
Evaluates whether a point belongs to a provider, company, tenant, city, polygon, radius, or configured zone.

### 8. Geofence Engine
Validates whether a mobile location event is inside an expected service boundary.

### 9. Live Location Session Service
Manages provider live-location sharing sessions, expiry, throttling, retention, and visibility.

### 10. Location Trust Signal Service
Generates non-final trust signals for spoofing, impossible movement, low accuracy, stale GPS, or inconsistent network data.

### 11. Provider Abstraction Registry
Allows Google Maps, Mapbox, OpenStreetMap/Nominatim, OSRM, Valhalla, Here, or internal services to be used without leaking provider-specific semantics into domain modules.

## Architecture Rule

No external module may directly call a map provider. All geospatial operations must pass through Module 10 contracts.
