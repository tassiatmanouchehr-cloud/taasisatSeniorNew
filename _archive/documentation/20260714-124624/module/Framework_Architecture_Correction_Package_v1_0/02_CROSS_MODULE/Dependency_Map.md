# Corrected Cross-Module Dependency Map v1.0

## Foundation Dependencies

- Module 08 Identity, Roles, Profiles & Access Engine is a foundation dependency for Modules 01–07.
- CES and CCS are foundation standards for all modules.
- Module 07 Communication Orchestration Engine consumes CES events from all modules and handles delivery.

## Module Ownership

| Module | Owns | Must Not Own |
|---|---|---|
| 01 Request | Service request intake, draft, submission, approval readiness | Identity, provider ranking, payment, communication delivery |
| 02 Matching | Candidate discovery, ranking, eligibility, matching runs | Assignment finalization, communications, payments |
| 03 Booking/Assignment | Booking confirmation, assignment, activation | Execution records, payment, communication delivery |
| 04 Execution | Service session execution, start, progress, completion, evidence | Financial settlement, trust sanctions, direct communications |
| 05 Financial | Wallet, ledger, invoice, payment, settlement, refund/adjustment | Identity verification, communication delivery |
| 06 Trust/Governance | Reviews, complaints, disputes, risk, enforcement recommendations | Identity source of truth, access engine implementation |
| 07 Communication | Message orchestration, templates, channels, preferences, delivery logs | Business decisions, identity ownership |
| 08 Identity/Access | User, account, actor, role, permission, profile, organization membership, verification, access decision | Business workflow ownership |

## Forbidden Dependencies

- A lower business module must not send communications directly.
- A business module must not duplicate access decisions locally.
- Financial state must not drive identity state directly; it emits events consumed by policy engines.
- Trust enforcement must be executed through access policies rather than hidden local flags.
