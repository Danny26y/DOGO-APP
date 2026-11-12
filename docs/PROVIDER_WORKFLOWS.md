# Selected provider workflows

## Paystack

`POST /api/v1/payments/initialize` accepts `{ "order_id": "...", "return_url": "https://..." }` for the authenticated order owner and returns the hosted checkout URL. The backend requires `PAYSTACK_SECRET_KEY`; the public key is for frontend Paystack.js. `POST /api/v1/webhooks/paystack` validates `x-paystack-signature`, matches order metadata, amount and currency, and stores the event ID once before changing payment state. Redirects are never proof of payment. Test credentials can be configured locally; never commit them. Refunds, stock reservation and settlement are not part of this flow.

## Email OTP

`POST /api/v1/auth/email-otp/request` accepts `{ "email": "..." }`; `POST /api/v1/auth/email-otp/verify` accepts `{ "email": "...", "code": "123456" }`. Codes are HMAC-hashed at rest, expire, are throttled to one issue per minute and allow five attempts. The response does not reveal whether an account exists. Enable with `EMAIL_OTP_ENABLED=true` and SMTP settings. While enabled, login requires verified email. No endpoint returns the OTP to the client.

## OSRM / OpenStreetMap

`GET /api/v1/routing/route?origin_lat=6.5&origin_lon=3.1&destination_lat=6.6&destination_lon=3.2` returns road distance in meters and duration in seconds. Configure `OSRM_BASE_URL`; the optional Compose `routing` profile serves a preprocessed regional OSRM dataset from `data/maps/region.osrm*`. The regional extract and preprocessing are deployment inputs. Client map rendering must attribute OpenStreetMap. Public community tile and geocoding endpoints have usage policies and are not an unlimited production service.

## Customer ID review

Customers upload raw PDF, JPEG or PNG bytes to `POST /api/v1/customers/me/identity-submissions?document_type=national_id`, with the matching content type and optional `X-File-Name`; maximum size is 5 MiB. Admins use `GET /api/v1/admin/identity-submissions`, `GET /api/v1/admin/identity-submissions/{id}/document` and `PATCH /api/v1/admin/identity-submissions/{id}` with `{ "status": "approved"|"rejected", "review_note": "..." }`. This is human review, not automated authenticity verification. Files live on a private volume outside the web root. Before production, move to private object storage and define encryption, malware scanning, access logging and retention/deletion rules.

## Required runtime configuration

`PAYSTACK_PUBLIC_KEY`, `PAYSTACK_SECRET_KEY`, `EMAIL_OTP_ENABLED`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`, `OSRM_BASE_URL`, `EMAIL_OTP_TTL_MINUTES`, and `VERIFICATION_UPLOAD_DIR` are environment settings. Leave provider credentials unset in source control. Sandbox payment tests require Paystack test keys; real email tests require SMTP credentials. Local unit tests use mocks and need no credentials.
