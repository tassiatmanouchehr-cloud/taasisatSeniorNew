# Module Boundary Map

## Boundary Types
- System Kernel Boundary: Module 25 only.
- Business Capability Boundary: Modules 01–11.
- Platform Capability Boundary: Modules 12–24.
- Adapter Boundary: provider-specific implementations.
- Experience Boundary: UI and channel surfaces.

## Ownership Rule
Each aggregate has exactly one owning module. Other modules may reference it only by canonical identifier and public contract.

## Read Model Rule
Cross-module read models are projections, not ownership transfers. A projection must identify its source event, source module, projection version, freshness, and rebuild policy.

## Write Rule
A module may not mutate another module's owned aggregate. It must request the change via command contract, API contract, or event-driven workflow.
