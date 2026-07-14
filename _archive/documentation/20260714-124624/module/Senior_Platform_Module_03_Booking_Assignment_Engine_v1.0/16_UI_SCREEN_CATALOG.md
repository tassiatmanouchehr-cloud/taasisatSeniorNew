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

# 16 — UI Screen Catalog

## Design Decision: No Redundant Summary/Confirmation Screen

During Discovery it was explicitly decided that both the customer and the provider can already see the relevant booking information in their own panel, so a separate one-time "confirm this summary" screen is **not** built in MVP (scenario 1 decision, FR-307). The dashboards below carry that information live instead.

## Customer / Family Screens

### 1. Customer Dashboard
Elements (per Discovery scenario answers):

- Next service (date/time, provider name, company if any)
- Provider en-route status
- Last message
- Next session (for recurring contracts)

### 2. Service Case Detail Screen
Elements:

- Provider / company info
- Address, agreed time
- Terms (price/range, cancellation rules)
- Live status (confirming / confirmed / coordinating / ready / started)
- Withdraw action (where allowed)

### 3. Arrival Check Prompt
Shown at appointment time:

- "Did the provider arrive?"
- "Did they call about a delay?"

## Provider Screens

### 4. Provider Dashboard
Elements:

- Today's service
- Start time
- Route
- Messages

### 5. Commitment Request Screen
Elements:

- Request/service-need summary
- Accept / Reject actions
- Commitment window countdown

### 6. En-Route / Start Service Screen
Elements:

- "On the way" button
- "Start Service" button (triggers Module 03 → Module 04 handoff)

## Company Screens

### 7. Company Dashboard
Elements:

- Today's dispatches
- Forces en route
- Problem cases

### 8. Provider Assignment Screen
Elements:

- Pending company-level commitments
- Assign/substitute provider action
- Reason field for substitution (BR-330)

## Admin (Platform Owner) Screens

### 9. Platform Owner Dashboard
Elements:

- Crises
- Delays
- No-shows
- Replacements

### 10. Service Case Admin Detail
Elements:

- Full Assignment/Session state
- Manual hold controls
- Manual assignment/override controls
- Audit trail

### 11. Booking Settings Panel
Controls:

- Selection lock TTL
- Commitment window
- Escalation threshold
- Hold policy

## Explicitly Deferred UI

- A dedicated "crisis scenario" screen set (for the ~100 legal-sensitive exceptions) is deferred pending legal review — see `00_README.md` → Open Issues.
