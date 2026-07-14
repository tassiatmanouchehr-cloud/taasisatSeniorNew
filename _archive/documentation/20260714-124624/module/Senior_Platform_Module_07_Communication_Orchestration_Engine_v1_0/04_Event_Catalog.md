# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## 1. Purpose

This catalog defines CES Events consumed and emitted by Module 07.

All event names are generic. Reference implementations may map domain-specific events into these generic event names.

## 2. Consumed Event Categories

### Request Events
- RequestCreated
- RequestUpdated
- RequestSubmitted
- RequestApproved
- RequestRejected
- RequestCancelled
- RequestCancellationRequested

### Matching Events
- MatchCreated
- MatchUpdated
- MatchAccepted
- MatchDeclined
- MatchExpired
- MatchRecomputed

### Booking / Assignment Events
- BookingCreated
- BookingConfirmed
- BookingUpdated
- BookingCancelled
- AssignmentCreated
- AssignmentChanged
- AssignmentRemoved
- AssignmentAccepted
- AssignmentRejected
- AssignmentExpired

### Service Execution Events
- ServiceScheduled
- ServiceStarted
- ServicePaused
- ServiceResumed
- ServiceCompleted
- ServiceCompletionConfirmed
- ServiceCompletionDisputed
- ServiceNoShowReported

### Financial Events
- InvoiceCreated
- InvoiceUpdated
- InvoiceSent
- InvoicePaid
- InvoicePaymentFailed
- InvoiceCancelled
- RefundRequested
- RefundApproved
- WalletCredited
- WalletDebited
- SettlementCreated
- SettlementCompleted

### Trust, Quality and Governance Events
- ReviewSubmitted
- RatingSubmitted
- ComplaintCreated
- DisputeOpened
- DisputeUpdated
- DisputeResolved
- TrustFlagRaised
- AccountRestricted
- AccountRestored
- AppealSubmitted
- AppealApproved
- AppealRejected

### Identity and Access Events
- UserRegistered
- UserVerified
- LoginSucceeded
- LoginFailed
- PasswordChanged
- MFAEnabled
- MFADisabled
- RoleChanged
- PermissionChanged

### Organization Events
- OrganizationCreated
- OrganizationApproved
- OrganizationSuspended
- OrganizationRestored
- OrganizationMemberAdded
- OrganizationMemberRemoved

### Platform Events
- MaintenanceScheduled
- MaintenanceStarted
- MaintenanceCompleted
- PolicyUpdated
- TermsUpdated
- SecurityNoticeCreated

## 3. Module 07 Emitted Events

- CommunicationEventReceived
- CommunicationRuleMatched
- CommunicationRuleSkipped
- CommunicationSessionCreated
- CommunicationSessionCompleted
- CommunicationSessionFailed
- CommunicationRecipientResolved
- CommunicationRecipientResolutionFailed
- CommunicationChannelSelected
- CommunicationChannelSkipped
- CommunicationTemplateRendered
- CommunicationTemplateRenderFailed
- CommunicationJobCreated
- CommunicationJobQueued
- CommunicationJobSent
- CommunicationJobDelivered
- CommunicationJobFailed
- CommunicationJobRetryScheduled
- CommunicationJobPermanentlyFailed
- CommunicationRead
- CommunicationOpened
- CommunicationClicked
- CommunicationAcknowledged
- CommunicationEscalated
- CommunicationFallbackTriggered
- CommunicationAuditRecorded
- InboxItemCreated
- InboxItemRead
- ReminderScheduled
- ReminderTriggered
- AnnouncementPublished
- CampaignStarted
- CampaignCompleted

## 4. Required Event Fields

Every consumed event must provide:

| Field | Description |
|---|---|
| event_id | Globally unique event ID |
| event_type | CES event type |
| source_module | Producer module |
| tenant_id | Tenant boundary |
| aggregate_type | Related business entity type |
| aggregate_id | Related business entity ID |
| actor_id | User/system actor |
| occurred_at | Event occurrence time |
| correlation_id | Cross-event tracing |
| trace_id | Observability trace |
| payload | Approved event data |

## 5. Communication-Relevant Payload Recommendations

Events should include enough data for communication without causing excessive coupling:

- public display names
- safe entity numbers
- status names
- amounts and currency when relevant
- dates and times
- action URLs or entity references
- recipient reference IDs, not raw private data unless explicitly approved

## 6. Event-to-Intent Defaults

| Event Category | Default Intent | Default Priority |
|---|---|---|
| Financial success/failure | financial | high |
| Security | security | critical |
| Cancellation/dispute | trust_and_safety | high |
| Booking/assignment | operational | high |
| Reminders | reminder | normal |
| Marketing | marketing | low |
| Legal/policy | legal | high |
| General updates | informational | normal |

## 7. Idempotency

Module 07 must treat event_id as the primary idempotency boundary and derive communication job idempotency using:

```text
event_id + rule_id + recipient_id + channel_type + template_version_id
```

## 8. Event Catalog Governance

No hidden event consumption is allowed. If Module 07 consumes an event, it must be listed here or in an approved extension catalog.
