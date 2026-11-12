import json
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.integrations.paystack import PaystackError, PaystackProvider
from app.integrations.ports import PaymentIntentRequest
from app.modules.audit.service import record_audit
from app.modules.auth.models import User
from app.modules.marketplace.models import Product
from app.modules.orders.models import InventoryReservation, Order, OrderFulfillment
from app.modules.payments.models import Payment, PaymentProviderEvent

router = APIRouter()


class PaymentIntentResponse(BaseModel):
    payment_id: str
    provider: str
    reference: str
    checkout_url: str
    amount_minor: int
    currency: str
    status: str


class PaymentInitializeRequest(BaseModel):
    order_id: str
    return_url: str = Field(min_length=8, max_length=1000)


@router.post("/payments/initialize", response_model=PaymentIntentResponse, status_code=201)
def initialize_payment(
    payload: PaymentInitializeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = urlsplit(payload.return_url)
    allowed_origins = {origin.rstrip("/") for origin in get_settings().cors_origins}
    if not target.scheme or not target.netloc or f"{target.scheme}://{target.netloc}" not in allowed_origins:
        raise HTTPException(status_code=422, detail="Return URL must use a configured frontend origin")
    order = db.scalar(select(Order).where(Order.id == payload.order_id, Order.customer_user_id == user.id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "awaiting_payment" or order.payment_status != "pending":
        raise HTTPException(status_code=409, detail="Order is not awaiting payment")
    existing = db.scalar(select(Payment).where(Payment.order_id == order.id, Payment.status == "pending"))
    if existing:
        return PaymentIntentResponse(payment_id=existing.id, provider=existing.provider, reference=existing.provider_reference, checkout_url=existing.checkout_url, amount_minor=existing.amount_minor, currency=existing.currency, status=existing.status)
    reference = f"dogo_{uuid4().hex}"
    try:
        intent = PaystackProvider().create_intent(PaymentIntentRequest(order_id=order.id, idempotency_key=reference, amount_minor=order.subtotal_minor, currency=order.currency, return_url=payload.return_url), email=user.email)
    except PaystackError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    payment = Payment(order_id=order.id, customer_user_id=user.id, provider="paystack", provider_reference=intent.provider_reference, amount_minor=order.subtotal_minor, currency=order.currency, checkout_url=intent.checkout_url)
    db.add(payment)
    try:
        db.flush()
        record_audit(db, actor_user_id=user.id, action="payment.initialized", resource_type="payment", resource_id=payment.id, details={"provider": "paystack", "order_id": order.id})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Payment initialization conflict; retry") from exc
    return PaymentIntentResponse(payment_id=payment.id, provider=payment.provider, reference=payment.provider_reference, checkout_url=payment.checkout_url, amount_minor=payment.amount_minor, currency=payment.currency, status=payment.status)


@router.post("/webhooks/paystack", status_code=200)
async def paystack_webhook(request: Request, x_paystack_signature: str | None = Header(default=None), db: Session = Depends(get_db)):
    body = await request.body()
    try:
        event = PaystackProvider().verify_webhook({"x-paystack-signature": x_paystack_signature or ""}, body)
    except PaystackError as exc:
        raise HTTPException(status_code=401, detail="Invalid Paystack webhook") from exc
    data = json.loads(body).get("data", {})
    if db.scalar(select(PaymentProviderEvent.id).where(PaymentProviderEvent.provider_event_id == event.provider_event_id)):
        return {"received": True, "duplicate": True}
    payment = db.scalar(select(Payment).where(Payment.provider_reference == event.provider_reference).with_for_update())
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment reference not found")
    order = db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == payment.order_id).with_for_update())
    if event.order_id != order.id or event.amount_minor != payment.amount_minor or event.currency != payment.currency:
        raise HTTPException(status_code=409, detail="Payment details do not match the order")
    db.add(PaymentProviderEvent(provider="paystack", provider_event_id=event.provider_event_id, payload=data))
    if payment.status == "succeeded":
        db.commit()
        return {"received": True, "duplicate": False}
    if event.status == "success":
        payment.status = "succeeded"
        order.payment_status = "paid"
        if order.status != "awaiting_payment":
            record_audit(db, actor_user_id=None, action="payment.succeeded_after_order_state_change", resource_type="payment", resource_id=payment.id, details={"order_id": order.id, "order_status": order.status})
        else:
            requirements = {}
            for item in order.items:
                requirements[item.product_id] = requirements.get(item.product_id, 0) + item.quantity
            products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(sorted(requirements))).order_by(Product.id).with_for_update())} if requirements else {}
            stock_available = len(products) == len(requirements) and all(products[pid].stock_quantity - products[pid].reserved_quantity >= qty for pid, qty in requirements.items())
            if not stock_available:
                order.status = "paid_needs_review"
                record_audit(db, actor_user_id=None, action="payment.paid_inventory_exception", resource_type="order", resource_id=order.id, details={"order_id": order.id})
            else:
                order.status = "paid"
                merchant_ids = set()
                for item in order.items:
                    product = products[item.product_id]
                    product.reserved_quantity += item.quantity
                    db.add(InventoryReservation(order_item_id=item.id, product_id=product.id, organization_id=item.merchant_organization_id, quantity=item.quantity))
                    merchant_ids.add(item.merchant_organization_id)
                for organization_id in merchant_ids:
                    db.add(OrderFulfillment(order_id=order.id, organization_id=organization_id, status="pending"))
                record_audit(db, actor_user_id=None, action="payment.verified_and_inventory_reserved", resource_type="payment", resource_id=payment.id, details={"order_id": order.id, "merchant_count": len(merchant_ids)})
    else:
        payment.status = "failed"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"received": True, "duplicate": True}
    return {"received": True, "duplicate": False}
