# ADR Index

## ADR-025-001 — Platform Kernel as Non-Business Module
Decision: Module 25 owns shared contracts and architecture governance only, not business workflows.

## ADR-025-002 — One-Way Kernel Dependency
Decision: All modules may depend on Module 25; Module 25 depends on none.

## ADR-025-003 — CES and CCS Envelopes as Mandatory Contracts
Decision: Events and configuration must use standardized envelopes for interoperability.

## ADR-025-004 — Frozen Contract Compatibility
Decision: Frozen contracts cannot be mutated incompatibly; new major versions are required.
