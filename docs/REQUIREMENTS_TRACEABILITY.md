# Requirements traceability

Status meanings: **Planned** = documented but not implemented; **Partial** = only part exists; **Deferred** = outside current Web MVP or pending approval; **Blocked** = safe implementation depends on a decision/provider. Tests are not claimed until run.

| Source | Requirement | Priority | Status | Module/API | Verification / dependency |
|---|---|---:|---|---|---|
| §9.2–9.4 | Public guest shipment tracking | P1 | Partial | `GET /api/v1/tracking/{tracking_number}` | status only; rate limiting and receipts remain |
| §9.2 | Public delivery rate calculator | P1 | Partial | `POST /api/v1/pricing/quotes` | requires rules; zone base + weight only; distance/SLA pending |
| §9.2 | Public storefront catalog | P2 | Partial | `GET /api/v1/marketplace/products` | publication/admin review; no checkout |
| §9.2, §9.4 | Merchant/B2B dispatch booking | P1 | Partial | `POST /api/v1/shipments` | quote-backed manual booking; dispatch integration remains |
| §9.4 | CSV bulk booking up to 500 parcels | P1 | Partial | `POST /api/v1/shipments/bulk` | 500-row and 2 MB caps; per-row outcomes; broader CSV tests remain |
| §9.2–9.4 | Shipment/rider/driver status and assignment | P1 | Partial | `/api/v1/delivery/*`, `/api/v1/admin/shipments/{id}/assignments`, shipment status API | applications/approval, manual assignments, agent acceptance and role-scoped status events; no GPS provider or automated dispatch |
| §9.2 | Merchant product catalog, storefront and stock | P2 | Partial | `/api/v1/merchant/products`, `/api/v1/merchant/store-profile`, `/api/v1/marketplace/stores/{slug}`, inventory route | merchant storefront profile and public product page added; image hosting and approval flow remain |
| §9.2 | Cart, paid order and merchant fulfillment | P2 | Partial | `/api/v1/cart`, `/api/v1/orders`, `/api/v1/merchant/orders/{id}/fulfillment` | order snapshots price/address; verified payment reserves stock; merchant-scoped preparation/handoff; no refunds, reservation release/reconciliation, or automated shipment creation |
| Customer app / cancellation policy | Customer cancellation of unpaid orders | P1 | Partial | `POST /api/v1/orders/{id}/cancel` | records customer reason and timestamp, only before payment; fee categories, cancellation windows for assigned deliveries and refunds remain pending approval |
| §9.2 | Customer profile and saved delivery addresses | P1 | Implemented | `/api/v1/users/me`, `/api/v1/customers/me/addresses` | caller-scoped CRUD, default address selection, and audit events; email change/recovery remains |
| Customer verification terms | Versioned terms acceptance and privacy notice acknowledgement | P1 | Partial | `/api/v1/customers/me/verification-terms*` | version pair and timestamp are persisted; remains disabled until final approved terms/privacy URLs and versions are configured; identity checks are separate |
| User decision | Paystack checkout/webhook | P1 | Implemented (sandbox credentials required) | `/api/v1/payments/initialize`, `/api/v1/webhooks/paystack` | owner-scoped intent, webhook signature/amount/currency checks and event deduplication; settlement/refunds remain |
| User decision | Email OTP | P1 | Implemented (SMTP configuration required) | `/api/v1/auth/email-otp/*` | expiring hashed codes, resend/attempt limits, enforced on protected access when enabled |
| User decision | Customer identity manual review | P1 | Implemented (manual, not automated KYC) | `/api/v1/customers/me/identity-submissions`, `/api/v1/admin/identity-submissions*` | private file volume, admin download/review and audit; object storage, scanning and retention decisions remain |
| User decision | OSM routing | P2 | Implemented (regional dataset required) | `/api/v1/routing/route` | self-hosted OSRM API; no OSM geocoder or map tile service bundled |
| User request | Customer, merchant and platform dashboard summaries | P1 | Partial | `/api/v1/customers/me/dashboard`, `/api/v1/merchant/dashboard`, `/api/v1/admin/dashboard/summary` | read-only aggregates over persisted records; no financial totals, live GPS, ETA, or dispatch claims |
| §9.2 | Paid checkout and fulfillment | P2 | Partial | payments/orders/marketplace | Paystack webhook verification, per-order inventory reservations and merchant fulfillment progression implemented; refunds, settlement, reservation reconciliation and shipment creation remain |
| §9.2, §9.4 | Fiat payments, invoices, KYB | P3 | Blocked/Planned | payments/invoices/verification | provider, credentials and storage decisions |
| §9.5 | Auditable financial records | P3 | Planned | payments/ledger | persistence and duplicate-event tests |
| User request §9 | Audit log for sensitive admin and business writes | P0 | Partial | `/api/v1/admin/audit-logs` | persists identity, membership, pricing, shipment, inventory, product and order events; financial audit coverage pending |
| §9.6 | Foundation, identity and RBAC | P0 | Partial | auth/organizations/customers | access/refresh rotation, user profile, address ownership, organization profile and owner-managed member roles/removal; password recovery, invitation delivery and broader RBAC remain |
| User request §§4,7 | Tenant isolation and secure auth | P0 | Partial | core/auth/organizations | auth tests pass; resource-specific tenant checks remain |
| User request §§8,12 | Versioned API, OpenAPI, containers, CI | P0 | Partial | repository | OpenAPI, Docker/Compose, CI config exist; CI tests and Ruff pass locally; Docker engine and GitHub Actions run status were inaccessible from this workspace |
| §9.2–9.4 | Rider/driver accounts, dispatch and assignment | P1 | Partial | `/api/v1/delivery/*`, `/api/v1/admin/delivery/*` | agent applications, admin activation, explicit online/offline availability, assignment to online agents, progress events and operations dashboard; licensing verification and external dispatch integration remain |
| §9.2 | Hailing, drones, warehouse robotics | Deferred | Deferred | future | outside Web MVP |
| §9.2, §9.4 | Live GPS, proof verification/storage, automated dispatch | Deferred/Blocked | Blocked | dispatch/location/proof adapters | status and proof references are recorded; live location, evidence verification/storage and external provider depend on policy/provider decisions |

Extend entries with concrete routes, migrations, test names/results, and dependencies as implementation proceeds. Distinguish source requirements from engineering recommendations.
