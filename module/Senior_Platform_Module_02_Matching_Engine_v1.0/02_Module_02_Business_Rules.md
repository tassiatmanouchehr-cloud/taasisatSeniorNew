# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


# Business Rules

## Eligibility Rules

### BR-201 — Platform Approval Required
No independent provider, company provider, or company may enter Matching unless approved by the platform.

### BR-202 — Profile Completeness Required
Providers with incomplete profiles cannot enter Matching.

### BR-203 — Provider Lifecycle
Only `ACTIVE` providers can enter Matching in MVP.

### BR-204 — Suspended Provider Visibility
Suspended providers cannot enter Matching and cannot be publicly viewed by customers/families.

### BR-205 — Hierarchical Company Eligibility
For company providers, company eligibility is checked before provider eligibility.

### BR-206 — Company Suspension
If a company is suspended, all company providers under it are removed from Matching.

### BR-207 — Company Provider Independent Registration
A company provider may register separately as an independent provider if eligible.

### BR-208 — Service-Level Eligibility
Eligibility is evaluated per service, not only per provider profile.

### BR-209 — Service-Level Deactivation
If a provider deactivates one service, only that service is removed from Matching.

### BR-210 — Document Expiry
Expired documents affect only services that require those documents.

### BR-211 — Pre-Expiry Warnings
The system must warn providers before important documents expire.

### BR-212 — Geographic Coverage
Service location must fall inside provider service coverage.

### BR-213 — Residence and Coverage Separation
Provider residence address and service coverage are separate.

### BR-214 — Multiple Coverages
Independent providers may define multiple service coverage areas.

### BR-215 — Company General Coverage
In MVP, a company has one general service coverage.

### BR-216 — Schedule Conflict
Providers with definitive schedule conflict cannot enter Matching for that time.

### BR-217 — Capacity Simplification
Capacity in MVP is treated as availability plus no conflict.

## Matching Rules

### BR-218 — Request May Contain Multiple Needs
A request can contain one or more service needs.

### BR-219 — Match Per Service Need
Matching is run for each service need.

### BR-220 — Package Candidate by Individual
An independent provider may cover multiple needs if eligible.

### BR-221 — Package Candidate by Company
A company may cover multiple needs if eligible.

### BR-222 — Partial Coverage Allowed
Partial coverage can be shown with lower fitness and clear warning.

### BR-223 — Broadcast Distribution in MVP
All eligible providers receive the request in MVP.

### BR-224 — Future Distribution Strategies
Architecture must support broadcast, wave-based, and smart distribution.

## Candidate Response Rules

### BR-225 — Response Actions
Candidates can only Accept or Reject in MVP.

### BR-226 — Acceptance Meaning
Acceptance means willingness to be shown and considered, not final legal commitment.

### BR-227 — Withdrawal Before Selection
Accepted candidates can withdraw before customer selection.

### BR-228 — Expired Request Cannot Be Accepted
After matching expiry, providers cannot accept.

## Ranking Rules

### BR-229 — Rule-Based Ranking in MVP
Ranking is rule-based in version one.

### BR-230 — AI Extension
AI ranking must be pluggable later.

### BR-231 — Primary Ranking Factor
Complete coverage of request needs is the most important ranking factor.

### BR-232 — Configurable Weights
Platform Owner can configure ranking weights.

### BR-233 — Company Bonus
Company affiliation may receive a small configurable operational bonus, not large enough to override real quality.

### BR-234 — Explainable Ranking
Important ranking factors and warnings must be explainable.

## Presentation Rules

### BR-235 — Accepted Candidates Only
Only candidates that accepted the request are shown.

### BR-236 — Summary Card
The customer/family should be able to make about 80% of the decision from the summary card.

### BR-237 — Profile View
Customers can open full profile details before choosing.

### BR-238 — Price Display
Price or price range must be shown.

### BR-239 — Limited Badges
Badges are allowed but must be limited and controlled.

### BR-240 — Trust Profile
Provider profiles must show verified trust information without exposing private documents.

## Notification Rules

### BR-241 — Notification Configurability
Push, SMS, email, in-app, and future channels must be configurable by Platform Owner.

### BR-242 — Push Primary
Push notification is the primary matching channel in MVP.

### BR-243 — SMS Fallback
SMS can be used for important, urgent, or unseen push events depending on settings.

### BR-244 — Customer Accepted Candidate Notice
Customer/family is notified when suitable accepted options are ready.

### BR-245 — Withdrawal Notice
Customer/family is notified when relevant accepted/selected candidate withdraws.

## Expiration Rules

### BR-246 — No Accepted Candidates
If no candidate accepts, matching fails and customer plus support are notified.

### BR-247 — One Candidate Display
If one candidate accepts, show immediately.

### BR-248 — Dynamic Updates
Accepted candidate list updates until customer selection.

### BR-249 — Reminder at 24 Hours
If customer does not select by configured reminder time, notify.

### BR-250 — Expiry at 48 Hours
If no selection occurs by configured expiry time, matching expires.

### BR-251 — Reopen Matching
Platform Owner can reopen expired matching.

## Manual Intervention Rules

### BR-252 — Support Intervention
Platform Owner and authorized support can intervene with different permissions.

### BR-253 — Admin Suggested Candidate
Authorized staff can manually suggest a candidate transparently.

### BR-254 — No Hidden Ranking Manipulation
Staff may not secretly manipulate ranking.

### BR-255 — Audit Log Required
All manual intervention must be logged.

### BR-256 — Final Decision
Final choice remains with customer/family, unless legal or platform constraints block a candidate.

## Selection Boundary Rules

### BR-257 — Selection Lock
When customer selects a candidate, Module 02 records a selection lock / selected candidate.

### BR-258 — No Final Commitment in Module 02
Final reservation, contract, payment, and assignment belong to Module 03.
