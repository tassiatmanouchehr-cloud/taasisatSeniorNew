# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


# UI Screens

## Customer / Family Screens

### 1. Matching Waiting Screen
Shows that providers are being notified.

Elements:

- request summary
- service needs
- estimated waiting message
- status updates

### 2. Candidate Comparison Screen
Groups candidates by:

- package options
- each service need
- accepted candidates

Card fields:

- photo/logo
- name
- provider type
- company name if relevant
- rating
- review count
- relevant services
- price/range
- start time
- coverage full/partial
- badges
- warnings
- view profile
- select

### 3. Provider Profile Screen
Must answer: “Would I trust this person/company with my parent?”

Sections:

- identity verified badges
- service-specific qualifications
- topic-based experience
- completed activity history
- reviews
- response rate
- cancellation rate
- price
- company support if applicable

### 4. Selection Confirmation Screen
Confirms selected candidate and states next step belongs to reservation/contract/payment.

## Provider Screens

### 5. Matching Invitation Screen
Shows request summary and actions:

- Accept
- Reject

No negotiation option in MVP.

### 6. Accepted Invitation State
Shows that provider is visible to customer/family and may withdraw before selection.

## Admin Screens

### 7. Match Round Detail
Shows:

- request
- service needs
- eligible count
- sent invitations
- accepted/rejected/withdrawn
- ranking
- notification status
- expiry status

### 8. Manual Intervention Panel
Actions:

- rerank
- restart matching
- reopen expired matching
- suggest candidate
- invite provider directly

### 9. Settings Panel
Controls:

- ranking weights
- distribution strategy
- notification channels
- reminder time
- expiry time
- company bonus

### 10. Audit Log Screen
Shows all system/manual decisions and reasons.
