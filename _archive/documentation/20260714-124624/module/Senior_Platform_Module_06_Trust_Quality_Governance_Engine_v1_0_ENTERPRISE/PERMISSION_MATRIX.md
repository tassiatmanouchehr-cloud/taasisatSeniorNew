# Module 06 — Permission Matrix v1.0

## Roles

- Customer
- Provider
- Organization Admin
- Organization Operator
- Platform Operator
- Platform Admin
- Platform Owner
- System

## Permission Rules

### Review
- Submit Review: Customer / Provider
- Edit Own Review: Reviewer, within config window
- Hide Review: Platform Admin
- Remove Review: Platform Admin
- Dispute Review: Reviewee / Platform Staff
- Restore Review: Platform Admin

### Complaint
- Open Complaint: Customer / Provider / Organization / Platform Staff
- Add Evidence: Case Participant / Assigned Staff
- Assign Complaint: Platform Admin / Organization Admin for own org
- Resolve Complaint: Assigned Staff
- Close Complaint: Platform Admin / Authorized Operator

### Dispute
- Open Dispute: Case Participant / Platform Staff
- Add Evidence: Participant / Mediator
- Assign Mediator: Platform Admin
- Decide Dispute: Platform Admin / Authorized Mediator
- Appeal Dispute Decision: Affected Party

### Violation
- Create Violation Case: System / Platform Staff
- Classify Violation: Platform Staff
- Confirm Violation: Platform Admin
- Dismiss Violation: Platform Admin

### Decision
- Create Recommendation: System / Staff
- Approve Warning: Operator+
- Approve Restriction: Platform Admin
- Approve Suspension: Platform Admin
- Approve Permanent Ban: Platform Owner
- Approve Financial Recommendation: Platform Admin; execution by Module 05

### Enforcement
- Issue Warning: Authorized Staff
- Apply Restriction: Platform Admin
- Apply Suspension: Platform Admin
- Apply Permanent Ban: Platform Owner
- Lift Enforcement: same or higher authority than issuer

### Compliance
- Upload Document: Provider / Organization
- Verify Document: Authorized Staff
- Revoke Compliance: Platform Admin
- Override Compliance: Platform Owner

### Risk
- Generate Risk Signal: System / Staff
- Open Risk Case: System / Platform Staff
- Dismiss Risk Case: Platform Admin
- Change Risk Rules: Platform Owner / Platform Admin with approval

### Appeal & Reopen
- Submit Appeal: Affected Party
- Review Appeal: Platform Staff
- Approve Appeal: Platform Admin
- Reopen Case: Platform Admin
- Force Reopen Sensitive Case: Platform Owner

### Reporting
- Own Reports: Organization Admin
- Organization Reports: Organization Admin
- Platform Reports: Platform Admin / Platform Owner
- Audit Reports: Platform Owner / Authorized Auditor

## Generic Service Marketplace Rule

Company can only access cases connected to its own organization.  
Platform Owner and platform-level roles can access the entire marketplace.
