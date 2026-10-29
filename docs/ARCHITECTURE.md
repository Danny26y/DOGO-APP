# Architecture

## Source scope

The authoritative business reference is the DOGO Master Document, especially Section 9. The project is a modular monolith for the responsive Web MVP: public tracking and storefront, merchant/B2B logistics and fulfillment, and operations review. The broader mobile super-app is not the initial web scope.

## Proposed stack (engineering recommendation)

Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL, Pytest, Docker Compose, and a production ASGI server. Keep dependencies reproducible and use migrations for all schema changes.

## Module boundaries

- `core`: settings, security primitives, request IDs, error mapping.
- `db`: engine, session lifecycle, declarative base, migrations.
- `modules/auth`: registration, login, profile, token lifecycle, organizations and memberships.
- `modules/customers`: customer address book and customer dashboard.
- `modules/delivery`: rider/driver profiles, manual shipment assignments, role-scoped progress and operations summaries.
- `modules/shipments`, `pricing`: booking, tracking, status transitions and configurable rate rules.
- `modules/marketplace`, `orders`: storefront, merchant catalog/inventory, carts and pending checkout records.
- `modules/dashboards`, `audit`: read-only role-scoped summaries and append-only audit history.
- Later modules: `payments`, `invoices`, `verification`; provider contracts live in `integrations` until approved implementations are selected.
- `api`: versioned router composition and shared dependencies.
- `integrations`: provider adapters; no provider is active until configured and verified.

HTTP routes validate and serialize; services enforce domain rules; persistence owns constraints and transactions; policy dependencies check access. Keep shipments, orders, and payments distinct but related.

## Tenant security

Users act through organization memberships. Tenant resources carry an organization owner and are queried through that scope. Platform operations permissions are separate from organization roles. Deny by default; do not trust client roles, tenant IDs, prices, payment states, or permissions.

## Integration boundaries

Provider-independent manual delivery assignments and status events are implemented. External dispatch adapters, live GPS, SLAs and proof verification/storage remain separate integrations. Payment adapters must verify signed provider events and process idempotently before marking an order paid. Do not implement custodial wallets, escrow, crypto custody, or payouts without approved design and compliance review.

## Initial data model direction

Identity: User, Organization, OrganizationMembership. Planned logistics: Shipment, ShipmentEvent, Waybill, Hub/ServiceZone, PricingRule. Planned commerce: MerchantProfile, Product, ProductCategory, InventoryMovement, Cart/CartItem, Order/OrderItem. Planned governance: Payment/PaymentEvent, Invoice, KYBSubmission/KYBDocument, AuditLog. Define tenant ownership, status transitions, references, timestamps, foreign keys, and indexes with each module and migration.
