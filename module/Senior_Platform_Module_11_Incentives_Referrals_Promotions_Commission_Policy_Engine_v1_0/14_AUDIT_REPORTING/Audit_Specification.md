# Audit Specification

## Audit Requirements
Every policy, campaign, referral, evaluation, reward, promotion and commission adjustment must be audit logged.

## Evaluation Audit Record
- tenant_id
- evaluation_id
- trigger_event
- actor_context
- source entity
- campaign_id
- policy_id
- policy_version
- input snapshot hash
- eligibility result
- reason codes
- fraud score
- conflict resolution result
- output effects
- evaluator version
- timestamp

## Explainability
The system must answer:
- Why was this actor eligible?
- Why was this actor rejected?
- Which policy version was used?
- Which campaign produced the reward?
- Why was reward amount calculated this way?
- Why was reward held, reversed or expired?
