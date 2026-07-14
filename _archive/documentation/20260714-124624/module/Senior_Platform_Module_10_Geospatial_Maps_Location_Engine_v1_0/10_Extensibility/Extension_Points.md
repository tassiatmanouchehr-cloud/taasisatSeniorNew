# Extension Points

## Map Provider Adapter
Supports adding providers without changing marketplace modules.

Required adapter methods:
- geocode_address
- reverse_geocode
- calculate_route
- calculate_distance_matrix
- validate_provider_response
- estimate_cost

## Spatial Index Strategy
Supported strategies:
- database geography type
- geohash
- S2 cells
- H3 hex index
- external search index

## Service Area Strategy
Supported strategies:
- radius-based
- polygon-based
- administrative boundary
- imported GIS zone
- provider/company custom area

## Privacy Strategy
Supports tenant-specific exposure policies.

## Trust Signal Strategy
Allows custom anomaly detectors to be plugged in without enforcement logic.

## Routing Strategy
Allows different modes:
- straight_line
- driving
- walking
- cycling
- public_transit
- provider_defined

## Localization Strategy
Allows country-specific address formats, postal codes, region names, and map provider preferences.
