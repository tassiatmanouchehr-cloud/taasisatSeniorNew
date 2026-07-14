# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# Glossary

## Customer or Customer Delegate
The person or family member who creates and owns a service request.

## گیرنده‌ی خدمت (Service Recipient)
The service recipient person or customer the request is for; may differ from the owner.

## ارائه‌دهنده (Provider)
Independent provider, company provider, or company that can serve a request.

## Request
A single service request created in Module 01.

## Service Need
A specific service inside a request (e.g. night nursing, physiotherapy, home lab).

## اعلام آمادگی (Application)
A provider declaring willingness for a published request.

## قرارداد (Contract)
A recurring commitment that contains multiple sessions.

## جلسه (Session)
One occurrence inside a contract.

## Validation
The check that a request has enough information to be published.

## Publishing
Showing a request to a bounded set of eligible providers.

## Targeted Distribution
Notifying a most-relevant subset instead of all eligible providers.

## Smart Distribution
Future strategy where the system/AI selects recipients.

## Request Life Cycle
The status machine from Draft to Completed / Cancelled.

## Timeline
Role-filtered chronological history of a request.

## Event-Driven Architecture
Design where request actions become events that other modules react to.

## Need-to-Know (Principle 1)
Show the right information, to the right people, at the right time, only as much as necessary.

## Platform First (Principle 2)
The platform protects a fair process, not one side; a fair process is always right.

## Platform Protection
Detection of off-platform bypass and abuse (phone sharing, external price, cancel-after-arrival).

## Protection Signal
A flag raised when a bypass or abuse pattern is detected.

## Freeze
Locking a module after all four exit criteria are met.
