# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


# Test Scenarios

## Eligibility Tests

- TS-201: Unapproved provider cannot enter Matching.
- TS-202: Incomplete profile cannot enter Matching.
- TS-203: Suspended provider is hidden from public profile and Matching.
- TS-204: Company provider blocked when company is suspended.
- TS-205: Company active but company provider suspended is blocked.
- TS-206: Provider eligible for care but not injection due to missing document.
- TS-207: Expired injection document blocks only injection service.
- TS-208: Provider service deactivated blocks only that service.
- TS-209: Residence outside area does not matter if service coverage includes customer location.
- TS-210: Customer location outside service coverage blocks provider.

## Availability Tests

- TS-211: Provider with free slot enters Matching.
- TS-212: Provider with conflicting order is blocked.
- TS-213: Partial recurring availability is shown with low fitness.
- TS-214: Company availability blocked prevents company providers from entering.

## Matching Tests

- TS-215: Single service request generates candidates for that need.
- TS-216: Multi-need request generates per-need candidates.
- TS-217: Independent provider covering multiple needs generates package candidate.
- TS-218: Company covering all needs generates company package candidate.
- TS-219: Company lacking provider for service is not eligible for that service.
- TS-220: Broadcast sends invitations to all eligible providers.

## Candidate Response Tests

- TS-221: Candidate can accept.
- TS-222: Candidate can reject.
- TS-223: Accepted candidate appears to customer.
- TS-224: Rejected candidate does not appear to customer.
- TS-225: Candidate can withdraw before selection.
- TS-226: Candidate cannot accept after expiry.

## Ranking Tests

- TS-227: Full coverage ranks above partial coverage by default.
- TS-228: Ranking weights are configurable.
- TS-229: Company bonus is small and configurable.
- TS-230: Quality can overcome partial coverage if weights allow.
- TS-231: Ranking reasons are stored.

## Presentation Tests

- TS-232: Independent provider card shows required fields.
- TS-233: Company provider card shows provider and company information.
- TS-234: Company package card shows covered needs.
- TS-235: Price/range appears on card.
- TS-236: Maximum badge count is enforced.
- TS-237: Verified documents show as verified labels but original files remain private.

## Selection Tests

- TS-238: Customer can select one candidate.
- TS-239: Duplicate tab selection causes first lock to win.
- TS-240: Different family users selecting same need causes first lock to win.
- TS-241: Candidate unavailable during selection returns error.
- TS-242: Selection creates Module 03 handoff state but not final contract.

## Notification Tests

- TS-243: Push sent when enabled.
- TS-244: SMS sent for urgent request when enabled.
- TS-245: Email not sent when disabled.
- TS-246: SMS fallback after unopened push follows settings.
- TS-247: Customer notified when candidates accept.
- TS-248: Customer notified when selected/visible candidate withdraws.

## Expiration Tests

- TS-249: 24h reminder is configurable.
- TS-250: 48h expiry is configurable.
- TS-251: Expired matching blocks new acceptance.
- TS-252: Platform Owner can reopen expired matching.
- TS-253: Reopen action is audited.

## Manual Intervention Tests

- TS-254: Support with permission can rerank.
- TS-255: Support without permission cannot rerank.
- TS-256: Admin suggested candidate is marked transparently.
- TS-257: Hidden ranking manipulation is blocked.
- TS-258: All manual actions create audit logs.

## Regression Tests

- TS-259: Module 02 does not create requests.
- TS-260: Module 02 does not process payment.
- TS-261: Module 02 does not create legal contract.
- TS-262: Module 02 respects Module 01 service needs.
