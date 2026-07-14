# Generic Service Marketplace Framework

**Module 03 — Booking, Assignment & Service Activation Engine**

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Frozen |
| **Document Owner** | Product Architecture |
| **Project** | Generic Service Marketplace Framework Reference Implementation |
| **Module Owner** | Platform Owner |
| **Depends On** | Module 01 — Request Engine, Module 02 — Matching Engine |
| **Next Modules** | Module 04 — Service Execution / Care Delivery Engine, Module 05/06 — Payment & Settlement |
| **Language** | Persian business domain, English technical structure |

> Module 01 and Module 02 are Frozen and Approved and are treated as baseline. Module 03 must not change their decisions unless a major architectural conflict is discovered.

# 09 — Service Assignment Specification

## Purpose
Define the Service Assignment: the formal link between one service need (or a package covering several) and the provider who has actually committed to deliver it.

## Business Goal
Make sure "assigned" always means a real party has accepted responsibility — never just that the customer clicked a button.

## Functional Specification

- A Service Assignment is created only after the responsible party's commitment succeeds (BR-312) — not at the moment of customer selection.
- Three creation paths exist, matching the three commitment paths (FR-302):
  - **Independent provider:** Assignment confirmed once the provider personally accepts.
  - **Company provider:** Assignment confirmed once the company accepts; the named provider may later be substituted by the company under BR-309.
  - **Company package:** Assignment(s) confirmed once the company accepts at the company level; provider(s) are assigned by the company afterward.
- A multi-need request produces multiple Assignments grouped into an AssignmentPlan (BR-313).
- Each Assignment links to exactly one Service Need, or is explicitly marked as a package Assignment covering several needs (BR-314).
- An Assignment can move to REPLACED if the company substitutes the provider, or to FAILED if commitment is rejected or times out.

## Business Rules
See `03_BUSINESS_RULES.md` — BR-307 through BR-314, BR-320, BR-321, BR-323, BR-324.

## Non-Functional Requirements
- Every state transition is auditable (actor, reason, timestamp).
- Assignment failure must never silently strand a Service Need — it must trigger BR-320's return-to-matching flow.

## Edge Cases (structural, non-legal)
- Company substitutes a provider after the customer had already seen and expected a specific named provider — must trigger a customer-facing notice (BR-309, BR-323).
- Two needs in the same request follow different commitment paths at once (e.g. one independent provider, one company package) — each Assignment resolves independently.

## Future Extension
- Automatic re-matching suggestion when an Assignment fails, instead of returning purely to manual/operator attention.

## Open Questions
- Whether repeated company substitutions on the same case should themselves trigger a review flag was raised implicitly but not decided; left open for a future session.

## Related ADR
ADR-03-01, ADR-03-02, ADR-03-03, ADR-03-06 (see `20_ADR.md`)

## Related Domain Objects
ServiceCase, AssignmentPlan, ProviderCommitment, SelectionLock
