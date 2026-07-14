# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


# Traceability Matrix

| Decision / Rule | Product Spec | Business Rules | Architecture | Data Model | API | UI | Tests |
|---|---|---|---|---|---|---|---|
| Customer-choice matching | FR-205 | BR-256 | Pipeline | customer_selections | select candidate | comparison screen | TS-238 |
| Service-need matching | FR-201 | BR-219 | Matching Engine | request_service_need_id | matches API | grouped UI | TS-216 |
| Multi-need package | FR-202 | BR-220/221 | Matching Engine | covers_need_ids | matches API | package cards | TS-217/218 |
| Platform approval | FR-206 | BR-201 | Eligibility | providers.lifecycle_status | internal | admin profile | TS-201 |
| Service-level eligibility | FR-201 | BR-208 | Eligibility | provider_service_profiles | internal | provider profile | TS-206 |
| Hierarchical company | FR-203 | BR-205 | Eligibility | company_id | internal | company provider card | TS-204 |
| Geographic coverage | FR-203 | BR-212 | Eligibility | service_coverages | internal | none | TS-209/210 |
| Schedule conflict | FR-203 | BR-216 | Availability | busy_intervals | internal | none | TS-212 |
| Broadcast distribution | FR-204 | BR-223 | Distribution | match_rounds.strategy | internal | provider invitations | TS-220 |
| Accept/Reject | FR-204 | BR-225 | Candidate Response | candidate_responses | accept/reject | invitation screen | TS-221/222 |
| Ranking weights | FR-206 | BR-232 | Ranking | ranking_weight_settings | admin settings | admin settings | TS-228 |
| Company bonus | FR-206 | BR-233 | Ranking | ranking settings | admin settings | admin settings | TS-229 |
| Summary card | FR-205 | BR-236 | Presentation | presentation read model | matches API | candidate card | TS-232/233 |
| Trust profile | FR-205 | BR-240 | Presentation | provider_documents | profile API | profile screen | TS-237 |
| Notification settings | FR-206 | BR-241 | Notification | notification_settings | admin settings | admin settings | TS-243-248 |
| Expiration | FR-206 | BR-249/250 | Expiry | match_rounds | reopen API | status UI | TS-249-252 |
| Reopen matching | FR-206 | BR-251 | Expiry | match_rounds | reopen API | admin panel | TS-252/253 |
| Manual suggestion | FR-206 | BR-253 | Manual | manual_intervention_logs | suggest API | admin badge | TS-256 |
| Audit logs | NFR | BR-255 | Manual | audit logs | audit API | audit UI | TS-258 |
| Module boundary | Scope | BR-258 | Boundary | customer_selections | select API | confirmation | TS-260/261 |
