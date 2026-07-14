# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## 1. Upstream Dependencies
CES v1.0, CCS v1.0, identity/user model, tenant model, role/permission model, Modules 01–06 event catalogs.

## 2. Downstream Dependencies
External SMS/email/push/voice providers, mobile apps, web app, admin dashboards, support console, observability stack.

## 3. Forbidden Dependencies
Business modules must not depend on provider adapters. Provider adapters must not depend on business modules. Templates must not query arbitrary business tables.

## 4. Dependency Direction
Business Module → CES Event → Module 07 → Provider/Internal Surface.

## 5. Reference Implementation Boundary
Generic Service Marketplace-care mappings are outside core Module 07.
