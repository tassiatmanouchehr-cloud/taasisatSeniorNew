# Permission Matrix

| Capability | Anonymous | Requester | Provider | Organization Operator | Tenant Admin | Platform Operator | Platform Admin |
|---|---:|---:|---:|---:|---:|---:|---:|
| Public discovery search | yes | yes | yes | yes | yes | yes | yes |
| Private request discovery | no | own only | eligible only | org scope | tenant scope | platform scope | platform scope |
| Provider directory search | yes if enabled | yes | yes | yes | yes | yes | yes |
| Organization directory search | yes if enabled | yes | yes | yes | yes | yes | yes |
| Administrative search | no | no | no | limited | yes | limited | yes |
| Support case lookup | no | no | no | no | conditional | yes | yes |
| Saved search create | no | yes | yes | yes | yes | yes | yes |
| Tenant reindex | no | no | no | no | yes | conditional | yes |
| Cross-tenant search | no | no | no | no | no | conditional | yes |
| Ranking profile manage | no | no | no | no | conditional | conditional | yes |
| Facet definition manage | no | no | no | no | conditional | conditional | yes |

Final authority is Module 08. This matrix is the Module 09 interpretation layer only.
