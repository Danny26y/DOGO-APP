from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.auth import models  # noqa: F401
from app.modules.auth.models import Organization, OrganizationMembership, User
from app.modules.marketplace.models import Product, ProductCategory
from app.modules.pricing.models import PricingRule

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(engine)
with TestingSession() as _session:
    _session.add_all([
        ProductCategory(id=f"00000000-0000-0000-0000-{index:012d}", slug=slug, name=name)
        for index, slug, name in [
            (1, "electronics-phones", "Electronics & Phones"),
            (2, "fashion", "Fashion"),
            (3, "groceries", "Groceries"),
            (4, "beauty-personal-care", "Beauty & Personal Care"),
            (5, "home-kitchen", "Home & Kitchen"),
            (6, "shoes-bags", "Shoes & Bags"),
            (7, "auto-parts", "Auto Parts"),
            (8, "books-office", "Books & Office"),
        ]
    ])
    _session.commit()


def override_db():
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = override_db
client = TestClient(app)


def test_health_endpoints():
    assert client.get("/health/live").json() == {"status": "live"}
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_register_login_and_me():
    response = client.post("/api/v1/auth/register", json={"email": "one@example.com", "password": "Correct-Horse-42!"})
    assert response.status_code == 201
    token = response.json()["access_token"]
    me_response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "one@example.com"
    login = client.post("/api/v1/auth/login", json={"email": "one@example.com", "password": "Correct-Horse-42!"})
    assert login.status_code == 200
    old_refresh = response.json()["refresh_token"]
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != old_refresh
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401
    family_revoked = client.post("/api/v1/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]})
    assert family_revoked.status_code == 401
    logout_token = login.json()["refresh_token"]
    assert client.post("/api/v1/auth/logout", json={"refresh_token": logout_token}).status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": logout_token}).status_code == 401


def test_organization_is_owned_by_creator():
    token = client.post("/api/v1/auth/login", json={"email": "one@example.com", "password": "Correct-Horse-42!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/v1/organizations", json={"name": "DOGO Test", "organization_type": "business"}, headers=headers)
    assert created.status_code == 201
    assert created.json()["role"] == "owner"
    listed = client.get("/api/v1/organizations", headers=headers)
    assert len(listed.json()) == 1


def test_validation_error_shape_and_request_id():
    response = client.post("/api/v1/auth/register", json={"email": "bad", "password": "short"}, headers={"X-Request-ID": "test-request"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["request_id"] == "test-request"


def test_quote_booking_public_tracking_and_tenant_isolation(monkeypatch):
    with TestingSession() as session:
        session.add(PricingRule(origin_zone="ibadan", destination_zone="lagos", delivery_tier="standard", base_fare_minor=120000, per_kg_minor=5000, created_by_user_id=session.scalar(select(User.id).where(User.email == "one@example.com"))))
        session.commit()

    quote_response = client.post("/api/v1/pricing/quotes", json={"origin_zone": "ibadan", "destination_zone": "lagos", "delivery_tier": "standard", "package_weight_kg": 2.25})
    assert quote_response.status_code == 201
    assert quote_response.json()["amount_minor"] == 131250
    token = client.post("/api/v1/auth/login", json={"email": "one@example.com", "password": "Correct-Horse-42!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    organization = client.get("/api/v1/organizations", headers=headers).json()[0]["id"]
    shipment_response = client.post("/api/v1/shipments", headers=headers, json={
        "organization_id": organization,
        "quote_id": quote_response.json()["quote_id"],
        "origin_zone": "ibadan",
        "destination_zone": "lagos",
        "delivery_tier": "standard",
        "package_weight_kg": 2.25,
        "pickup_address": "Pickup street, Ibadan",
        "destination_address": "Delivery street, Lagos",
        "recipient_name": "Recipient Person",
        "recipient_phone": "+2348000000000",
        "package_category": "parcel",
    })
    assert shipment_response.status_code == 201
    shipment = shipment_response.json()
    tracking = client.get(f"/api/v1/tracking/{shipment['tracking_number']}")
    assert tracking.status_code == 200
    assert "recipient_name" not in tracking.json()
    assert "pickup_address" not in tracking.json()
    assert client.get(f"/api/v1/waybills/verify/{shipment['qr_verification_code']}").json()["valid"] is True

    altered_quote = client.post("/api/v1/shipments", headers=headers, json={
        "organization_id": organization,
        "quote_id": quote_response.json()["quote_id"],
        "origin_zone": "ibadan",
        "destination_zone": "other-zone",
        "delivery_tier": "standard",
        "package_weight_kg": 2.25,
        "pickup_address": "Pickup street, Ibadan",
        "destination_address": "Delivery street, Lagos",
        "recipient_name": "Recipient Person",
        "recipient_phone": "+2348000000000",
        "package_category": "parcel",
    })
    assert altered_quote.status_code == 409

    monkeypatch.setattr("app.modules.shipments.routes.is_platform_admin", lambda _user: True)
    for next_status in ("pickup_scheduled", "picked_up", "in_transit", "out_for_delivery"):
        transition = client.patch(f"/api/v1/shipments/{shipment['id']}/status", headers=headers, json={"status": next_status})
        assert transition.status_code == 200
    delivered_without_proof = client.patch(f"/api/v1/shipments/{shipment['id']}/status", headers=headers, json={"status": "delivered"})
    assert delivered_without_proof.status_code == 422
    delivered = client.patch(f"/api/v1/shipments/{shipment['id']}/status", headers=headers, json={"status": "delivered", "proof_method": "otp", "proof_reference": "approved-case-proof"})
    assert delivered.status_code == 200
    monkeypatch.undo()

    with TestingSession() as session:
        other = User(email="other@example.com", password_hash=hash_password("Another-Password-44!"))
        session.add(other)
        session.flush()
        org = Organization(name="Other Org", organization_type="business")
        session.add(org)
        session.flush()
        session.add(OrganizationMembership(user_id=other.id, organization_id=org.id, role="owner"))
        session.commit()
    other_token = client.post("/api/v1/auth/login", json={"email": "other@example.com", "password": "Another-Password-44!"}).json()["access_token"]
    cross_tenant = client.get(f"/api/v1/shipments/{shipment['id']}", headers={"Authorization": f"Bearer {other_token}"})
    assert cross_tenant.status_code == 404
    added_member = client.post(f"/api/v1/organizations/{organization}/members", headers=headers, json={"email": "other@example.com", "role": "merchant_staff"})
    assert added_member.status_code == 201
    assert added_member.json()["role"] == "merchant_staff"
    member_list = client.get(f"/api/v1/organizations/{organization}/members", headers=headers)
    assert {member["email"] for member in member_list.json()} == {"one@example.com", "other@example.com"}


def test_quote_unavailable_without_approved_rule():
    response = client.post("/api/v1/pricing/quotes", json={"origin_zone": "no-rate", "destination_zone": "other", "delivery_tier": "standard", "package_weight_kg": 1})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "REQUEST_ERROR"


def test_bulk_csv_partial_failures_and_row_cap():
    token = client.post("/api/v1/auth/login", json={"email": "one@example.com", "password": "Correct-Horse-42!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    organization_id = client.get("/api/v1/organizations", headers=headers).json()[0]["id"]
    quote = client.post("/api/v1/pricing/quotes", json={"origin_zone": "ibadan", "destination_zone": "lagos", "delivery_tier": "standard", "package_weight_kg": 1})
    assert quote.status_code == 201
    csv_content = (
        "quote_id,origin_zone,destination_zone,delivery_tier,package_weight_kg,pickup_address,destination_address,recipient_name,recipient_phone,package_category\n"
        f"{quote.json()['quote_id']},ibadan,lagos,standard,1,Pickup street,Delivery street,Ada,+2348000000000,parcel\n"
        "bad-quote,ibadan,lagos,standard,invalid,Pickup street,Delivery street,Bola,+2348000000001,parcel\n"
    )
    response = client.post(f"/api/v1/shipments/bulk?organization_id={organization_id}", headers={**headers, "Content-Type": "text/csv"}, content=csv_content)
    assert response.status_code == 200
    assert response.json()["created"] == 1
    assert response.json()["failed"] == 1

    csv_header = "quote_id,origin_zone,destination_zone,delivery_tier,package_weight_kg,pickup_address,destination_address,recipient_name,recipient_phone,package_category\n"
    oversized_rows = csv_header + "bad-quote,ibadan,lagos,standard,1,Pickup street,Delivery street,Ada,+2348000000000,parcel\n" * 501
    capped = client.post(f"/api/v1/shipments/bulk?organization_id={organization_id}", headers={**headers, "Content-Type": "text/csv"}, content=oversized_rows)
    assert capped.status_code == 413


def test_product_catalog_and_inventory_are_tenant_scoped(monkeypatch):
    categories = client.get("/api/v1/marketplace/categories").json()
    assert len(categories) == 8
    token = client.post("/api/v1/auth/login", json={"email": "one@example.com", "password": "Correct-Horse-42!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    organization_id = client.get("/api/v1/organizations", headers=headers).json()[0]["id"]
    created = client.post("/api/v1/merchant/products", headers=headers, json={
        "organization_id": organization_id,
        "category_id": categories[0]["id"],
        "title": "Test phone",
        "description": "Catalog item",
        "price_minor": 100000,
        "initial_stock": 5,
    })
    assert created.status_code == 201
    product = created.json()
    assert product["published"] is False
    assert product["stock_quantity"] == 5
    assert client.get("/api/v1/marketplace/products").json() == []

    adjustment = client.post(f"/api/v1/merchant/products/{product['id']}/inventory?organization_id={organization_id}", headers=headers, json={"quantity_delta": -3, "reason": "Damaged units"})
    assert adjustment.status_code == 201
    negative = client.post(f"/api/v1/merchant/products/{product['id']}/inventory?organization_id={organization_id}", headers=headers, json={"quantity_delta": -3, "reason": "Should fail"})
    assert negative.status_code == 409
    listed = client.get(f"/api/v1/merchant/products?organization_id={organization_id}", headers=headers).json()
    assert listed[0]["stock_quantity"] == 2

    with TestingSession() as session:
        item = session.get(Product, product["id"])
        item.published = True
        session.commit()
    added_to_cart = client.put("/api/v1/cart/items", headers=headers, json={"product_id": product["id"], "quantity": 1})
    assert added_to_cart.status_code == 200
    created_order = client.post("/api/v1/orders", headers={**headers, "Idempotency-Key": "order-key-0001"})
    assert created_order.status_code == 201
    order = created_order.json()
    assert order["status"] == "awaiting_payment"
    assert order["payment_status"] == "pending"
    assert order["subtotal_minor"] == 100000
    repeated_order = client.post("/api/v1/orders", headers={**headers, "Idempotency-Key": "order-key-0001"})
    assert repeated_order.json()["id"] == order["id"]
    merchant_orders = client.get(f"/api/v1/merchant/orders?organization_id={organization_id}", headers=headers)
    assert merchant_orders.status_code == 200
    assert merchant_orders.json()[0]["merchant_subtotal_minor"] == 100000
    assert client.get(f"/api/v1/merchant/products?organization_id={organization_id}", headers=headers).json()[0]["stock_quantity"] == 2

    other_token = client.post("/api/v1/auth/login", json={"email": "other@example.com", "password": "Another-Password-44!"}).json()["access_token"]
    forbidden = client.patch(f"/api/v1/merchant/products/{product['id']}?organization_id={organization_id}", headers={"Authorization": f"Bearer {other_token}"}, json={"title": "Stolen edit"})
    assert forbidden.status_code == 200
    assert forbidden.json()["title"] == "Stolen edit"

    audit_denied = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert audit_denied.status_code == 403
    from app.modules.audit import routes as audit_routes
    monkeypatch.setattr(audit_routes, "get_settings", lambda: SimpleNamespace(platform_admin_email_set={"one@example.com"}))
    audit_response = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert audit_response.status_code == 200
    assert {item["action"] for item in audit_response.json()} >= {"inventory.adjusted", "order.created"}
