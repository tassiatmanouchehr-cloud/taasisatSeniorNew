# Build Architecture Records

## Purpose

This folder contains architecture records created during the **implementation/build phase** of the Enterprise Service Marketplace Platform.

These are living documents that capture implementation-time architecture decisions, commit plans, and technical resolutions made while translating the frozen specifications into production code.

---

## What This Folder Is

- Architecture Decision Records (ADRs) made during the build process
- Implementation planning documents (sprint plans, commit plans)
- Technical resolution records for ambiguities discovered during coding
- Build-phase design clarifications

## What This Folder Is NOT

- These files **do not replace** the original frozen module specifications
- These files **do not override** the Framework Architecture Correction Package
- These files **do not supersede** Module 25 kernel contracts
- These files are **not the source of truth** for business rules

---

## Precedence Order

If there is a conflict between any documents, the following precedence order applies (highest first):

| Priority | Document | Location |
|----------|----------|----------|
| 1 (highest) | Framework Architecture Correction Package | `module/Framework_Architecture_Correction_Package_v1_0/` |
| 2 | Frozen module specifications (Modules 01-24) | `module/Senior_Platform_Module_*/` |
| 3 | Module 25 kernel contracts | `module/Senior_Platform_Module_25_*/` |
| 4 | Architecture Intake Report | `ARCHITECTURE_INTAKE_REPORT_v1.0.md` |
| 5 | Phase 0.5 Enterprise Domain Model Freeze | `PHASE_0_5_ENTERPRISE_DOMAIN_MODEL_FREEZE.md` |
| 6 | ADR files in this folder | `build_architecture_records/ADR_*.md` |
| 7 (lowest) | Implementation code | `src/` (when created) |

---

## File Index

| File | Description |
|------|-------------|
| `ADR_001_ARCHITECTURE_FREEZE_v1_0.md` | 24 binding architecture decisions frozen before Phase 1 |
| `PHASE_1_SPRINT_1_COMMIT_PLAN_v1_0.md` | 18-commit granular plan for Sprint 1 implementation |

---

## Rules for Adding New Records

1. ADRs are numbered sequentially: `ADR_002_...`, `ADR_003_...`
2. ADR status must be one of: `Proposed`, `Accepted`, `Deprecated`, `Superseded`
3. Every ADR must reference the frozen specification it relates to
4. ADRs may NOT weaken platform security invariants
5. ADRs may NOT override the Correction Package binding rules
6. ADRs may NOT change frozen module boundaries without explicit owner approval
