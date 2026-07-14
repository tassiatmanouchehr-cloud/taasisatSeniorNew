# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## Adding a New Channel
Add channel type, provider adapter, templates, configuration keys, delivery status mapping and tests. No business module changes are allowed.

## Adding WhatsApp
Add WhatsApp channel/provider adapter, template renderer constraints, consent rules and provider credentials. Do not alter core aggregates.

## Adding AI Voice Call
Add voice provider adapter, voice template type, call status mapping, recording/privacy policy and escalation rules.

## Adding a New Event
Register CES Event, define safe payload schema, add communication rules and templates. Do not add direct sending code to source module.

## Adding Tenant Customization
Use CCS overrides, tenant templates and tenant provider configuration within platform constraints.
