# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## 1. Purpose
The Template Engine renders channel-specific content safely and consistently.

## 2. Template Types
sms, email, push, in_app, inbox, dashboard, chat, announcement, webhook, voice.

## 3. Template Lifecycle
Draft → Review → Approved → Deprecated → Archived.

Approved template versions are immutable.

## 4. Rendering Rules
Templates may use only approved variables from event payloads or approved read-only data resolvers.

## 5. Validation
Validation checks:
- missing variables
- unsupported variables
- channel length limits
- unsafe markup
- locale coverage
- subject/body requirements
- action URL safety

## 6. Localization
Templates are selected by locale fallback chain:
recipient locale → tenant default locale → framework default locale.

## 7. Example
Event: InvoicePaid
Customer SMS: "Dear customer, your invoice #{invoice_number} was paid successfully. Thank you."
Provider Push: "Customer {customer_display_name} paid invoice #{invoice_number}."

## 8. Security
Sensitive variables must be masked where required. Rendered payload hashes may be stored in audit; raw sensitive content must not be logged casually.
