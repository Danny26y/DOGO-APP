# Requirements traceability

Status meanings: **Planned** = documented but not implemented; **Partial** = only part exists; **Deferred** = outside current Web MVP or pending approval; **Blocked** = safe implementation depends on a decision/provider. Tests are not claimed until run.

| Source | Requirement | Priority | Status | Module/API | Verification / dependency |
|---|---|---:|---|---|---|
| §9.2–9.4 | Public guest shipment tracking | P1 | Partial | `GET /api/v1/tracking/{tracking_number}` | status only; rate limiting and receipts remain |
| §9.2 | Public delivery rate calculator | P1 | Partial | `POST /api/v1/pricing/quotes` | requires rules; zone base + weight only; distance/SLA pending |
| §9.2 | Public storefront catalog | P2 | Partial | `GET /api/v1/marketplace/products` | publication/admin review; no checkout |
| §9.2, §9.4 | Merchant/B2B dispatch booking | P1 | Partial | `POST /api/v1/shipments` | quote-backed manual booking; dispatch integration remains |
| §9.4 | CSV bulk booking up to 500 parcels | P1 | Partial | `POST /api/v1/shipments/bulk` | 500-row and 2 MB caps; per-row outcomes; broader CSV tests remain |
| §9.2, §9.4 | Shipment/fleet status visibility | P1 | Partial | shipment list and status API | event updates; no GPS/rider system |
| §9.2 | Merchant product catalog and stock | P2 | Partial | `/api/v1/merchant/products`, inventory route | tenant scope and stock safety tested; cart/orders remain |
| §9.2 | Cart and order records | P2 | Partial | `/api/v1/cart`, `POST/GET /api/v1/orders` | snapshots and idempotent create; no payment or stock reservation |
| §9.2 | Paid checkout and fulfillment | P2 | Blocked | orders/payments/shipments | provider verification, stock reservation, and fulfillment contract |
| §9.2, §9.4 | Fiat payments, invoices, KYB | P3 | Blocked/Planned | payments/invoices/verification | provider, credentials and storage decisions |
| §9.5 | Auditable financial records | P3 | Planned | payments/ledger | persistence and duplicate-event tests |
| User request §9 | Audit log for sensitive admin and business writes | P0 | Partial | `/api/v1/admin/audit-logs` | persists identity, membership, pricing, shipment, inventory, product and order events; financial audit coverage pending |
| §9.6 | Foundation, identity and RBAC | P0 | Partial | auth/organizations | access/refresh rotation, organization roles and owner-controlled membership; password reset, invitations and broader RBAC remain |
| User request §§4,7 | Tenant isolation and secure auth | P0 | Partial | core/auth/organizations | auth tests pass; resource-specific tenant checks remain |
| User request §§8,12 | Versioned API, OpenAPI, containers, CI | P0 | Partial | repository | OpenAPI, Docker/Compose, CI config exist; CI not run remotely |
| §9.2 | Hailing, drones, warehouse robotics | Deferred | Deferred | future | outside Web MVP |
| §9.2, §9.4 | Live GPS, OTP POD, automated dispatch | Deferred/Blocked | Blocked | dispatch integrations | operational process/provider decision |

Extend entries with concrete routes, migrations, test names/results, and dependencies as implementation proceeds. Distinguish source requirements from engineering recommendations.
