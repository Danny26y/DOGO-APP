# Team workflow

## Workstreams and dependencies

1. Foundation/identity owns `core`, `db`, `auth`, `organizations`, and shared API conventions.
2. Logistics/pricing owns shipments, waybills, pricing and dispatch; depends on identity/tenant policy.
3. Marketplace/inventory owns catalog, stock and orders; depends on identity/tenant policy.
4. Payments/invoices/verification owns provider adapters, financial events and KYB; depends on order contract and approved decisions.
5. Frontend integration consumes OpenAPI and contract checks; depends on stable schemas.

Use feature branches, pull requests, reviewed migrations, automated checks, and backward-compatible API changes. Coordinate edits to shared API/security/database files. The user authorized a push to `Danny26y/DOGO-APP` only after all milestones are complete; this project workflow does not authorize merges or production deployment.
