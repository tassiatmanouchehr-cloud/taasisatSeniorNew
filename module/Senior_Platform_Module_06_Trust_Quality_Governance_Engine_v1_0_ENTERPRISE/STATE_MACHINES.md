# Module 06 — State Machines v1.0

## Review

```text
draft
→ submitted
→ pending_moderation
→ visible
   ├── disputed
   ├── hidden
   └── removed
```

## Complaint

```text
opened
→ triaged
→ under_review
   ├── waiting_for_evidence
   ├── escalated
   ├── resolved
   └── rejected
→ closed
```

## Dispute

```text
created
→ evidence_collection
→ mediation
→ decision_pending
→ decided
   ├── accepted
   ├── appealed
   └── enforcement_pending
→ closed
```

## Violation

```text
detected
→ classified
→ investigating
   ├── no_violation
   ├── confirmed_violation
   └── escalated
→ decision_required
→ enforced
→ closed
```

## Risk Case

```text
signal_generated
→ risk_scored
→ case_opened
→ under_review
   ├── false_positive
   ├── watchlisted
   ├── restricted
   ├── suspended
   └── escalated
→ closed
```

## Compliance

```text
not_required
→ required
→ submitted
→ under_verification
   ├── verified
   ├── rejected
   ├── expired
   └── revoked
```

## Enforcement

Warning:
```text
issued → acknowledged → expired / escalated / converted_to_restriction
```

Restriction:
```text
created → active → expired / lifted / extended / converted_to_suspension
```

Suspension:
```text
pending → active → appealed / expired / lifted / converted_to_ban
```

## Appeal

```text
submitted
→ accepted_for_review
→ under_review
   ├── need_more_evidence
   ├── approved
   ├── partially_approved
   └── rejected
→ closed
```
