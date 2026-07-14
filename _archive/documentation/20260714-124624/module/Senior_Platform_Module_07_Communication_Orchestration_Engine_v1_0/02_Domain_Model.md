# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## 1. Domain Overview

The Communication Domain transforms CES Events into communication sessions, delivery jobs, attempts, inbox messages, conversations, reminders, campaigns, announcements and immutable audit evidence.

## 2. Aggregate Roots

- CommunicationEventMirror
- CommunicationSession
- CommunicationRule
- CommunicationPolicy
- CommunicationTemplate
- CommunicationProvider
- CommunicationDeliveryJob
- CommunicationInboxItem
- CommunicationConversation
- CommunicationReminder
- CommunicationAnnouncement
- CommunicationCampaign
- CommunicationPreferenceProfile
- CommunicationAuditLog

## 3. CommunicationEventMirror

A local immutable representation of a consumed CES Event.

Fields:
- event_id
- event_type
- source_module
- aggregate_type
- aggregate_id
- actor_id
- tenant_id
- occurred_at
- correlation_id
- trace_id
- payload_hash
- payload_snapshot
- received_at

Rules:
- immutable
- one event may create zero or many sessions
- duplicate event IDs must not create duplicate communication outputs

## 4. CommunicationSession

Root orchestration object created for a consumed event and matched rule set.

Fields:
- session_id
- event_id
- tenant_id
- status
- intent
- priority
- matched_rule_count
- job_count
- completed_job_count
- failed_job_count
- created_at
- completed_at
- expires_at

States:
- created
- processing
- waiting
- completed
- partially_completed
- failed
- cancelled
- expired

## 5. CommunicationRule

Defines what communication should be generated for an event.

Fields:
- rule_id
- code
- name
- description
- enabled
- event_type
- tenant_scope
- audience_policy
- channel_policy
- template_policy
- condition_expression
- intent
- priority
- retry_policy_id
- fallback_policy_id
- escalation_policy_id
- expiration_policy_id
- audit_policy_id
- version
- status

Lifecycle:
- draft
- active
- disabled
- deprecated
- archived

## 6. CommunicationPolicy

Groups rules and governs override behavior.

Fields:
- policy_id
- scope_type
- scope_id
- enabled
- default_channels
- mandatory_channels
- blocked_channels
- preference_mode
- quiet_hours_policy
- consent_policy
- emergency_override_policy

## 7. CommunicationAudience

Logical recipient group.

Allowed generic types:
- customer
- provider
- organization
- organization_admin
- platform_owner
- platform_operator
- support_agent
- finance_operator
- trust_operator
- admin
- external_contact
- custom_role

## 8. CommunicationRecipient

Concrete recipient resolved from an audience.

Fields:
- recipient_id
- audience_type
- user_id
- organization_id
- external_contact_id
- display_name
- locale
- timezone
- status
- channel_capabilities
- consent_state

## 9. CommunicationChannel

Transport surface.

Channel types:
- sms
- email
- push
- in_app
- inbox
- dashboard
- web_notification
- mobile_notification
- chat
- announcement
- webhook
- voice
- future

Fields:
- channel_type
- enabled
- supports_delivery_receipt
- supports_read_receipt
- supports_click_tracking
- supports_reply
- supports_attachments
- cost_class
- latency_class

## 10. CommunicationTemplate

Template metadata.

Fields:
- template_id
- code
- event_type
- audience_type
- channel_type
- locale
- status
- current_version_id
- tenant_scope

## 11. CommunicationTemplateVersion

Immutable approved message definition.

Fields:
- version_id
- template_id
- version_number
- subject
- body
- variables_schema
- allowed_resolvers
- content_hash
- status
- approved_by
- approved_at

Template version lifecycle:
- draft
- review
- approved
- deprecated
- archived

Approved versions are immutable.

## 12. CommunicationDeliveryJob

One recipient-channel delivery unit.

Fields:
- job_id
- session_id
- rule_id
- recipient_id
- channel_type
- provider_id
- template_version_id
- status
- priority
- attempt_count
- max_attempts
- next_retry_at
- expires_at
- idempotency_key
- last_error_code
- last_error_message
- created_at
- sent_at
- delivered_at

## 13. CommunicationDeliveryAttempt

One provider interaction.

Fields:
- attempt_id
- job_id
- provider_id
- attempt_number
- started_at
- finished_at
- result
- provider_message_id
- provider_status_code
- provider_response_hash
- latency_ms
- error_code

## 14. CommunicationInboxItem

Persistent in-platform message.

Fields:
- inbox_item_id
- recipient_id
- tenant_id
- title
- body
- category
- priority
- action_url
- entity_type
- entity_id
- status
- pinned
- archived_at
- read_at
- expires_at

## 15. CommunicationConversation

Thread for chat/support/system communication.

Fields:
- conversation_id
- tenant_id
- conversation_type
- status
- participants
- entity_reference
- last_message_at
- created_at

Conversation types:
- private
- support
- system
- group
- marketplace_transaction

## 16. CommunicationMessage

Message inside a conversation.

Fields:
- message_id
- conversation_id
- sender_type
- sender_id
- body
- attachments
- visibility
- status
- created_at
- edited_at
- deleted_at

## 17. CommunicationReminder

Scheduled communication intent.

Fields:
- reminder_id
- rule_id
- target_entity_type
- target_entity_id
- schedule_type
- schedule_expression
- next_run_at
- max_occurrences
- status

## 18. CommunicationAnnouncement

Platform or tenant announcement.

Fields:
- announcement_id
- scope_type
- scope_id
- audience_segment
- title
- body
- channels
- status
- scheduled_at
- published_at
- expires_at

## 19. CommunicationCampaign

Controlled bulk communication.

Fields:
- campaign_id
- tenant_id
- campaign_type
- audience_segment
- channels
- templates
- schedule
- consent_policy
- rate_limit_policy
- status
- statistics

## 20. CommunicationPreferenceProfile

User and role communication choices.

Fields:
- preference_id
- user_id
- tenant_id
- event_type
- intent
- channel_type
- enabled
- quiet_hours
- frequency
- updated_at

## 21. CommunicationAuditLog

Immutable evidence record.

Fields:
- audit_id
- event_id
- session_id
- rule_id
- job_id
- recipient_id
- channel_type
- provider_id
- template_version_id
- decision
- reason
- status
- metadata_hash
- created_at

## 22. Value Objects

- CommunicationIntent
- CommunicationPriority
- AudienceType
- ChannelType
- RecipientAddress
- ContactCapability
- ConsentState
- QuietHours
- RetryPolicy
- FallbackPolicy
- EscalationPolicy
- ExpirationPolicy
- TemplateVariableSchema
- ProviderCapability
- DeliveryStatus
- ReadStatus
- EntityReference
- CorrelationReference

## 23. Domain Services

- CommunicationPolicyService
- CommunicationRuleMatcher
- AudienceResolverService
- ChannelResolverService
- PreferenceResolverService
- TemplateResolverService
- TemplateRenderingService
- ProviderSelectionService
- DeliveryJobService
- DeliveryAttemptService
- RetryService
- FallbackService
- EscalationService
- InboxService
- ConversationService
- ReminderSchedulerService
- CampaignExecutionService
- AnnouncementService
- CommunicationAuditService
- CommunicationTimelineService

## 24. Invariants

- Every communication must originate from a CES Event or an explicitly scheduled system communication registered by Module 07.
- Every delivery job belongs to one communication session.
- Every communication session belongs to one event mirror.
- Every attempt belongs to one job.
- Approved templates are immutable.
- Audit records are immutable.
- Provider credentials are never exposed to business modules.
- Tenant isolation is mandatory.
- Duplicate event processing must not duplicate delivery.
- Critical communication cannot be silently discarded.
