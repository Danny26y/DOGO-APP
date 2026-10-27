# Frontend handoff

The API uses `/api/v1`, bearer authentication for protected routes, JSON, and the shared error envelope in `API_CONTRACT.md`. Local interactive OpenAPI docs are at `/docs`.

The current orders API creates only pending order records. It does not charge payment, reserve stock, or fulfill. Use `Idempotency-Key` on order creation. Product and inventory schemas are available in OpenAPI: public products show only platform-published, in-stock items; merchant writes require organization ownership; new products are unpublished drafts. Do not assume fare values, payment success from redirects, GPS availability, or escrow semantics. Payment and KYB contracts remain incomplete.
