# Security

Access tokens expire quickly. Refresh tokens are opaque, stored as hashes, rotated once, and family-revoked when reuse is detected. Logout revokes refresh credentials; an already issued access token remains usable until its short expiry.

- Store passwords with an adaptive hash; never log raw passwords.
- Deny by default; scope tenant queries by server-validated membership.
- Public tracking returns approved fields only and must be rate-limited.
- Validate inputs, bound bulk requests, use parameterized ORM operations, and explicit writable schemas.
- Trust payment status only after provider verification; validate webhook signatures and deduplicate events.
- KYB upload requires private storage, restricted access, malware scanning, and retention policy before activation.
- Never commit production secrets or personal customer data.
- Audit sensitive administrative, access, and financial actions.
- Pricing rule and shipment status endpoints use a deployment-configured `PLATFORM_ADMIN_EMAILS` allowlist. Configure it only through environment/secret management.
- Audit records are append-only through the application API and visible only to platform-admin allowlist users. Retention/export policy remains a deployment decision.
- Delivery assignment responses expose pickup/dropoff and recipient contact data only to platform dispatch administrators and the currently assigned delivery agent. Public tracking omits these values.
- Delivery proof method/reference fields are audit pointers supplied by an authorized actor. They do not prove that an OTP, image, or signature was independently validated; secure evidence storage and verification are not active.

Deployment rate limiting, TLS, secret management, and file scanning are not active in the foundation milestone.
