# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# Test Scenarios

## Request Start Tests

- TS-101: Guest can start a request without full registration.
- TS-102: Identity is required before final submission.
- TS-103: Service-first entry path produces a valid request.
- TS-104: Service-recipient-first entry path produces a valid request.
- TS-105: Draft is preserved when the connection drops.

## Information Collection Tests

- TS-106: Form accepts free-text description.
- TS-107: Photo attachment is accepted and compressed.
- TS-108: Video attachment is accepted and size-limited.
- TS-109: Oversized attachment is rejected with a clear message.
- TS-110: AI suggests a file type on upload.
- TS-111: User can confirm the suggested file type.
- TS-112: User can correct the file type and correction wins.

## Multi-Need Tests

- TS-113: A request can contain multiple service needs.
- TS-114: Each need is stored separately.
- TS-115: Removing one need keeps the rest of the request active.

## Validation Tests

- TS-116: Insufficient request cannot be published.
- TS-117: Missing fields are reported to the user.
- TS-118: Sufficient request publishes successfully.

## Publishing Tests

- TS-119: Request is shown only to eligible providers.
- TS-120: Large pool triggers bounded subset notification, not fan-out.
- TS-121: Provider sees new-request count by city.
- TS-122: View-without-apply behaviour is recorded as signal data.

## Life Cycle Tests

- TS-123: Request follows Draft → Published → … → Completed.
- TS-124: Provider application moves request toward selection.
- TS-125: Selection sets PROVIDER_SELECTED then CONFIRMED.

## Editing Tests

- TS-126: Editing after selection notifies and re-confirms the provider.
- TS-127: Editing while applications pending notifies applied providers.
- TS-128: Address change follows the correct edit rule for current status.

## Deletion & Timeout Tests

- TS-129: Owner can delete before any provider accepts.
- TS-130: Deletion is recorded in customer history.
- TS-131: No separate notification is sent to other applicants on deletion.
- TS-132: 24h no-selection triggers a reminder.
- TS-133: Continued silence triggers a phone follow-up.
- TS-134: Final silence auto-deletes with retention.

## Follow-Up Tests

- TS-135: Provider gets a reminder ~1h before appointment.
- TS-136: Customer is asked at appointment time whether the provider arrived.

## Contract Tests

- TS-137: Recurring request creates a contract with sessions.
- TS-138: A single session can be cancelled without cancelling the contract.
- TS-139: Provider unavailability triggers replacement proposal and customer notice.

## Cancellation & Penalty Tests

- TS-140: Family, provider, company, and platform can each cancel per rules.
- TS-141: Repeated provider cancellations trigger a penalty.
- TS-142: Repeated customer cancellations after selection trigger a penalty.

## Protection Tests

- TS-143: Phone number in chat raises a protection signal.
- TS-144: Phone number in a photo raises a protection signal.
- TS-145: Phone number in a PDF raises a protection signal.
- TS-146: External price agreement raises a protection signal.
- TS-147: Cancel-after-arrival abuse is flagged.

## Timeline & Event Tests

- TS-148: Every status change writes a timeline entry.
- TS-149: Timeline entries are role-filtered.
- TS-150: Request actions emit events for downstream modules.

## Regression Tests

- TS-151: Module 01 does not rank providers.
- TS-152: Module 01 does not process payment.
- TS-153: Module 01 does not create a final legal settlement.
- TS-154: A published request hands a clean structure to Module 02.
