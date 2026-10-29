from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class PaymentIntentRequest:
    order_id: str
    idempotency_key: str
    amount_minor: int
    currency: str
    return_url: str


@dataclass(frozen=True)
class PaymentIntentResult:
    provider_reference: str
    checkout_url: str
    expires_at: datetime | None


@dataclass(frozen=True)
class VerifiedPaymentEvent:
    provider_event_id: str
    provider_reference: str
    order_id: str
    amount_minor: int
    currency: str
    status: str
    occurred_at: datetime


class PaymentProvider(Protocol):
    """Provider adapter contract; only verified server events may confirm payment."""

    def create_intent(self, request: PaymentIntentRequest) -> PaymentIntentResult: ...

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> VerifiedPaymentEvent: ...


@dataclass(frozen=True)
class SettlementLine:
    beneficiary_reference: str
    amount_minor: int
    currency: str
    category: str


class SettlementCalculator(Protocol):
    """Policy adapter. Every ratio, fee and rounding rule must be explicitly supplied."""

    def calculate(
        self,
        *,
        gross_amount_minor: int,
        fee_amount_minor: int,
        currency: str,
        policy: dict[str, int],
    ) -> list[SettlementLine]: ...


@dataclass(frozen=True)
class DispatchRequest:
    shipment_id: str
    tracking_number: str
    delivery_agent_id: str
    agent_type: str


@dataclass(frozen=True)
class DispatchReference:
    provider: str
    provider_job_id: str


class DispatchProvider(Protocol):
    """Optional external dispatch adapter; the internal assignment workflow works without it."""

    def create_assignment(self, request: DispatchRequest) -> DispatchReference: ...
