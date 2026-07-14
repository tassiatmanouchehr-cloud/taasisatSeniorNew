# 11 — Extensibility Model

## 1. Extension points

Supported extension points:

- search provider adapter;
- tokenizer and analyzer;
- synonym dictionary;
- locale normalizer;
- filter compiler;
- ranking signal provider;
- ranking profile;
- facet definition;
- redaction profile;
- suggestion generator;
- abuse detector;
- telemetry exporter;
- saved search evaluator;
- projection builder.

## 2. Provider adapter interface

Adapters must implement:

- create_index;
- update_mapping;
- upsert_document;
- partial_update_document;
- delete_document;
- search;
- autocomplete;
- aggregate_facets;
- health_check;
- rotate_alias;
- bulk_operation;
- export_snapshot;
- compare_checksum.

## 3. Vertical extensions

Vertical-specific marketplaces may add:

- custom service attributes;
- custom capability codes;
- custom credentials;
- custom availability semantics;
- custom display labels;
- custom ranking boosts.

They must do so through tenant-specific schemas and projection extensions. The generic module must not embed the vertical terms.

## 4. Semantic search readiness

The architecture supports semantic/vector search as an optional adapter feature. Requirements:

- embeddings must not contain prohibited sensitive fields;
- embedding generation must be consent-aware;
- vector index must preserve tenant isolation;
- semantic ranking must be explainable enough for administrative review;
- lexical fallback must exist.

## 5. Versioning

Each extension artifact must be versioned:

- projection version;
- filter schema version;
- ranking profile version;
- redaction profile version;
- analyzer version;
- provider mapping version.

Reindex is required when incompatible changes are introduced.
