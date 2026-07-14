# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# API Contracts

> Contracts are conceptual. Final endpoint naming depends on implementation stack.

## Customer / Family APIs

### POST /requests/draft
Starts a request as guest or logged-in user. Returns a draft id.

### PATCH /requests/{request_id}
Updates request fields, service needs, timing, or address (see edit rules).

### POST /requests/{request_id}/attachments
Uploads a compressed attachment. Returns AI-suggested type.

### POST /requests/{request_id}/attachments/{attachment_id}/confirm-type
Confirms or corrects the file type.

Body:
- confirmed_type

### POST /requests/{request_id}/identify
Captures mobile number, verification code, and personal info at the final step.

### POST /requests/{request_id}/publish
Validates and publishes the request.

Errors:
- REQUEST_INSUFFICIENT
- REQUEST_NOT_PUBLISHABLE

### DELETE /requests/{request_id}
Deletes a request (allowed while no provider accepted).

Errors:
- PROVIDER_ALREADY_ACCEPTED

### POST /requests/{request_id}/needs/{need_id}/remove
Removes a single service need from a multi-need request.

### GET /requests/{request_id}/timeline
Returns the role-filtered timeline.

## Provider APIs

### GET /provider/requests/new
Returns count and summary of new eligible requests (e.g. "7 in Shiraz").

### GET /provider/requests/{request_id}
Returns a request the provider is eligible to see.

### POST /provider/requests/{request_id}/apply
Declares willingness (اعلام آمادگی).

### POST /provider/requests/{request_id}/withdraw
Withdraws a prior application before selection.

## Contract APIs

### POST /contracts
Creates a recurring contract with sessions from a recurring request.

### POST /contracts/{contract_id}/sessions/{session_id}/cancel
Cancels a single session.

### POST /contracts/{contract_id}/sessions/{session_id}/propose-replacement
Company proposes a replacement provider for a session.

## Admin APIs

### PATCH /admin/requests/settings
Updates timeouts, reminder hours, and publishing breadth.

### GET /admin/requests/{request_id}/audit
Returns full request history and events.

### GET /admin/protection/signals
Lists protection signals for review.

### POST /admin/protection/signals/{signal_id}/review
Actions or dismisses a protection signal.

## Internal Services

### ValidationService.validate(request)
Returns sufficiency plus missing reasons.

### PublishingService.publish(request)
Selects the bounded eligible recipient set and emits events.

### EventBus.emit(event)
Emits request domain events for downstream modules.

### ProtectionService.scan(content)
Scans chat/photo/PDF/price content for bypass attempts.

### TimelineService.record(request, entry)
Records a role-filtered timeline entry.
