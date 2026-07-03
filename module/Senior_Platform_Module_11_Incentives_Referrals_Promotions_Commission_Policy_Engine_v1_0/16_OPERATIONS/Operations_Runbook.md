# Operations Runbook

## Campaign Launch Checklist
1. Define business objective.
2. Define target segment.
3. Define reward and caps.
4. Define fraud gates.
5. Define settlement criteria.
6. Simulate expected spend.
7. Review with finance and compliance.
8. Publish policy version.
9. Activate campaign.
10. Monitor spend, fraud holds and conversion.

## Emergency Pause
Authorized admins may pause campaign evaluation immediately. Pausing prevents new rewards but does not delete existing reward records.

## Reward Incident Handling
For incorrect reward creation, create reversal decision, emit reward.reversed, request Module 05 reversal instruction if money was posted, and preserve full audit chain.
