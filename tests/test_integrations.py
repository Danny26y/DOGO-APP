import hashlib
import hmac
import json
from io import BytesIO
from types import SimpleNamespace

import pytest

from app.integrations.osrm import RoutingError, route
from app.integrations.paystack import PaystackError, PaystackProvider


def test_paystack_webhook_signature_is_verified_and_normalized():
    body = json.dumps({"event": "charge.success", "data": {"id": 17, "reference": "ref-1", "status": "success", "amount": 2500, "currency": "NGN", "metadata": {"order_id": "order-1"}}}).encode()
    signature = hmac.new(b"test-secret", body, hashlib.sha512).hexdigest()
    event = PaystackProvider(secret_key="test-secret").verify_webhook({"X-Paystack-Signature": signature}, body)
    assert event.provider_event_id == "charge.success:17"
    assert event.order_id == "order-1"
    assert event.amount_minor == 2500


def test_paystack_rejects_invalid_webhook_signature():
    with pytest.raises(PaystackError, match="signature"):
        PaystackProvider(secret_key="test-secret").verify_webhook({}, b"{}")


def test_osrm_route_response_is_normalized(monkeypatch):
    monkeypatch.setattr("app.integrations.osrm.get_settings", lambda: SimpleNamespace(osrm_base_url="http://routing:5000"))
    monkeypatch.setattr("app.integrations.osrm.urlopen", lambda *_a, **_k: BytesIO(b'{"code":"Ok","routes":[{"distance":1234,"duration":456}]}'))
    assert route(3.1, 6.5, 3.2, 6.6) == {"distance_meters": 1234, "duration_seconds": 456}


def test_osrm_no_route_returns_controlled_error(monkeypatch):
    monkeypatch.setattr("app.integrations.osrm.get_settings", lambda: SimpleNamespace(osrm_base_url="http://routing:5000"))
    monkeypatch.setattr("app.integrations.osrm.urlopen", lambda *_a, **_k: BytesIO(b'{"code":"NoRoute","routes":[]}'))
    with pytest.raises(RoutingError, match="No driving route"):
        route(3.1, 6.5, 3.2, 6.6)
