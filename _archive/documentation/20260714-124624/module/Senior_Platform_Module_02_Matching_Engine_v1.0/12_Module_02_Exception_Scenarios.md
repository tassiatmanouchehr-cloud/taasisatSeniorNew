# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


# Exception Scenarios

## EX-201 — No Eligible Providers
System marks matching failed, notifies customer/family and support, and enables manual intervention.

## EX-202 — No Candidate Accepts
Same as matching failed; support can restart or manually intervene.

## EX-203 — Only One Candidate Accepts
Candidate is shown immediately.

## EX-204 — Candidate Withdraws Before Selection
Remove candidate from list and notify customer if relevant.

## EX-205 — Candidate Withdraws During Customer View
Show message: provider is no longer available.

## EX-206 — Candidate Withdraws After Selection
Handoff to replacement/cancellation logic in Module 03, with support alert.

## EX-207 — Two Browser Tabs Select Different Candidates
First successful selection lock wins. Second receives `ALREADY_SELECTED`.

## EX-208 — Two Family Members Select Different Candidates
First successful selection lock wins. Other user is informed that selection already exists.

## EX-209 — Matching Expired
Providers cannot accept. Customer sees expired state. Platform Owner can reopen.

## EX-210 — Late Provider Acceptance
System rejects with `MATCHING_EXPIRED`.

## EX-211 — Provider Becomes Suspended Mid-Matching
Remove from candidate list and notify if selected/visible.

## EX-212 — Company Suspended Mid-Matching
Remove company and company providers from candidate list.

## EX-213 — Document Expires Mid-Matching
If required for the requested service, candidate becomes not eligible and is removed/warned depending on timing.

## EX-214 — Ranking Service Fails
Use fallback deterministic ordering and alert support/engineering.

## EX-215 — Notification Failure
Try configured fallback channel. Log failure.

## EX-216 — Customer Does Not Select by Reminder Time
Notify customer/family.

## EX-217 — Customer Does Not Select by Expiry Time
Expire matching and notify customer/family.

## EX-218 — Admin Suggests Candidate
Candidate is marked transparently as admin/operator suggested and logged.

## EX-219 — Hidden Ranking Manipulation Attempt
System must block or log unauthorized ranking manipulation.

## EX-220 — Partial Coverage Candidate
Show with lower fitness and explicit warning.
