# Fraud Prevention Specification

## Fraud Signals
- self-referral
- duplicate phone
- duplicate identity document
- duplicate bank account
- duplicate device fingerprint
- suspicious IP or VPN
- circular referrals
- referral farming
- fake orders
- repeated cancellations after reward creation
- shared payout instruments
- abnormal geographic distance
- low trust score
- blacklisted actor
- excessive campaign usage

## Actions
- allow
- allow with monitoring
- hold reward
- require manual review
- reject reward
- invalidate referral
- reverse reward
- escalate to Module 06

## Fraud Explainability
Every fraud decision must include reason codes, signal values, policy threshold, evaluator version, and reviewer identity if manual.
