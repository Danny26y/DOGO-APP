# Testing

Use Pytest with isolated configuration and a dedicated database. Planned coverage: authentication, RBAC and tenant isolation, validation/errors, shipment transitions, pricing boundaries, tracking disclosure, bulk row failures, inventory concurrency, checkout/fulfillment idempotency, webhook ordering, migrations, KYB permissions, and OpenAPI consistency. Tests are reported only when run and observed. External providers are mocked by default; sandbox procedures follow provider approval.

## Foundation milestone result

`pytest -q -p no:cacheprovider`: 8 passed. `ruff check app tests`: passed. Alembic migrations upgraded a local SQLite development database successfully. Coverage includes auth, refresh rotation/reuse/logout, organization ownership, zone quote math, quote-to-shipment matching, tracking disclosure, QR verification, status progression, proof requirements, cross-tenant denial, catalog visibility, inventory floors, idempotent pending orders, bulk CSV partial failures and limits, and restricted audit logs. PostgreSQL Compose startup and hosted CI have not been run here.

Migration verification passed for the full six-migration chain on a clean SQLite database: upgrade to head, downgrade to base, then upgrade to head. `alembic check` reported no new operations. The merchant catalog/inventory suite adds category, unpublished draft, stock adjustment, nonnegative stock, and cross-tenant product access checks.
