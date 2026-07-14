# Test Strategy

## 1. Unit tests

- query normalization;
- filter validation;
- filter compiler;
- ranking profile selection;
- redaction profile application;
- permission tag evaluation;
- idempotency key generation;
- cursor signing and validation;
- facet bucket threshold enforcement.

## 2. Integration tests

- Module 01 request projection indexing;
- Module 08 profile projection indexing;
- Module 06 compliance suppression;
- Module 03 availability update;
- Module 07 saved search notification handoff;
- provider adapter search and aggregation.

## 3. Security tests

- tenant isolation;
- cross-tenant denial;
- anonymous private result denial;
- field redaction fail closed;
- facet enumeration prevention;
- rate-limit enforcement;
- cursor tampering rejection.

## 4. Reindex tests

- blue/green alias rotation;
- failed operation replay;
- stale event rejection;
- source version ordering;
- checksum comparison;
- drift reconciliation.

## 5. Performance tests

- p95 query latency;
- p99 query latency;
- autocomplete latency;
- facet aggregation latency;
- indexing throughput;
- critical suppression lag.

## 6. Regression tests

- no domain-specific terms in generic module artifacts;
- all public results pass redaction;
- all private results pass permission policy;
- saved search dedupe prevents duplicate alerts.
