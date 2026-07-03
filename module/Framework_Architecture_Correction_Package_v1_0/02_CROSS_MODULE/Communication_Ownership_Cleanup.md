# Communication Ownership Cleanup v1.0

## Rule

Only Module 07 sends or schedules communications. Modules 01–06 and 08 emit CES events.

## Required Refactor

Any document named Notification Engine, SMS Engine, Email Engine, Push Engine, Reminder Engine or Message Engine outside Module 07 must be interpreted as a business-event trigger catalog, not a delivery engine.

## Correct Flow

1. Business module changes state.
2. Business module emits a CES event.
3. Module 07 consumes event.
4. Module 07 resolves audience, template, channel, preference, consent, provider, retry and delivery audit.
