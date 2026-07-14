# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


# API Contracts

> Contracts are conceptual. Final endpoint naming depends on implementation stack.

## Customer APIs

### GET /requests/{request_id}/matches
Returns accepted candidates grouped by service need and packages.

Response includes:

- candidate id
- candidate type
- summary card data
- ranking position
- badges
- warnings
- profile link

### GET /matches/candidates/{candidate_id}/profile
Returns full provider/company profile.

### POST /matches/candidates/{candidate_id}/select
Records customer selection lock.

Errors:

- CANDIDATE_NOT_AVAILABLE
- MATCHING_EXPIRED
- ALREADY_SELECTED
- REQUEST_NOT_SELECTABLE

## Provider APIs

### GET /provider/matching/invitations
Returns pending matching invitations.

### POST /provider/matching/invitations/{candidate_id}/accept
Accepts invitation.

### POST /provider/matching/invitations/{candidate_id}/reject
Rejects invitation.

### POST /provider/matching/invitations/{candidate_id}/withdraw
Withdraws prior acceptance before customer selection.

## Admin APIs

### POST /admin/matching/{match_round_id}/reopen
Reopens expired matching.

### POST /admin/matching/{match_round_id}/rerank
Recalculates ranking.

### POST /admin/matching/{match_round_id}/restart
Starts matching again.

### POST /admin/matching/{match_round_id}/suggest-candidate
Adds transparent admin/operator suggestion.

### PATCH /admin/matching/settings/ranking-weights
Updates ranking weights.

### PATCH /admin/matching/settings/notifications
Updates notification channel settings.

### GET /admin/matching/{match_round_id}/audit-log
Returns manual actions and system decisions.

## Internal Services

### EligibilityService.evaluate(request_service_need, provider)
Returns explainable eligibility result.

### MatchingService.generate_candidates(request)
Builds candidate set.

### DistributionService.distribute(match_round)
Sends invitations using configured strategy.

### RankingService.rank(candidates)
Returns ordered candidate list with scoring reasons.

### NotificationService.notify(event_type, recipient)
Sends configured notifications.
