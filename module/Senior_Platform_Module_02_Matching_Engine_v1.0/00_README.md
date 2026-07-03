# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


## Package Contents

This documentation package contains the standard output for **Module 02 — Matching Engine** of the Generic Service Marketplace Framework Reference Implementation platform.

### Documents

1. `01_Module_02_Product_Specification.md`
2. `02_Module_02_Business_Rules.md`
3. `03_Module_02_Architecture.md`
4. `04_Module_02_Domain_Model.md`
5. `05_Module_02_State_Machines.md`
6. `06_Module_02_System_Flows.md`
7. `07_Module_02_Data_Model.md`
8. `08_Module_02_API_Contracts.md`
9. `09_Module_02_Admin_Functions.md`
10. `10_Module_02_Permissions.md`
11. `11_Module_02_UI_Screens.md`
12. `12_Module_02_Exception_Scenarios.md`
13. `13_Module_02_Test_Scenarios.md`
14. `14_Module_02_ADRs.md`
15. `15_Module_02_Glossary.md`
16. `16_Module_02_Traceability_Matrix.md`
17. `17_Module_02_Product_Bible.md`

## Frozen Scope

Module 02 receives approved requests and service needs from Module 01. It identifies eligible providers, distributes requests, collects candidate responses, ranks accepted candidates, presents them to the customer/family, and records the final customer selection boundary.

Module 02 does **not** own final reservation, contract, payment, legal commitment, or final assignment. Those begin in Module 03.


---

# Generic Framework Correction Notice
This package has been corrected to operate as a generic, reusable, event-driven service marketplace module. Domain-specific terminology, where retained, is non-normative reference implementation material only.
