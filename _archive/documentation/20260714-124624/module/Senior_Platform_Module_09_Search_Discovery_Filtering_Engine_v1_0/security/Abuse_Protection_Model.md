# Abuse Protection Model

## Controls

- actor and anonymous rate limiting;
- IP/device/session anomaly scoring;
- query complexity limits;
- cursor chain limits;
- high-cardinality facet restrictions;
- minimum bucket counts;
- private field non-indexing;
- suspicious filter pattern detection;
- repeated near-identical query detection;
- scraping detection;
- autocomplete throttling;
- saved search creation limits.

## Abuse signals

- excessive pagination depth;
- systematic alphabetic enumeration;
- repeated geo grid probing;
- high-cardinality facet probing;
- rapid saved search creation;
- permission-denied bursts;
- query patterns containing contact data extraction attempts.

## Response actions

- soft throttle;
- hard rate limit;
- disable facets;
- disable autocomplete;
- require authentication;
- emit search.abuse_signal_detected;
- escalate to Module 06.
