# Senior Platform — Module 17 — Analytics, Reporting & BI Engine v1.0

**Status:** Frozen Draft / Enterprise Package v1.0  
**Domain:** Generic Service Marketplace Framework  
**Zero-domain-leakage:** Mandatory  
**Multi-tenant boundary:** Mandatory  

Metrics, dashboards, funnels, cohorts, exports, scheduled reports, semantic layer, data governance and KPI definitions.

---

| Role | Read | Create | Update Draft | Publish | Activate/Pause | Export | Audit | Override |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| PlatformOwner | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| PlatformAdmin | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| TenantOwner | Yes | Yes | Yes | Yes | Yes | No | No | No |
| TenantAdmin | Yes | Yes | Yes | Yes | Yes | No | No | No |
| OperationsManager | Yes | Yes | Yes | No | No | No | No | No |
| SupportAgent | Yes | No | No | No | No | No | No | No |
| FinanceUser | Yes | No | No | No | No | No | No | No |
| MarketingUser | Yes | No | No | No | No | No | No | No |
| ComplianceAuditor | Yes | No | No | No | No | Yes | Yes | No |
| ReadOnlyAnalyst | Yes | No | No | No | No | Yes | No | No |
| ExternalPartner | Limited | No | No | No | No | No | No | No |
| EndUser | Yes | No | No | No | No | No | No | No |