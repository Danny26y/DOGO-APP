# Frontend handoff

The API uses `/api/v1`, bearer authentication for protected routes, JSON, and the shared error envelope in `API_CONTRACT.md`. Local interactive OpenAPI docs are at `/docs`.

The current orders API creates only pending order records. It does not charge payment, reserve stock, or fulfill. Use `Idempotency-Key` on order creation. Product and inventory schemas are available in OpenAPI: public products show only platform-published, in-stock items; merchant writes require organization ownership; new products are unpublished drafts. Do not assume fare values, payment success from redirects, GPS availability, or escrow semantics. Payment and KYB contracts remain incomplete.

Customer screens can use `PATCH /api/v1/users/me`, the `/api/v1/customers/me/addresses` address-book routes, and `/api/v1/customers/me/dashboard`. Checkout sends a caller-owned `delivery_address_id` to `POST /api/v1/orders`; the order snapshots that address and prices but remains unpaid and unfulfilled. Store screens can use `/api/v1/merchant/store-profile`, `/api/v1/merchant/dashboard`, and the public `/api/v1/marketplace/stores/{storefront_slug}` catalog. Platform management summaries are available at `/api/v1/admin/dashboard/summary`; they report persisted counts only. No rider/driver, dispatch assignment, live GPS, payment, or settlement routes are available yet.

Organization settings and staff screens can use `PATCH /api/v1/organizations/{id}` and the member list/add/update/remove routes. Only owners can change roles or remove members; owners cannot remove or demote themselves through these routes.

Platform catalog moderation can use `GET /api/v1/admin/products/review-queue` with limit/offset pagination, then `POST /api/v1/admin/products/{id}/publish?organization_id=...` to approve an item. Rejection states and merchant-facing review notes are not modeled yet.
