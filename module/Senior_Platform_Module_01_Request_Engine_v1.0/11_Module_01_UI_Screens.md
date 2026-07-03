# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# UI Screens

## Customer / Family Screens

### 1. Request Start Screen
Lets the user begin as a guest and choose service-first or service-recipient-first.

Elements:

- "Who is this for?" (service recipient)
- "What service do you need?"
- reassurance that sign-up comes later

### 2. Step-by-Step Request Form
Traditional form presented one step at a time.

Fields:

- service need(s)
- service recipient condition
- city / address
- date / time
- urgency
- free-text description
- attachments (photo / video / document)

### 3. File Confirmation Screen
Shows the AI's guess with a single question.

Elements:

- "This looks like a doctor's prescription — is that correct?"
- ✅ Yes
- ✏️ Correct it

### 4. Identity / Final Step Screen
Captured only at the end.

Elements:

- mobile number
- verification code
- personal info
- final submit

### 5. Request Status & Timeline Screen
Shows the family a plain-language timeline.

Example entries:

- request created
- N providers applied
- provider selected
- service done
- rating recorded

### 6. Edit Request Screen
Lets the owner change details, with clear warnings about re-confirmation or re-notification.

### 7. Contract / Sessions Screen
For recurring needs: shows the contract and its sessions, with per-session cancel.

## Provider Screens

### 8. New Requests Screen
Shows counts by city.

Example:

- "7 new requests in Shiraz"

### 9. Request Detail Screen
Shows a request the provider is eligible to see, with Apply / Withdraw.

## Admin Screens

### 10. Request Detail (Admin)
Shows status, service needs, applications, timeline, and events.

### 11. Request Settings Panel
Controls reminder time, auto-delete policy, publishing breadth, attachment limits, cancellation windows.

### 12. Protection Signals Panel
Lists detected bypass attempts with review / action controls.

### 13. Customer History Screen
Shows a customer's created, edited, and deleted requests.
