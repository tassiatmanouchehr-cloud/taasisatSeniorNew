# Trusted Person Order-Scoped Access Workflow

## Purpose
A customer may invite a trusted person to observe a specific order without granting access to the customer account, financial history, other orders or administrative capabilities.

## Flow
1. Customer selects an existing order they are authorized to manage.
2. Customer enters trusted person's contact information.
3. Module 08 creates a pending trusted actor or links to an existing account.
4. Secure invitation is issued with scoped token.
5. Trusted person accepts invitation and verifies contact where required.
6. Trusted access grant becomes active for one order only.
7. Module 07 may send order-related communications to the trusted person according to grant permissions.
8. Access ends on expiry, explicit revocation, order closure policy or account risk event.

## Allowed Capabilities
- View order progress.
- Receive communications related only to the granted order.
- View service completion state.
- View limited provider/company public profile attached to the order.

## Denied Capabilities
- No access to customer account settings.
- No access to customer financial history.
- No access to other orders.
- No ability to create, modify, cancel or pay unless explicitly introduced in a future extension and configured.
- No platform administration or organization administration permission.
- No visibility into private documents, private addresses beyond order-specific safe display policy, or unrelated communications.

## Security Controls
- Resource-bound grant.
- Token expiry.
- Optional MFA/contact verification.
- Revocation by customer or platform-authorized actor.
- Automatic revocation on suspicious activity.
- Full audit trail.
