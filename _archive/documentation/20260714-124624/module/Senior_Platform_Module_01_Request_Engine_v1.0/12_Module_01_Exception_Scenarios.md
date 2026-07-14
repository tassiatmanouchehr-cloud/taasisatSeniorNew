# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# Exception Scenarios

## EX-101 — Internet Drops Mid-Creation
The step-by-step draft is saved so the user can resume without losing progress.

## EX-102 — Guest Never Completes Identity
The request stays a draft and is not published until identity is captured at the final step.

## EX-103 — Attachment Too Large
The file is compressed or rejected with a clear size message; request creation is not blocked by heavy media.

## EX-104 — AI Misclassifies a File
The user corrects the type via the confirmation screen; the corrected type is authoritative.

## EX-105 — Insufficient Request at Publish
Publish is blocked and the missing fields are listed to the user.

## EX-106 — No Eligible Providers
Request is created but has no recipients; support is alerted and can intervene.

## EX-107 — Large Eligible Pool
System notifies only a bounded most-relevant subset instead of all providers.

## EX-108 — Owner Edits After Provider Selected
Selected provider is notified first and must re-confirm the changed request.

## EX-109 — Owner Edits While Applications Pending
Applied providers in the queue are notified of the change.

## EX-110 — Owner Changes Address With Applicants Waiting
Same as EX-108/EX-109 depending on whether a provider is already selected.

## EX-111 — Owner Removes One Need of a Multi-Need Request
Only that need is removed; the rest of the request continues.

## EX-112 — Owner Deletes Before Acceptance
Deletion allowed; no separate notification to applicants; recorded in customer history.

## EX-113 — Family Does Not Select Within 24h
Reminder sent; then phone call; then auto-delete with retention in history.

## EX-114 — Provider Selected but Inactive
~1h pre-appointment reminder to provider; at appointment time customer is asked whether the provider arrived.

## EX-115 — Provider Ill Mid-Contract
Company proposes a replacement, platform assists, customer is informed.

## EX-116 — Single Session Cancellation
Only that session is cancelled; the contract continues.

## EX-117 — Repeated Provider Cancellations
Provider is penalized per policy.

## EX-118 — Repeated Customer Cancellations After Selection
Customer is penalized per policy.

## EX-119 — Phone Number Shared in Chat
Protection signal raised (PHONE_IN_CHAT); support reviews.

## EX-120 — Phone Number Hidden in Photo or PDF
Protection signal raised (PHONE_IN_IMAGE / PHONE_IN_PDF); support reviews.

## EX-121 — Cancel-After-Arrival to Avoid Commission
Guarded: provider arriving and asking the customer to cancel is flagged as abuse.

## EX-122 — External Price Agreement
Protection signal raised (EXTERNAL_PRICE); support reviews.

## EX-123 — Duplicate Requests for the Same Service Recipient
Owner is warned; requests are kept distinct but linked in history.
