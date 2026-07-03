# Cross-Module Contracts

## Module 08 Identity Contract
Provides actor identity, role, verification status, tenant membership, profile attributes, company affiliation and risk-relevant identifiers.

## Module 03 Booking Contract
Provides booking status, assignment state, provider actor, customer actor and booking lifecycle events.

## Module 04 Execution Contract
Provides service completion, cancellation, check-in validation and execution proof states.

## Module 05 Financial Contract
Receives approved ledger instructions and returns payment settlement, refund, reversal and payable status. Module 11 cannot directly mutate ledger balances.

## Module 06 Trust Contract
Provides dispute status, compliance holds, fraud escalation result and actor risk status.

## Module 10 Geospatial Contract
Provides location validation, region membership, service area matching, distance signals and geographic risk indicators.

## Contract Rule
No module may consume private internal tables from another module. All interactions must use events, APIs, or documented read models.
