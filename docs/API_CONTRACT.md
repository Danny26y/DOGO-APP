# Initial API contract

Base path: `/api/v1`. OpenAPI is exposed by FastAPI at `/openapi.json`; interactive docs at `/docs`. This proposed list must be refined with approved business rules.

| Method/path | Purpose | Access | Initial behavior |
|---|---|---|---|
| `GET /health/live` | Liveness | Public | Process status |
| `GET /health/ready` | Readiness | Public | Checks configured database |
| `POST /auth/register`, `/auth/login` | Register/authenticate | Public | Validate input; hashed passwords |
| `POST /auth/refresh` | Rotate refresh session | Refresh token body | One-time rotation; reuse revokes that token family |
| `POST /auth/logout` | Revoke refresh session | Refresh token body | Access token remains valid until its short expiry |
| `GET /users/me` | Current user | Authenticated | Implemented; caller profile only |
| `GET/POST /organizations` | List/create organization | Authenticated | Implemented; caller memberships; creator is owner |
| `GET/POST /organizations/{id}/members` | List/add organization members | Owner manages; owner/admin reads | Adds an existing active account; roles are organization-scoped |
| `POST /pricing/quotes` | Fare estimate | Public | Configured exact zone-pair/tier rule; 503 if unavailable; 15-minute quote |
| `POST /pricing/rules`, `GET /pricing/rules` | Manage fare rules | Platform admin email allowlist | Minor-unit base plus per-kg surcharge; no default rates |
| `GET /tracking/{tracking_number}` | Shipment tracking | Public | Status timeline only; no contact details or street addresses |
| `GET/POST /shipments`, `POST /shipments/bulk`, `GET /shipments/{id}` | Book/list/detail/bulk | Organization member | Quote-backed tenant booking; CSV max 500 rows and row outcomes |
| `PATCH /shipments/{id}/status` | Operations status transition | Platform admin email allowlist | Validated transitions; delivered requires proof method/reference |
| `GET /waybills/verify/{verification_code}` | Verify QR token | Public | Validity, waybill reference, tracking number and status |
| `GET /admin/audit-logs` | Inspect audit records | Platform admin email allowlist | Read-only; newest first, capped pages |
| `GET /marketplace/products` | Browse catalog | Public | Search by title; category filter; `limit`/`offset`; published/in-stock items only |
| `GET /marketplace/categories` | List product departments | Public | Eight Section 8.8 categories |
| `GET /merchant/products` | List merchant catalog | Merchant owner | `organization_id`, `limit`, `offset`; tenant-scoped |
| `POST /merchant/products`, `PATCH /merchant/products/{id}` | Manage catalog | Merchant owner | Tenant-scoped; new items remain unpublished |
| `POST /merchant/products/{id}/inventory` | Adjust stock | Merchant owner | Atomic delta; no negative stock; movement audit |
| `POST /merchant/products/{id}/publish` | Publish item | Platform admin allowlist | Manual platform review gate; KYB automation pending |
| `GET /cart`, `PUT /cart/items`, `DELETE /cart/items/{product_id}` | Read/edit customer cart | Authenticated customer | Cart belongs to caller; only published products can be added |
| `POST /orders`, `GET /orders` | Create pending order/history | Authenticated customer | Requires `Idempotency-Key`; snapshots prices; stays `awaiting_payment` |
| `GET /merchant/orders` | Merchant order view | Merchant owner | Only that merchant's line items and subtotal are returned |
| `POST /orders/{id}/fulfill` | Fulfill paid order | Owning merchant | Not implemented; requires verified payment workflow |
| `POST /payments/initialize`, `POST /webhooks/{provider}` | Payment flow | Authenticated/provider signature | Sandbox and deduplicated trusted events |
| `GET /invoices` | List invoices | Organization member | Tenant-scoped |
| `POST /verification/kyb` | Submit KYB | Merchant owner | Upload policy pending |

## Conventions

Protected routes use bearer access tokens. Client-supplied organization IDs or roles do not grant access. Error envelope: `{"error":{"code":"...","message":"...","details":[],"request_id":"..."}}`. Lists use one documented pagination format. Sensitive creates accept an `Idempotency-Key`. Endpoint-specific schemas, codes, examples, and pagination are added with each implemented module.

Register/login return a short-lived access token and an opaque refresh token. `POST /auth/refresh` consumes and rotates a refresh token. Reuse of a rotated token revokes the active token family. `POST /auth/logout` revokes a refresh token.

## Pricing and booking example

An illustrative platform-admin rule is `{"origin_zone":"ibadan","destination_zone":"lagos","delivery_tier":"standard","currency":"NGN","base_fare_minor":120000,"per_kg_minor":5000}`. For a 2.25 kg parcel the current formula returns 131250 minor units (kobo): `base_fare_minor + ceil(per_kg_minor * weight_kg)`. These numbers demonstrate the contract only; they are not DOGO-approved fares. Distance and delivery SLA are not calculated. Booking repeats the zones, tier, and weight, and each quote can be consumed once.

## Catalog and inventory examples

Merchant product creation accepts an `organization_id`, category ID, title, description, `price_minor`, optional dimensions/weight, currency, and `initial_stock`. Initial stock is recorded as an inventory movement. New products are private drafts; only a platform administrator can publish them after review. Stock changes use signed `quantity_delta` values and a required reason, with a conflict response if the change would make stock negative. Public catalog results include only published items with stock available.

Cart `PUT` sets a product quantity rather than incrementing it. `POST /orders` snapshots the current cart and prices, returns `awaiting_payment` / `pending`, and replays the same order for a repeated idempotency key. It does not charge or reserve inventory. Do not present this order as paid or fulfilled.

## Bulk booking CSV

`POST /api/v1/shipments/bulk?organization_id=...` accepts `Content-Type: text/csv`, up to 500 data rows and 2 MB. Required headers: `quote_id,origin_zone,destination_zone,delivery_tier,package_weight_kg,pickup_address,destination_address,recipient_name,recipient_phone,package_category`. Each row consumes its own quote; a failed row does not roll back successful rows. The response contains per-row `created` or `failed` outcomes. Example:

```csv
quote_id,origin_zone,destination_zone,delivery_tier,package_weight_kg,pickup_address,destination_address,recipient_name,recipient_phone,package_category
<quote-id>,ibadan,lagos,standard,2.25,"Pickup address","Delivery address",Ada,+2348000000000,parcel
```
