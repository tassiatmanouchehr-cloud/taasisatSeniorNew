# Cross-Module Contracts

## 1. Contract posture

Module 09 consumes canonical events and projection-read APIs from Modules 01–08. It does not mutate their canonical entities.

## 2. Module 01 — Request Engine

Consumes:

- request.created;
- request.updated;
- request.lifecycle_changed;
- request.cancelled;
- request.deleted;
- request.visibility_changed.

Requires projection fields:

- request_id;
- tenant_id;
- source_version;
- lifecycle_state;
- service_category_id;
- service_unit_codes;
- request_summary;
- location_area;
- time_window;
- requester_visibility_profile;
- discoverability_state;
- permission_tags.

## 3. Module 02 — Matching Engine

Consumes optional signals:

- matching.score_updated;
- matching.eligibility_changed;
- matching.ranking_signal_updated.

Uses:

- eligibility signal as hard filter when configured;
- score features as ranking signals only.

Module 09 must not make final matching decisions.

## 4. Module 03 — Booking, Assignment & Activation

Consumes:

- booking.created;
- booking.updated;
- assignment.created;
- assignment.changed;
- assignment.removed;
- availability.changed;
- activation.state_changed.

Effects:

- update availability fields;
- suppress assigned records from public request board when configured;
- expose assigned records only to eligible actors.

## 5. Module 04 — Service Execution

Consumes:

- execution.started;
- execution.completed;
- execution.cancelled;
- execution.state_changed.

Effects:

- completed/cancelled records may be suppressed from marketplace discovery;
- administrative search may retain references by permission.

## 6. Module 05 — Financial Operations

Consumes:

- price_summary.updated;
- payment_visibility.changed;
- settlement_state.changed.

Effects:

- update price range filters;
- hide payment-sensitive fields from unauthorized actors.

Module 09 must never mutate ledgers, balances, invoices, payouts, or payment records.

## 7. Module 06 — Trust, Safety, Dispute & Compliance

Consumes:

- trust.status_changed;
- compliance.status_changed;
- dispute.visibility_restriction_changed;
- safety.suppression_created;
- safety.suppression_removed.

Effects:

- hard suppress;
- demote;
- restore;
- change permission tags;
- trigger critical priority processing.

## 8. Module 07 — Communication, Notification & Support

Produces to Module 07:

- search.saved_search_match_found;
- search.reindex_failed;
- search.abuse_signal_detected;
- search.critical_suppression_failed.

Module 07 owns delivery, channels, templates, and support communication.

## 9. Module 08 — Identity, Roles, Profiles & Access

Consumes:

- actor.profile_updated;
- actor.role_changed;
- actor.permission_changed;
- organization.profile_updated;
- organization.membership_changed;
- profile.visibility_changed;
- tenant.access_policy_changed.

Requires Module 08 for:

- actor resolution;
- tenant membership;
- permission grants;
- role boundaries;
- profile visibility;
- organization hierarchy.

Module 09 must not define independent role truth.
