# Architecture

## Source scope

The authoritative business reference is the DOGO Master Document, especially Section 9. The project is a modular monolith for the responsive Web MVP: public tracking and storefront, merchant/B2B logistics and fulfillment, and operations review. The broader mobile super-app is not the initial web scope.

## Proposed stack (engineering recommendation)

Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL, Pytest, Docker Compose, and a production ASGI server. Keep dependencies reproducible and use migrations for all schema changes.

## Module boundaries

- `core`: settings, security primitives, request IDs, error mapping.
- `db`: engine, session lifecycle, declarative base, migrations.
- `modules/auth`: registration, login, token lifecycle.
- `modules/organizations`: organizations, memberships, tenant policies.
- Planned: `shipments`, `pricing`, `dispatch`, `marketplace`, `inventory`, `orders`, `payments`, `invoices`, `verification`.
- `api`: versioned router composition and shared dependencies.
- `integrations`: provider adapters; no provider is active until configured and verified.

HTTP routes validate and serialize; services enforce domain rules; persistence owns constraints and transactions; policy dependencies check access. Keep shipments, orders, and payments distinct but related.

## Tenant security

Users act through organization memberships. Tenant resources carry an organization owner and are queried through that scope. Platform operations permissions are separate from organization roles. Deny by default; do not trust client roles, tenant IDs, prices, payment states, or permissions.

## Integration boundaries

Payment adapters support trusted verification only after approval. Webhooks must validate signatures and process idempotently. Do not implement custodial wallets, escrow, crypto custody, or payouts without approved design and compliance review. Dispatch/GPS availability is not assumed; record statuses only when an authorized operator or configured system supplies them.

## Initial data model direction

Identity: User, Organization, OrganizationMembership. Planned logistics: Shipment, ShipmentEvent, Waybill, Hub/ServiceZone, PricingRule. Planned commerce: MerchantProfile, Product, ProductCategory, InventoryMovement, Cart/CartItem, Order/OrderItem. Planned governance: Payment/PaymentEvent, Invoice, KYBSubmission/KYBDocument, AuditLog. Define tenant ownership, status transitions, references, timestamps, foreign keys, and indexes with each module and migration.
