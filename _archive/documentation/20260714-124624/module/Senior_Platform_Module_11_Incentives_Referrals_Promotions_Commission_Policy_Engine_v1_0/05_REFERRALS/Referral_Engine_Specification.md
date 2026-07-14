# Referral Engine Specification

## Supported Referral Channels
- Manual referral code
- Referral link
- Invite token
- QR code
- Admin-created referral
- Partner attribution
- Campaign landing page
- Deep link attribution

## Validation Rules
- No self-referral unless explicitly allowed.
- No referral across tenant boundary unless cross-tenant partner policy exists.
- Referrer must be eligible under active policy.
- Invitee must be eligible under active policy.
- Referral may expire.
- Referral may be locked after first qualifying activity.
- Manual override requires permission and audit reason.

## Referral Ownership
If multiple attribution sources exist, ownership is resolved by policy:
- first touch
- last touch
- highest priority campaign
- manual override
- partner contract
- fraud hold
