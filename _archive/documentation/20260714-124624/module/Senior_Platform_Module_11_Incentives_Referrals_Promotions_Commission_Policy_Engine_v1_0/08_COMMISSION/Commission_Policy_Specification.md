# Commission Policy Specification

## Purpose
Commission policies alter platform commission calculations based on business rules without changing financial engine code.

## Supported Adjustments
- percentage reduction
- fixed commission reduction
- capped commission
- zero commission window
- first-N-orders commission reduction
- first-N-days reduction
- role-based commission
- company-based commission
- geography-based commission
- service-category-based commission
- performance-tier commission

## Integration with Module 05
Module 11 decides eligibility and adjustment. Module 05 remains authoritative for ledger posting, invoice totals, settlement, payable balances, tax handling, and accounting records.

## Locking
Commission effects become locked after the related financial transaction reaches configured settlement finality.
