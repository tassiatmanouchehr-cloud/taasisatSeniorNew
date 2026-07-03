# Permission Matrix

## Roles
- Platform Owner
- Platform Admin
- Marketing Manager
- Finance Manager
- Compliance Manager
- Support Operator
- Tenant Admin
- Company Admin
- Auditor
- Read-only Analyst

## Capabilities
Create campaign: Platform Admin, Marketing Manager.
Publish campaign: Platform Admin or authorized Marketing Manager with approval.
Pause campaign: Platform Admin, Marketing Manager, Compliance Manager.
Create policy draft: Platform Admin, Marketing Manager.
Publish policy version: Platform Admin only unless delegated.
Approve high-value reward: Finance Manager.
Override referral: Platform Admin, Compliance Manager.
Reverse reward: Finance Manager or Compliance Manager with reason.
View reports: authorized finance, marketing, admin and audit roles.
View fraud signals: compliance and restricted admin roles only.

## Boundary Rules
Tenant admins may only manage campaigns scoped to their tenant if platform policy allows. Company admins may not create platform-wide incentives. Support cannot approve financial rewards unless explicitly granted.
