# Integration adapter boundaries

The core API owns business records and state transitions. Vendor SDKs, credentials and provider-specific payloads belong behind the protocols in `app/integrations/ports.py`.

## Payments

Implement `PaymentProvider` for the provider selected by Finance/Engineering. The adapter creates an intent and verifies webhook authenticity before returning a normalized `VerifiedPaymentEvent`. The payment module must match the event amount/currency to the order and deduplicate by provider event ID before changing payment state. Browser redirects never prove payment. Until a provider is selected, no payment route is enabled.

## Settlement

Implement `SettlementCalculator` only after Finance/Legal approves the split basis, fee treatment, rounding, and recipient rules. The current protocol requires an explicit policy mapping for every calculation and has no default ratio. A demo implementation may preview alternatives but must not create a payable balance or initiate a transfer.

## Dispatch

The delivery module currently owns rider/driver profiles, manual assignments, acceptance, and status events. Implement `DispatchProvider` later to notify or synchronize an external dispatch product. Keep the database assignment as the source of truth and call external systems through an outbox/retry workflow after the assignment transaction commits.

## Demo adapters

Fake payment and settlement adapters may be instantiated only by tests or a separate demo application configuration. They must use clearly marked demo references, never production credentials, and must not be registered as a production provider. Keep the frontend-facing API schemas provider-neutral so approval selects an adapter without changing those contracts.

## Unresolved operational integrations

Agent account approval, manual assignment, assignment response, shipment progress, and operations summaries are implemented. External dispatch notifications, location streaming, SLA/ETA computation, identity/license checks, and proof-of-delivery storage/verification need their own approved adapter and policy. Current proof references are audit data, not evidence verified by DOGO.
