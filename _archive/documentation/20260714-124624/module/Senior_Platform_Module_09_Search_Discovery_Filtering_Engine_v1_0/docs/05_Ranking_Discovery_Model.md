# 05 — Ranking & Discovery Model

## 1. Ranking principles

Ranking must be explainable, deterministic, configurable, and safe. Module 09 may rank discovery candidates, but must not override hard eligibility, compliance, tenant, or permission rules.

Hard filters always precede ranking.

## 2. Ranking pipeline

```text
Candidate retrieval
  → hard policy filtering
  → query relevance scoring
  → structured fit scoring
  → geo/time/availability scoring
  → trust/compliance demotions
  → fairness and diversity rules
  → business configurable boosts
  → deterministic tie-breakers
  → redaction
  → response
```

## 3. Ranking signal classes

| Signal | Description |
|---|---|
| text_relevance | lexical and semantic fit to query text |
| category_fit | match to selected service category or service unit |
| geo_fit | distance, service area coverage, travel feasibility |
| availability_fit | overlap with requested time window or capacity |
| price_fit | price range compatibility where visible |
| trust_fit | generic trust, verification, rating, quality state |
| freshness | recency of request, offer, profile, or availability |
| responsiveness | response timing or acceptance behavior |
| completion_quality | generic successful completion history |
| fairness_rotation | prevents permanent dominance by a small set of entities |
| policy_demotion | demotions from compliance, complaints, availability, or stale data |

## 4. Hard exclusions

The ranking engine must exclude before scoring:

- tenant mismatch;
- actor lacks permission;
- lifecycle state not discoverable;
- compliance blocked;
- trust safety blocked;
- entity deleted or suppressed;
- private profile not visible;
- time window incompatible when strict availability is requested;
- location outside service coverage when strict geo is requested;
- source module marks entity as non-searchable.

## 5. Ranking profile example

```json
{
  "ranking_profile_id": "provider_discovery_default_v1",
  "base_sort": "relevance",
  "boost_rules": [
    {"signal": "availability_fit", "weight": 0.25},
    {"signal": "geo_fit", "weight": 0.20},
    {"signal": "trust_fit", "weight": 0.20},
    {"signal": "freshness", "weight": 0.10}
  ],
  "demotion_rules": [
    {"signal": "stale_availability", "weight": -0.30},
    {"signal": "low_response_rate", "weight": -0.15}
  ],
  "tie_breakers": ["source_entity_id", "indexed_at"]
}
```

## 6. Discovery surfaces

Discovery surfaces are not just search endpoints. They are curated result contexts.

Supported surfaces:

- marketplace_home;
- provider_directory;
- request_board;
- category_browse;
- organization_directory;
- availability_explorer;
- admin_global_search;
- operator_workbench_search;
- support_case_lookup;
- saved_search_alert_evaluation.

Each surface defines:

- allowed result scopes;
- allowed filters;
- default facets;
- default ranking profile;
- max page size;
- telemetry policy;
- actor eligibility;
- redaction profile.

## 7. Fairness controls

Configurable fairness controls may include:

- rotation within score bands;
- exposure caps;
- new-provider exploration boost;
- anti-spam demotion;
- overexposure demotion;
- tenant-specific business policy boost.

Fairness controls must never bypass hard eligibility or compliance rules.

## 8. Explainability

The engine may return a result explanation to authorized actors:

- matched category;
- distance band;
- availability match;
- profile verification state;
- ranking bucket;
- primary sort reason.

Public users must not receive sensitive scoring internals or security-related demotion reasons.
