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

# 18 — Test Scenarios

> Scope note: these cover the **structural** flows decided in Discovery. The legally sensitive crisis-scenario library (internet loss, GPS off, death, accident, hospitalization, etc.) is explicitly deferred — see `00_README.md` → Open Issues — and is not tested here.

## Selection Lock Tests

- TS-301: Selection Lock is created on customer selection.
- TS-302: Lock expires after its TTL without commitment.
- TS-303: Expired lock releases the option and notifies the customer.
- TS-304: Only one active lock exists per Service Need at a time.

## Provider Commitment Tests

- TS-305: Independent provider can accept a commitment request.
- TS-306: Independent provider can reject a commitment request.
- TS-307: Company can accept on behalf of a company provider.
- TS-308: Company can accept for a company-package Assignment.
- TS-309: Commitment request that is not answered in time times out.

## Assignment Creation Tests

- TS-310: Assignment is created only after successful commitment, not at selection time.
- TS-311: Multi-need request produces an Assignment Plan with one Assignment per need.
- TS-312: Assignment links correctly to its Service Need.
- TS-313: Failed commitment marks the Assignment FAILED and returns the need toward Matching.

## Company Substitution Tests

- TS-314: Company can substitute the assigned provider before service start.
- TS-315: Substitution after customer saw a specific named provider triggers a customer notice.
- TS-316: Substitution reason is recorded.

## Service Case Tests

- TS-317: Service Case is created once at least one Assignment begins confirming.
- TS-318: Service Case correctly reflects mixed per-need status for multi-need requests.
- TS-319: Service Case status is visible live in customer and provider dashboards without a separate summary screen.

## Session & Coordination Tests

- TS-320: First Session is created immediately once timing is confirmed.
- TS-321: Full session schedule is created for a recurring contract.
- TS-322: Reminder is sent ahead of appointment time.
- TS-323: Provider signalling "on the way" updates session state.
- TS-324: Non-response close to appointment time triggers immediate contact plus company involvement (BR-318).
- TS-325: Customer is asked at appointment time whether the provider arrived.
- TS-326: Single session in a recurring contract can be cancelled without affecting the rest.

## Manual Intervention Tests

- TS-327: Platform Owner/support with permission can place a Service Case on hold.
- TS-328: A held Service Case cannot progress to READY_TO_START.
- TS-329: Hold release resumes coordination.
- TS-330: Manual Assignment creation/override is logged with actor and reason.
- TS-331: Manual Selection Lock extension is logged.

## Boundary Tests

- TS-332: Service Case handoff to Module 04 occurs exactly at "Service Started."
- TS-333: Module 03 does not process payment.
- TS-334: Module 03 does not record care delivery data.
- TS-335: Module 03 does not re-run Matching/Ranking logic.

## Audit Tests

- TS-336: Every commitment, assignment, hold, and substitution records actor, role, timestamp, and reason.
