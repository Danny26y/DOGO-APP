"""Paystack HTTP adapter. Secret-key configuration is required for server calls."""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.integrations.ports import (
    PaymentIntentRequest,
    PaymentIntentResult,
    VerifiedPaymentEvent,
)


class PaystackError(RuntimeError):
    pass


class PaystackProvider:
    def __init__(self, secret_key: str | None = None, base_url: str | None = None):
        settings = get_settings()
        self.secret_key = secret_key or settings.paystack_secret_key
        self.base_url = (base_url or settings.paystack_base_url).rstrip("/")

    def _post(self, path: str, payload: dict) -> dict:
        if not self.secret_key:
            raise PaystackError("Paystack is not configured")
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self.secret_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                result = json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise PaystackError("Paystack request failed") from exc
        if not result.get("status") or not isinstance(result.get("data"), dict):
            raise PaystackError("Paystack rejected the transaction request")
        return result["data"]

    def create_intent(self, request: PaymentIntentRequest, email: str) -> PaymentIntentResult:
        data = self._post("/transaction/initialize", {
            "email": email,
            "amount": request.amount_minor,
            "currency": request.currency,
            "reference": request.idempotency_key,
            "callback_url": request.return_url,
            "metadata": {"order_id": request.order_id},
        })
        try:
            return PaymentIntentResult(
                provider_reference=data["reference"],
                checkout_url=data["authorization_url"],
                expires_at=None,
            )
        except KeyError as exc:
            raise PaystackError("Paystack response was incomplete") from exc

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> VerifiedPaymentEvent:
        if not self.secret_key:
            raise PaystackError("Paystack is not configured")
        signature = next((v for k, v in headers.items() if k.lower() == "x-paystack-signature"), "")
        expected = hmac.new(self.secret_key.encode(), body, hashlib.sha512).hexdigest() if self.secret_key else ""
        if not signature or not hmac.compare_digest(signature, expected):
            raise PaystackError("Invalid Paystack webhook signature")
        try:
            payload = json.loads(body)
            data = payload["data"]
            if payload.get("event") not in {"charge.success", "charge.failed"}:
                raise PaystackError("Unsupported Paystack webhook event")
            if data.get("status") != ("success" if payload.get("event") == "charge.success" else "failed"):
                raise PaystackError("Paystack webhook event status is inconsistent")
            metadata = data.get("metadata") or {}
            return VerifiedPaymentEvent(
                provider_event_id=f"{payload['event']}:{data['id']}",
                provider_reference=data["reference"],
                order_id=metadata["order_id"],
                amount_minor=int(data["amount"]),
                currency=data["currency"],
                status=data["status"],
                occurred_at=datetime.now(UTC),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PaystackError("Malformed Paystack webhook") from exc
