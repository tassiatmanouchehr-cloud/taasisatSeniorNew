# Registration & Onboarding Workflows

## Company Registration
1. Applicant creates organization registration request.
2. Identity/account created in pending state.
3. Organization actor created in onboarding state.
4. Required organization profile fields collected.
5. Required verification documents requested by CCS policy.
6. Verification workflow begins.
7. Platform reviewer approves/rejects organization.
8. On approval, organization becomes active and receives tenant administration capability.
9. CES events are published for each state change.

## Independent Provider Registration
1. Human account is created.
2. Provider actor is created as `INDEPENDENT_PROVIDER` in onboarding state.
3. Provider profile draft is created.
4. Required identity/professional verification is requested.
5. Provider completes onboarding requirements.
6. Platform or automated workflow approves activation according to CCS.
7. Provider becomes active when required checks pass.

## Customer Registration
1. Customer account is created through direct sign-up, order flow or invited flow.
2. Customer actor is created.
3. Required contact verification is performed.
4. Customer profile remains private by default.
5. Optional trusted contacts can be added only through explicit invitation flows.

## Company-Affiliated Provider Flow
1. Provider registers independently.
2. Provider optionally enters a company identifier during onboarding.
3. System validates identifier format without automatically granting membership.
4. Affiliation request is created with status `pending_approval`.
5. Company administrator receives review task through Module 07.
6. Company administrator approves or rejects.
7. If approved, organization provider membership becomes active.
8. Provider actor receives `ORGANIZATION_PROVIDER` context for that organization.
9. If rejected or ignored, provider remains independent.
10. Provider may later request affiliation again, subject to rate limits and policy.

## Staff Invitation Flow
1. Organization administrator invites staff by verified contact.
2. Invitation token is issued with limited expiry.
3. Invitee accepts and creates/signs into account.
4. Organization assigns role within allowed role boundary.
5. Staff membership becomes active.
6. Audit and CES events record invitation, acceptance and role assignment.

## Onboarding Completion Rule
An actor is active only when mandatory identity, contact, verification, profile and policy acceptance requirements for that actor type are satisfied.
